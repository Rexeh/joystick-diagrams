"""The template catalogue: every template the user can choose, with fit and thumbnails.

Enumeration
-----------
``bundled_templates()`` walks the shipped ``templates`` folder: one maker per
top-level folder (``CH``, ``WinWing`` …, nested folders belong to the same
maker), ``.bkp`` and dot-files skipped, empty folders (``MOZA``) simply absent.
The root-level ``Starter Template.svg`` has an empty maker and
``TemplateInfo.is_starter``. ``user_templates()`` lists **My templates**
(``utils.user_templates_root()``). ``all_templates()`` is both; ``find(key)``
looks one up by ``template_key``.

Fit
---
``fit(info, device_or_devices)`` answers "does this template have a box for every
control I use?" with ``ExportDevice.check_compatibility`` semantics: the bound
control identifiers (buttons, hats, axes and sliders, lower-cased) minus the
template's placeholder keys. Pass one ``Device_``/``ExportDevice`` or several
(the same controller across profiles; their controls are unioned). The result is
cached by ``(template_key, content_hash, hash of the bound-control set)`` and the
``Template`` parse by ``(template_key, content_hash)``, so a picker that shows a
fit count on every row costs one parse per template. ``control_label`` turns
``button_31`` into "Button 31", ``pov_3_u`` into "Hat 3 Up", ``axis_slider_1``
into "Slider 1".

Thumbnails
----------
``thumbnail_for(info, size=(320, None))`` renders the template with
``QSvgRenderer`` to ``data_root()/cache/thumbs/<content_hash>.png`` (other widths
get ``-w<width>`` appended). The draw.io ``content`` attribute and the
"Text is not SVG" footer are removed first, so the footer never shows.
``QSvgRenderer``, ``QImage`` and ``QPainter`` need a ``QGuiApplication`` to exist
but **not** the GUI thread, so this is safe to call from a worker (``QThreadPool``
runnable) once the application is up; without one ``ThumbnailUnavailableError`` is
raised. The Starter Template (an instructions page) and any file QtSvg cannot
read get a generic controller icon instead.

Starter copy
------------
``create_from_starter(device_name)`` copies the bundled Starter Template into My
templates as ``<device name>.svg`` (file-name-safe, ``" 2"`` … appended on a
clash) and returns ``CreatedTemplate(path, template_key, info)``.
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from joystick_diagrams import utils
from joystick_diagrams.template import (
    Template,
    bundled_templates_root,
    hash_file_bytes,
    template_key_for,
)

_logger = logging.getLogger(__name__)

STARTER_TEMPLATE_FILE = "Starter Template.svg"
TEMPLATE_SUFFIX = ".svg"
THUMBNAIL_WIDTH = 320
THUMBS_DIR = ("cache", "thumbs")
FALLBACK_DEVICE_NAME = "My controller"

Source = Literal["bundled", "user"]


@dataclass(frozen=True)
class TemplateInfo:
    key: str  # Template.template_key: "bundled:<rel>" | "user:<abs>"
    name: str  # file stem, shown to the user
    maker: str  # top-level folder for bundled; "My templates" for user files; "" for the Starter
    path: Path
    source: Source
    content_hash: str

    @property
    def is_starter(self) -> bool:
        return self.source == "bundled" and self.path.name == STARTER_TEMPLATE_FILE


@dataclass(frozen=True)
class FitResult:
    total_bound: int  # controls the user has bound on this controller
    missing: tuple[
        str, ...
    ]  # plain names of bound controls the template has no box for
    fits_all: bool

    @property
    def fitted(self) -> int:
        return self.total_bound - len(self.missing)


@dataclass(frozen=True)
class CreatedTemplate:
    path: Path
    template_key: str
    info: TemplateInfo


class ThumbnailUnavailableError(RuntimeError):
    """Raised when no ``QGuiApplication`` exists (thumbnails need one; see module doc)."""


# ── Enumeration ──


def _is_template_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() == TEMPLATE_SUFFIX
        and not path.name.startswith(".")
    )


def _info_for(
    path: Path, root: Path, source: Source, default_maker: str
) -> TemplateInfo:
    try:
        relative = path.relative_to(root)
        maker = relative.parts[0] if len(relative.parts) > 1 else default_maker
    except ValueError:
        maker = default_maker
    return TemplateInfo(
        key=template_key_for(path),
        name=path.stem,
        maker=maker,
        path=path,
        source=source,
        content_hash=hash_file_bytes(path),
    )


def _sorted(infos: Iterable[TemplateInfo]) -> list[TemplateInfo]:
    return sorted(infos, key=lambda i: (i.maker.casefold(), i.name.casefold()))


def _enumerate(root: Path, source: Source, default_maker: str) -> list[TemplateInfo]:
    if not root.is_dir():
        return []
    infos = []
    for path in sorted(root.rglob(f"*{TEMPLATE_SUFFIX}")):
        if not _is_template_file(path):
            continue
        try:
            infos.append(_info_for(path, root, source, default_maker))
        except OSError as error:
            _logger.warning(f"Skipping unreadable template {path}: {error}")
    return _sorted(infos)


def bundled_templates() -> list[TemplateInfo]:
    """Shipped templates, by maker then name. The Starter Template has maker ``""``."""
    return _enumerate(bundled_templates_root(), "bundled", "")


def user_templates() -> list[TemplateInfo]:
    """Templates in My templates (``data_root()/templates/My templates``)."""
    return _enumerate(
        utils.user_templates_root(), "user", utils.USER_TEMPLATES_DIR_NAME
    )


def all_templates() -> list[TemplateInfo]:
    return bundled_templates() + user_templates()


def makers(infos: Iterable[TemplateInfo] | None = None) -> list[str]:
    """Distinct non-empty makers, in catalogue order."""
    seen: dict[str, None] = {}
    for info in infos if infos is not None else all_templates():
        if info.maker:
            seen.setdefault(info.maker, None)
    return list(seen)


def find(template_key: str) -> TemplateInfo | None:
    for info in all_templates():
        if info.key == template_key:
            return info
    return None


def info_for_path(path: Path) -> TemplateInfo:
    """A ``TemplateInfo`` for any template file (bundled, My templates or elsewhere)."""
    path = Path(path).resolve()
    bundled_root = bundled_templates_root()
    user_root = utils.user_templates_root()
    if template_key_for(path).startswith("bundled:"):
        return _info_for(path, bundled_root, "bundled", "")
    if path.is_relative_to(user_root):
        return _info_for(path, user_root, "user", utils.USER_TEMPLATES_DIR_NAME)
    return _info_for(path, path.parent, "user", path.parent.name)


def starter_template() -> TemplateInfo:
    path = bundled_templates_root() / STARTER_TEMPLATE_FILE
    return _info_for(path, bundled_templates_root(), "bundled", "")


# ── Fit ──

_lock = threading.Lock()
_template_cache: dict[tuple[str, str], Template] = {}
_fit_cache: dict[tuple[str, str, str], FitResult] = {}


def clear_caches() -> None:
    with _lock:
        _template_cache.clear()
        _fit_cache.clear()


def template_for(info: TemplateInfo) -> Template:
    """The parsed ``Template`` for ``info`` (cached by key and content hash)."""
    cache_key = (info.key, info.content_hash)
    with _lock:
        cached = _template_cache.get(cache_key)
    if cached is not None:
        return cached
    template = Template(str(info.path))
    with _lock:
        _template_cache[cache_key] = template
    return template


def _devices(device_or_devices: Any) -> list[Any]:
    if device_or_devices is None:
        return []
    if hasattr(device_or_devices, "get_inputs"):
        return [device_or_devices]
    if hasattr(device_or_devices, "device"):  # ExportDevice
        return [device_or_devices.device]
    devices = []
    for item in device_or_devices:
        devices.extend(_devices(item))
    return devices


def bound_controls(device_or_devices: Any) -> frozenset[str]:
    """Lower-cased identifiers of every bound control, across one or more devices.

    Accepts a ``Device_``, an ``ExportDevice`` or an iterable of either.
    """
    controls: set[str] = set()
    for device in _devices(device_or_devices):
        for inputs in device.get_inputs().values():
            controls.update(key.lower() for key in inputs)
    return frozenset(controls)


def controls_hash(controls: Iterable[str]) -> str:
    return sha256("\n".join(sorted(controls)).encode("utf-8")).hexdigest()


_HAT_DIRECTIONS = {
    "u": "Up",
    "ur": "Up Right",
    "r": "Right",
    "dr": "Down Right",
    "d": "Down",
    "dl": "Down Left",
    "l": "Left",
    "ul": "Up Left",
}


def control_label(identifier: str) -> str:
    """Plain-language name for a control identifier ("button_31" → "Button 31")."""
    parts = identifier.lower().split("_")
    if parts[0] == "button" and len(parts) == 2:
        return f"Button {parts[1]}"
    if parts[0] == "pov" and len(parts) == 3:
        direction = _HAT_DIRECTIONS.get(parts[2], parts[2].upper())
        return f"Hat {parts[1]} {direction}"
    if parts[0] == "axis" and len(parts) == 3 and parts[1] == "slider":
        return f"Slider {parts[2]}"
    if parts[0] == "axis" and len(parts) == 2:
        return f"Axis {parts[1].upper()}"
    return identifier.replace("_", " ").title()


def _sort_key(identifier: str) -> tuple[int, int, str]:
    parts = identifier.lower().split("_")
    order = {"button": 0, "pov": 1, "axis": 2}.get(parts[0], 3)
    number = next((int(p) for p in parts[1:] if p.isdigit()), 0)
    return order, number, identifier


def missing_controls(template: Template, controls: Iterable[str]) -> list[str]:
    """Bound control identifiers the template has no box for, in display order."""
    controls = {c.lower() for c in controls}
    buttons = {c for c in controls if c.startswith("button_")}
    hats = {c for c in controls if c.startswith("pov_")}
    axes = {c for c in controls if c.startswith("axis_")}
    missing = (
        (buttons - template.get_template_buttons())
        | (hats - template.get_template_hats())
        | (axes - template.get_template_axis())
    )
    return sorted(missing, key=_sort_key)


def fit(info: TemplateInfo, device_or_devices: Any) -> FitResult:
    """How well ``info`` fits the controls bound on a controller (see module doc)."""
    controls = bound_controls(device_or_devices)
    cache_key = (info.key, info.content_hash, controls_hash(controls))
    with _lock:
        cached = _fit_cache.get(cache_key)
    if cached is not None:
        return cached
    template = template_for(info)
    missing = tuple(control_label(c) for c in missing_controls(template, controls))
    result = FitResult(total_bound=len(controls), missing=missing, fits_all=not missing)
    with _lock:
        _fit_cache[cache_key] = result
    return result


def fit_text(result: FitResult) -> str:
    """The one-line status for a picker row or the Template section."""
    if result.total_bound == 0:
        return "No bindings to check"
    if result.fits_all:
        return f"Has all {result.total_bound} controls you use"
    return f"{result.fitted} of {result.total_bound} controls fit"


# ── Starter copy ──

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_file_stem(name: str, fallback: str = FALLBACK_DEVICE_NAME) -> str:
    """A file-name-safe stem: forbidden characters removed, whitespace collapsed."""
    cleaned = _INVALID_FILENAME_CHARS.sub("", name)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return cleaned[:120] or fallback


def unique_path(folder: Path, stem: str, suffix: str = TEMPLATE_SUFFIX) -> Path:
    candidate = folder / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = folder / f"{stem} {counter}{suffix}"
        counter += 1
    return candidate


def create_from_starter(device_name: str) -> CreatedTemplate:
    """Copy the bundled Starter Template into My templates, named after the controller."""
    source = bundled_templates_root() / STARTER_TEMPLATE_FILE
    folder = utils.user_templates_root()
    target = unique_path(folder, safe_file_stem(device_name))
    target.write_bytes(source.read_bytes())
    info = _info_for(target, folder, "user", utils.USER_TEMPLATES_DIR_NAME)
    _logger.info(f"Created template {target} from the Starter Template")
    return CreatedTemplate(target, info.key, info)


# ── Thumbnails ──


def thumbs_root() -> Path:
    root = utils.data_root().joinpath(*THUMBS_DIR)
    utils.create_directory(root)
    return root


def thumbnail_path(info: TemplateInfo, width: int = THUMBNAIL_WIDTH) -> Path:
    stem = (
        info.content_hash
        if width == THUMBNAIL_WIDTH
        else f"{info.content_hash}-w{width}"
    )
    return thumbs_root() / f"{stem}.png"


def _require_gui_app() -> None:
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.instance() is None:
        raise ThumbnailUnavailableError(
            "Thumbnails need a QGuiApplication (QSvgRenderer/QImage); create one first."
        )


def thumbnail_svg_bytes(info: TemplateInfo) -> bytes:
    """The template prepared for QtSvg: no draw.io model, no footer."""
    from lxml import etree

    from joystick_diagrams.render.compose import strip_drawio_footer
    from joystick_diagrams.render.document import make_parser

    root = etree.fromstring(info.path.read_bytes(), make_parser())
    root.attrib.pop("content", None)
    strip_drawio_footer(root)
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


def _target_size(
    natural: tuple[float, float], size: tuple[int, int | None]
) -> tuple[int, int]:
    width, height = size
    natural_w, natural_h = natural
    if height is None:
        height = max(1, round(width * natural_h / natural_w)) if natural_w else width
    return max(1, int(width)), max(1, int(height))


def _render_generic_icon(width: int, height: int, path: Path) -> None:
    """A plain controller glyph for templates QtSvg cannot draw (and the Starter)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen

    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("#f4f5f7"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    unit = min(width, height) / 10
    pen = QPen(QColor("#5b6472"))
    pen.setWidthF(max(unit / 6, 1.0))
    painter.setPen(pen)
    painter.setBrush(QBrush(QColor("#d9dde3")))
    cx, cy = width / 2, height / 2
    # base
    painter.drawRoundedRect(
        QRectF(cx - 3 * unit, cy + unit, 6 * unit, 2.2 * unit), unit / 2, unit / 2
    )
    # stick
    painter.drawRoundedRect(
        QRectF(cx - 0.5 * unit, cy - 3 * unit, unit, 4.2 * unit), unit / 3, unit / 3
    )
    # grip top
    painter.drawEllipse(
        QRectF(cx - 1.2 * unit, cy - 4.2 * unit, 2.4 * unit, 1.8 * unit)
    )
    painter.end()
    image.save(str(path), "PNG")


def render_thumbnail(
    info: TemplateInfo, path: Path, size: tuple[int, int | None]
) -> None:
    """Render ``info`` to ``path`` now (no cache check). Needs a QGuiApplication."""
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    _require_gui_app()
    renderer = QSvgRenderer()
    loaded = False
    if not info.is_starter:
        try:
            loaded = renderer.load(QByteArray(thumbnail_svg_bytes(info)))
        except Exception as error:  # XML errors, unreadable files
            _logger.warning(f"Thumbnail for {info.path} fell back to the icon: {error}")
    if not loaded or not renderer.isValid():
        width, height = _target_size((4.0, 3.0), size)
        _render_generic_icon(width, height, path)
        return
    view_box = renderer.viewBoxF()
    natural = (
        (view_box.width(), view_box.height())
        if view_box.width() > 0 and view_box.height() > 0
        else (
            float(renderer.defaultSize().width() or 4),
            float(renderer.defaultSize().height() or 3),
        )
    )
    width, height = _target_size(natural, size)
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
    renderer.render(painter, QRectF(0, 0, width, height))
    painter.end()
    image.save(str(path), "PNG")


def thumbnail_for(
    info: TemplateInfo, size: tuple[int, int | None] = (THUMBNAIL_WIDTH, None)
) -> Path:
    """The cached PNG thumbnail for ``info`` (rendered on first use). See module doc."""
    path = thumbnail_path(info, size[0])
    if path.is_file():
        return path
    temp = path.with_suffix(".tmp.png")
    render_thumbnail(info, temp, size)
    temp.replace(path)
    return path


__all__ = [
    "CreatedTemplate",
    "FitResult",
    "TemplateInfo",
    "ThumbnailUnavailableError",
    "all_templates",
    "bound_controls",
    "bundled_templates",
    "clear_caches",
    "control_label",
    "create_from_starter",
    "find",
    "fit",
    "fit_text",
    "info_for_path",
    "makers",
    "missing_controls",
    "starter_template",
    "template_for",
    "thumbnail_for",
    "thumbnail_path",
    "user_templates",
]

if __name__ == "__main__":
    pass
