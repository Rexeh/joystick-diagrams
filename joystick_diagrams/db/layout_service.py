"""Cached, write-through access to layout ops (plan §5.3, §5.6).

Mirrors ``ThemeService``/``ModifierKeyService``: a dict cache keyed by
``(template_key, profile_key)`` loaded once, every write goes to the database and
the cache together, invalid rows are logged and skipped.

How the editor (E2) uses it
---------------------------
- ``layers = service.get_layers(template.template_key, wrapper.profile_key)``:
  the template layer (``profile_key == ""``) and the profile layer, as
  ``LayoutLayers``; pass them to ``render_for_editor``.
- Persist one op from the editor::

      service.append_op(template.template_key, scope_key, op, template.content_hash)

  where ``scope_key`` is ``TEMPLATE_LAYER`` ("Changes apply to: all profiles on
  this diagram") or the wrapper's ``profile_key`` ("only this profile"). Keyboard
  nudges can use ``append_op(..., coalesce=True)`` so consecutive moves of the
  same target merge into one op. Undo removes the op again with
  ``remove_op(template_key, scope_key, uid)``; editing a note or re-dragging
  uses ``replace_op``. ``clear`` deletes a layer ("Undo my changes for this
  profile" / "Reset all").
- Drift: ``drift_notice(template_key, profile_key, template.content_hash)``
  is ``True`` when the stored ``content_hash`` differs from the file's current
  hash, i.e. the template was edited or updated since the ops were saved. The
  ops still apply (they are keyed by slot identity); ``layout_apply`` reports
  the ones that no longer fit. ``relink_candidates(content_hash)`` lists rows
  whose template moved (same bytes, different key) for a "Re-link my changes"
  action, carried out by ``relink``.
- ``snapshot()`` is the immutable mapping ``RenderContext.layouts`` carries to
  the export worker (``build_render_context`` calls it).
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from pydantic import ValidationError

from joystick_diagrams.db import db_template_layouts
from joystick_diagrams.render.layout import (
    TEMPLATE_LAYER,
    LayoutDocument,
    LayoutLayers,
    LayoutOp,
    MoveOp,
)

_logger = logging.getLogger(__name__)

LayoutKey = tuple[str, str]


@dataclass(frozen=True)
class StoredLayout:
    document: LayoutDocument
    content_hash: str | None
    updated_at: str | None


class LayoutService:
    def __init__(self):
        self._cache: dict[LayoutKey, StoredLayout] = {}
        self._load_cache()

    # ── Loading ────────────────────────────────────────────────────────

    def _load_cache(self) -> None:
        self._cache = {}
        for row in db_template_layouts.get_all_layouts():
            template_key, profile_key, ops_json, content_hash, updated_at = row
            try:
                document = LayoutDocument.model_validate_json(ops_json)
            except ValidationError as err:
                _logger.warning(
                    f"Skipping invalid stored layout {template_key!r}/{profile_key!r}: {err}"
                )
                continue
            document = document.model_copy(
                update={
                    "template_key": template_key,
                    "profile_key": profile_key,
                    "content_hash": content_hash,
                }
            )
            self._cache[(template_key, profile_key)] = StoredLayout(
                document, content_hash, updated_at
            )
        _logger.info(f"Loaded {len(self._cache)} template layouts from database")

    # ── Read API ───────────────────────────────────────────────────────

    def get_document(
        self, template_key: str, profile_key: str = TEMPLATE_LAYER
    ) -> LayoutDocument:
        """The stored document for one layer (an empty one when nothing is stored)."""
        stored = self._cache.get((template_key, profile_key))
        if stored is None:
            return LayoutDocument(template_key=template_key, profile_key=profile_key)
        return stored.document.model_copy(deep=True)

    def get_layers(self, template_key: str, profile_key: str | None) -> LayoutLayers:
        """Template layer then profile layer for ``(template_key, profile_key)``."""
        profile = (
            self.get_document(template_key, profile_key)
            if profile_key
            else LayoutDocument(template_key=template_key)
        )
        return LayoutLayers(self.get_document(template_key, TEMPLATE_LAYER), profile)

    def has_ops(self, template_key: str, profile_key: str | None) -> bool:
        return not self.get_layers(template_key, profile_key).is_empty

    def templates_with_layouts(self) -> set[str]:
        return {key for key, _profile in self._cache}

    def layers_of_template(self, template_key: str) -> list[str]:
        """Profile keys of every stored layer for ``template_key`` (``""`` = template layer)."""
        return sorted(profile for key, profile in self._cache if key == template_key)

    def stored_hash(self, template_key: str, profile_key: str) -> str | None:
        stored = self._cache.get((template_key, profile_key))
        return stored.content_hash if stored is not None else None

    def drift_notice(
        self, template_key: str, profile_key: str | None, current_hash: str | None
    ) -> bool:
        """True when either stored layer was written against different template bytes."""
        if current_hash is None:
            return False
        for layer in (TEMPLATE_LAYER, profile_key or TEMPLATE_LAYER):
            stored = self._cache.get((template_key, layer))
            if stored is not None and stored.content_hash not in (None, current_hash):
                return True
        return False

    def relink_candidates(self, content_hash: str | None) -> list[str]:
        """Template keys whose stored ops were made on identical bytes (template moved)."""
        if not content_hash:
            return []
        return sorted(
            {
                key
                for (key, _profile), stored in self._cache.items()
                if stored.content_hash == content_hash
            }
        )

    def snapshot(self) -> Mapping[LayoutKey, LayoutDocument]:
        """Immutable copy for ``RenderContext.layouts``."""
        return MappingProxyType(
            {
                key: stored.document.model_copy(deep=True)
                for key, stored in self._cache.items()
            }
        )

    # ── Write API ──────────────────────────────────────────────────────

    def set_ops(
        self,
        template_key: str,
        profile_key: str,
        ops: list[LayoutOp],
        content_hash: str | None,
    ) -> LayoutDocument:
        """Replace a layer's op list (an empty list deletes the row)."""
        if not ops:
            self.clear(template_key, profile_key)
            return LayoutDocument(template_key=template_key, profile_key=profile_key)
        document = LayoutDocument(
            template_key=template_key,
            profile_key=profile_key,
            content_hash=content_hash,
            ops=list(ops),
        )
        db_template_layouts.upsert_layout(
            template_key, profile_key, document.model_dump_json(), content_hash
        )
        self._cache[(template_key, profile_key)] = StoredLayout(
            document.model_copy(deep=True), content_hash, None
        )
        return document

    def append_op(
        self,
        template_key: str,
        profile_key: str,
        op: LayoutOp,
        content_hash: str | None,
        *,
        coalesce: bool = False,
    ) -> LayoutOp:
        """Add one op to a layer; ``coalesce`` merges a move into a trailing move."""
        document = self.get_document(template_key, profile_key)
        stored = (
            document.coalesce_move(op)
            if coalesce and isinstance(op, MoveOp)
            else document.append(op)
        )
        self.set_ops(template_key, profile_key, document.ops, content_hash)
        return stored

    def replace_op(
        self,
        template_key: str,
        profile_key: str,
        uid: str,
        op: LayoutOp,
        content_hash: str | None,
    ) -> bool:
        document = self.get_document(template_key, profile_key)
        if not document.replace_op(uid, op):
            return False
        self.set_ops(template_key, profile_key, document.ops, content_hash)
        return True

    def remove_op(self, template_key: str, profile_key: str, uid: str) -> bool:
        document = self.get_document(template_key, profile_key)
        if not document.remove_op(uid):
            return False
        self.set_ops(template_key, profile_key, document.ops, document.content_hash)
        return True

    def clear(self, template_key: str, profile_key: str) -> None:
        db_template_layouts.delete_layout(template_key, profile_key)
        self._cache.pop((template_key, profile_key), None)

    def clear_template(self, template_key: str) -> None:
        db_template_layouts.delete_layouts_for_template(template_key)
        for key in [k for k in self._cache if k[0] == template_key]:
            del self._cache[key]

    def relink(self, old_key: str, new_key: str) -> None:
        """Move every layer from ``old_key`` to ``new_key`` (replacing clashes)."""
        db_template_layouts.rename_template_key(old_key, new_key)
        for (key, profile), stored in list(self._cache.items()):
            if key == old_key:
                del self._cache[(key, profile)]
                document = stored.document.model_copy(update={"template_key": new_key})
                self._cache[(new_key, profile)] = StoredLayout(
                    document, stored.content_hash, stored.updated_at
                )


if __name__ == "__main__":
    pass
