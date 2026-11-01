"""``LayoutEditSession``: the Layout screen's edit model (plain Python, no Qt).

Every gesture becomes one or more ``LayoutOp``s written straight through
``LayoutService`` (so the change survives ``MainWindow._invalidate_data_pages``
and is used by the next export), plus one **undo entry** that remembers the
touched layers' op lists before and after. Undo restores the "before" lists
with ``set_ops``; redo restores the "after" lists. That makes every action,
from a single nudge to "Auto-add 24 boxes" or "Reset all", exactly one undo
step, and keeps the service's stored documents as the single source of truth.

Layers: ``TEMPLATE_LAYER`` (``""``, "All profiles on this diagram") or a
``ProfileWrapper.profile_key`` ("Only <profile>"). ``scope`` is the layer new
ops go to; ``profile_key`` is the "Preview with" profile whose layer is shown
on top of the template layer.

Layout edits belong to one controller: every read and write carries
``device_guid`` (``export_device.device_id``), so two controllers sharing a
template (a Starter Template copy, say) keep independent layouts. A controller
with no rows of its own yet reads the shared rows (``device_guid == ""``,
layouts made before edits were per controller); its first edit copies that
layer into its own row, so nothing it showed is lost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from joystick_diagrams.render.layout import (
    TEMPLATE_LAYER,
    AddModifierBoxOp,
    AddNoteOp,
    EditNoteOp,
    HideOp,
    LayoutLayers,
    LayoutOp,
    MoveOp,
    NoteStyle,
    RemoveAddedElementOp,
    ResizeOp,
    ShowOp,
    normalise_target,
)

MAX_HISTORY = 200


@dataclass
class UndoEntry:
    label: str
    before: dict[str, list[LayoutOp]]
    after: dict[str, list[LayoutOp]]
    coalesce_key: tuple[str, str] | None = None  # (layer, target) for nudges
    uids: list[str] = field(default_factory=list)  # ops this entry created


class LayoutEditSession:
    def __init__(
        self,
        service: Any,
        template_key: str,
        content_hash: str | None,
        *,
        profile_key: str | None = None,
        scope: str = TEMPLATE_LAYER,
        device_guid: str = "",
    ) -> None:
        self.service = service
        self.template_key = template_key
        self.content_hash = content_hash
        self.profile_key = profile_key
        self.scope = scope
        self.device_guid = device_guid or ""
        self._undo: list[UndoEntry] = []
        self._redo: list[UndoEntry] = []

    # ── Scope and layers ──

    def set_scope(self, layer: str) -> None:
        self.scope = layer

    def set_profile(self, profile_key: str | None) -> None:
        self.profile_key = profile_key
        if self.scope and self.scope != profile_key:
            self.scope = profile_key or TEMPLATE_LAYER

    def layers(self) -> LayoutLayers:
        return self.service.get_layers(
            self.template_key, self.profile_key, device_guid=self.device_guid
        )

    def _own_layers(self) -> list[str]:
        return self.service.layers_of_template(self.template_key, self.device_guid)

    def ops_in(self, layer: str) -> list[LayoutOp]:
        """The ops this controller's diagram uses for ``layer`` (its own row, else
        the shared row it falls back to)."""
        document = self.service.get_document(self.template_key, layer, self.device_guid)
        if self.device_guid and not document.ops and layer not in self._own_layers():
            document = self.service.get_document(self.template_key, layer, "")
        return list(document.ops)

    def _clear(self, layer: str) -> None:
        """Remove this controller's row for ``layer`` and the shared row it would fall
        back to (an empty layer can't be stored, so a shared row would reappear)."""
        self.service.clear(self.template_key, layer, device_guid=self.device_guid)
        if self.device_guid:
            self.service.clear(self.template_key, layer, device_guid="")

    def _set_ops(self, layer: str, ops: list[LayoutOp]) -> None:
        self.service.set_ops(
            self.template_key,
            layer,
            list(ops),
            self.content_hash,
            device_guid=self.device_guid,
        )

    def change_count(self, layer: str) -> int:
        return len(self.ops_in(layer))

    # ── History ──

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def clear_history(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def _snapshot(self, layers: list[str]) -> dict[str, list[LayoutOp]]:
        return {layer: self.ops_in(layer) for layer in dict.fromkeys(layers)}

    def _restore(self, snapshot: dict[str, list[LayoutOp]]) -> None:
        for layer, ops in snapshot.items():
            self._set_ops(layer, ops)

    def _record(self, entry: UndoEntry) -> UndoEntry:
        self._undo.append(entry)
        del self._undo[:-MAX_HISTORY]
        self._redo.clear()
        return entry

    def undo(self) -> UndoEntry | None:
        if not self._undo:
            return None
        entry = self._undo.pop()
        self._restore(entry.before)
        self._redo.append(entry)
        return entry

    def redo(self) -> UndoEntry | None:
        if not self._redo:
            return None
        entry = self._redo.pop()
        self._restore(entry.after)
        self._undo.append(entry)
        return entry

    # ── Applying ops ──

    def apply(
        self,
        ops: list[LayoutOp],
        *,
        layer: str | None = None,
        label: str = "",
        coalesce_key: tuple[str, str] | None = None,
    ) -> UndoEntry | None:
        """Append ``ops`` to ``layer`` (default: the scope) as one undo step."""
        if not ops:
            return None
        layer = self.scope if layer is None else layer
        before = self._snapshot([layer])
        self._set_ops(layer, [*before[layer], *ops])
        after = self._snapshot([layer])
        entry = UndoEntry(label, before, after, coalesce_key, [op.uid for op in ops])
        return self._record(entry)

    def move(
        self, target: str, dx: float, dy: float, *, coalesce: bool = False
    ) -> UndoEntry | None:
        if not (dx or dy):
            return None
        key = (self.scope, normalise_target(target)) if coalesce else None
        last = self._undo[-1] if self._undo else None
        if coalesce and last is not None and last.coalesce_key == key:
            # Merge into the previous nudge: same "before", new "after".
            previous = self.ops_in(self.scope)
            merged = False
            for index in range(len(previous) - 1, -1, -1):
                op = previous[index]
                if op.uid in last.uids and isinstance(op, MoveOp):
                    previous[index] = op.model_copy(
                        update={"dx": op.dx + dx, "dy": op.dy + dy}
                    )
                    merged = True
                    break
            if merged:
                self._set_ops(self.scope, previous)
                last.after = self._snapshot([self.scope])
                self._redo.clear()
                return last
        return self.apply(
            [MoveOp(target=target, dx=dx, dy=dy)], label="move", coalesce_key=key
        )

    def resize(
        self, target: str, width: float, height: float, dx: float = 0.0, dy: float = 0.0
    ) -> UndoEntry | None:
        ops: list[LayoutOp] = []
        if dx or dy:
            ops.append(MoveOp(target=target, dx=dx, dy=dy))
        ops.append(ResizeOp(target=target, width=width, height=height))
        return self.apply(ops, label="resize")

    def hide(self, target: str) -> UndoEntry | None:
        return self.apply([HideOp(target=target)], label="hide")

    def show(self, target: str) -> UndoEntry | None:
        return self.apply([ShowOp(target=target)], label="show")

    def remove_added(self, uid: str) -> UndoEntry | None:
        return self.apply([RemoveAddedElementOp(target=uid)], label="remove")

    def add_modifier_box(
        self,
        target: str,
        index: int,
        dx: float,
        dy: float,
        width: float | None = None,
        height: float | None = None,
    ) -> AddModifierBoxOp:
        op = AddModifierBoxOp(
            target=target, index=index, dx=dx, dy=dy, width=width, height=height
        )
        self.apply([op], label="add box")
        return op

    def add_note(
        self,
        text: str,
        x: float,
        y: float,
        width: float,
        height: float,
        style: NoteStyle | None = None,
    ) -> AddNoteOp:
        op = AddNoteOp(
            text=text, x=x, y=y, width=width, height=height, style=style or NoteStyle()
        )
        self.apply([op], label="add note")
        return op

    def edit_note(self, uid: str, text: str) -> UndoEntry | None:
        return self.apply([EditNoteOp(target=uid, text=text)], label="edit note")

    # ── Removing ops ──

    def undo_changes_to(self, target: str) -> UndoEntry | None:
        """Drop every op in the scope layer that touches ``target`` (one undo step)."""
        wanted = normalise_target(target)
        before = self._snapshot([self.scope])
        kept = [op for op in before[self.scope] if not _touches(op, wanted)]
        if len(kept) == len(before[self.scope]):
            return None
        self._set_ops(self.scope, kept)
        return self._record(
            UndoEntry("undo changes to box", before, self._snapshot([self.scope]))
        )

    def clear_layer(self, layer: str) -> UndoEntry | None:
        """ "Undo my changes for this profile" (one undo step)."""
        before = self._snapshot([layer])
        if not before[layer]:
            return None
        self._clear(layer)
        return self._record(UndoEntry("clear layer", before, {layer: []}))

    def has_changes(self) -> bool:
        """Whether this controller's diagram has any layout change (own or shared)."""
        layers = set(self._own_layers())
        if self.device_guid:
            layers.update(self.service.layers_of_template(self.template_key, ""))
        return any(self.ops_in(layer) for layer in layers)

    def reset_all(self) -> UndoEntry | None:
        """ "Reset layout": every layer of this controller's diagram (one undo step)."""
        layers = set(self._own_layers())
        if self.device_guid:
            layers.update(self.service.layers_of_template(self.template_key, ""))
        layers = sorted(layer for layer in layers if self.ops_in(layer))
        if not layers:
            return None
        before = self._snapshot(layers)
        for layer in layers:
            self._clear(layer)
        return self._record(
            UndoEntry("reset all", before, {layer: [] for layer in layers})
        )


def _touches(op: LayoutOp, target: str) -> bool:
    own = getattr(op, "target", None)
    if own is not None and own == target:
        return True
    anchor = getattr(op, "anchor", None)
    return anchor is not None and anchor == target


__all__ = ["MAX_HISTORY", "LayoutEditSession", "UndoEntry"]

if __name__ == "__main__":
    pass
