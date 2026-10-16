"""Live Chromium-backed SVG preview widgets for the Export page."""

import re
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QEvent, QSize, Qt, QTemporaryDir, QTimer, QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.export_text_layout import get_text_layout_options
from joystick_diagrams.ui.export_text_layout_settings import ExportTextLayoutSettings

_DIMENSION_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z%]*)")
_CSS_PX_PER_UNIT = {
    "": 1.0,
    "px": 1.0,
    "in": 96.0,
    "cm": 96.0 / 2.54,
    "mm": 96.0 / 25.4,
    "q": 96.0 / 101.6,
    "pt": 96.0 / 72.0,
    "pc": 16.0,
}


def _parse_dimension(value: str | None) -> float | None:
    if not value:
        return None
    match = _DIMENSION_RE.match(value)
    if not match:
        return None

    unit = match.group(2).casefold()
    multiplier = _CSS_PX_PER_UNIT.get(unit)
    if multiplier is None:
        return None

    try:
        return float(match.group(1)) * multiplier
    except ValueError:
        return None


def parse_svg_dimensions(svg_data: str) -> tuple[float, float]:
    """Return dimensions matching the SVG coordinate space used by Chromium.

    draw.io commonly stores physical ``width``/``height`` values (for example
    millimetres) alongside a pixel-like ``viewBox``. Fit calculations must use the
    viewBox first or the physical units can make the preview zoom to several hundred
    percent. Physical units are converted to CSS pixels only when no valid viewBox
    exists.
    """
    root_match = re.search(r"<svg\b(?P<attrs>[^>]*)>", svg_data, re.IGNORECASE)
    if not root_match:
        return (800.0, 600.0)

    attrs = root_match.group("attrs")

    def attribute(name: str) -> str | None:
        match = re.search(
            rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
            attrs,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return match.group(2) if match else None

    viewbox = attribute("viewBox")
    if viewbox:
        try:
            values = [float(value) for value in viewbox.replace(",", " ").split()]
            if len(values) == 4 and values[2] > 0 and values[3] > 0:
                return (values[2], values[3])
        except ValueError:
            pass

    width = _parse_dimension(attribute("width"))
    height = _parse_dimension(attribute("height"))
    if width and height:
        return (width, height)

    return (800.0, 600.0)


def wheel_navigation_mode(modifiers: Qt.KeyboardModifier) -> str:
    """Map wheel modifiers to Photoshop-style preview navigation."""
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        return "zoom"
    if modifiers & Qt.KeyboardModifier.AltModifier:
        return "horizontal"
    return "vertical"


def fit_zoom_factor(
    *,
    viewport_width: float,
    viewport_height: float,
    content_width: float,
    content_height: float,
    padding: float = 0.96,
) -> float:
    """Return the zoom needed to fit content inside a CSS-pixel viewport."""
    if min(viewport_width, viewport_height, content_width, content_height) <= 0:
        return 1.0

    factor = min(
        viewport_width / content_width,
        viewport_height / content_height,
    ) * padding
    return min(1.0, max(0.01, factor))


class _PreviewWebView(QWebEngineView):
    """QWebEngineView with Photoshop-style wheel navigation and drag-to-pan."""

    zoom_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panning = False
        self._last_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.installEventFilter(self)
        QTimer.singleShot(0, self.install_wheel_filters)

    def install_wheel_filters(self) -> None:
        """Intercept modified wheel gestures from Chromium's render widget."""
        targets = [self]
        focus_proxy = self.focusProxy()
        if focus_proxy is not None:
            targets.append(focus_proxy)
        targets.extend(self.findChildren(QWidget))

        for target in targets:
            target.installEventFilter(self)

    @staticmethod
    def _wheel_delta(event) -> int:
        pixel_delta = event.pixelDelta()
        if not pixel_delta.isNull():
            if pixel_delta.y() != 0:
                return pixel_delta.y()
            if pixel_delta.x() != 0:
                return pixel_delta.x()

        angle_delta = event.angleDelta()
        if angle_delta.y() != 0:
            return angle_delta.y()
        return angle_delta.x()

    def _handle_modified_wheel(self, event) -> bool:
        mode = wheel_navigation_mode(event.modifiers())
        if mode == "vertical":
            # Leave an unmodified wheel event entirely to Chromium so the page
            # scrolls naturally, including touchpad/inertial scrolling.
            return False

        delta = self._wheel_delta(event)
        if delta == 0:
            return False

        if mode == "zoom":
            self.zoom_requested.emit(1.15 if delta > 0 else 1 / 1.15)
        else:
            # Qt wheel-up is positive while browser scroll-right is positive, so
            # invert the wheel delta to match normal vertical scrolling direction.
            self.page().runJavaScript(f"window.scrollBy({-delta}, 0);")

        event.accept()
        return True

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Wheel and self._handle_modified_wheel(event):
            return True
        return super().eventFilter(watched, event)

    def wheelEvent(self, event) -> None:
        if self._handle_modified_wheel(event):
            return
        super().wheelEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self.install_wheel_filters)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = True
            self._last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning and self._last_pos is not None:
            delta = event.position() - self._last_pos
            self._last_pos = event.position()
            self.page().runJavaScript(
                f"window.scrollBy({-delta.x():.2f}, {-delta.y():.2f});"
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._panning:
            self._panning = False
            self._last_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class SvgPreviewView(QWidget):
    """Pan/zoom SVG view using Chromium for draw.io ``foreignObject`` support."""

    zoom_changed = Signal(int)
    load_failed = Signal()

    MIN_ZOOM = 0.10
    MAX_ZOOM = 5.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._web_view: _PreviewWebView | None = None
        self._svg_size = (800.0, 600.0)
        self._has_preview = False
        self._auto_fit = True
        self._zoom_factor = 1.0
        self._fit_request_id = 0
        self._temp_dir = QTemporaryDir()
        self._preview_path = (
            Path(self._temp_dir.path()) / "preview.svg"
            if self._temp_dir.isValid()
            else None
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(360, 280)

    @property
    def has_preview(self) -> bool:
        return self._has_preview

    def _ensure_web_view(self) -> _PreviewWebView:
        if self._web_view is not None:
            return self._web_view

        view = _PreviewWebView(self)
        view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        view.zoom_requested.connect(self._zoom_by)
        view.loadFinished.connect(self._on_load_finished)
        self._layout.addWidget(view)
        self._web_view = view
        return view

    def load_svg(self, svg_data: str) -> bool:
        """Render generated SVG through a private temporary file in Chromium.

        QWebEngine's ``setContent`` uses a data URL internally and is subject to a
        small URL-size limit. draw.io templates can be several megabytes, so the
        preview writes only to a QTemporaryDir and loads that file locally. The
        bytes are still exactly those returned by ``populate_template()``.
        """
        if re.search(r"<svg\b", svg_data, re.IGNORECASE) is None:
            self.clear_preview()
            return False
        if self._preview_path is None:
            self.clear_preview()
            return False

        try:
            self._preview_path.write_text(svg_data, encoding="utf-8")
        except OSError:
            self.clear_preview()
            return False

        self._svg_size = parse_svg_dimensions(svg_data)
        self._has_preview = True
        self._auto_fit = True
        self._fit_request_id += 1

        view = self._ensure_web_view()
        view.show()
        view.load(QUrl.fromLocalFile(str(self._preview_path.resolve())))
        return True

    def clear_preview(self) -> None:
        self._fit_request_id += 1
        self._has_preview = False
        self._auto_fit = True
        self._zoom_factor = 1.0
        if self._web_view is not None:
            self._web_view.hide()
        self.zoom_changed.emit(100)

    def fit_content(self) -> None:
        """Fit against Chromium's CSS viewport, avoiding Qt/HiDPI unit mismatch."""
        if not self._has_preview or self._web_view is None:
            return

        self._fit_request_id += 1
        request_id = self._fit_request_id
        self._auto_fit = True

        # Browser zoom changes window.innerWidth/innerHeight. Reset to 100% first,
        # then query Chromium's CSS-pixel viewport on the next event-loop turn.
        self._web_view.setZoomFactor(1.0)
        self._zoom_factor = 1.0

        def query_viewport() -> None:
            if request_id != self._fit_request_id or self._web_view is None:
                return
            self._web_view.page().runJavaScript(
                "({width: window.innerWidth, height: window.innerHeight})",
                lambda viewport: self._apply_fit_viewport(request_id, viewport),
            )

        QTimer.singleShot(0, query_viewport)

    def _apply_fit_viewport(self, request_id: int, viewport) -> None:
        if (
            request_id != self._fit_request_id
            or not self._has_preview
            or self._web_view is None
            or not isinstance(viewport, dict)
        ):
            return

        try:
            viewport_width = float(viewport["width"])
            viewport_height = float(viewport["height"])
        except (KeyError, TypeError, ValueError):
            return

        factor = fit_zoom_factor(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            content_width=self._svg_size[0],
            content_height=self._svg_size[1],
        )
        self._set_zoom_factor(factor, auto_fit=True)
        QTimer.singleShot(0, lambda: self._center_content(request_id))

    def _center_content(self, request_id: int) -> None:
        if request_id != self._fit_request_id or self._web_view is None:
            return
        self._web_view.page().runJavaScript(
            """
            (() => {
                const scroller = document.scrollingElement || document.documentElement;
                const left = Math.max(0, (scroller.scrollWidth - window.innerWidth) / 2);
                const top = Math.max(0, (scroller.scrollHeight - window.innerHeight) / 2);
                window.scrollTo(left, top);
            })();
            """
        )

    def zoom_in(self) -> None:
        self._zoom_by(1.2)

    def zoom_out(self) -> None:
        self._zoom_by(1 / 1.2)

    def _zoom_by(self, factor: float) -> None:
        if not self._has_preview:
            return
        self._fit_request_id += 1
        self._set_zoom_factor(self._zoom_factor * factor, auto_fit=False)

    def _set_zoom_factor(self, factor: float, *, auto_fit: bool) -> None:
        if self._web_view is None:
            return
        clamped = min(self.MAX_ZOOM, max(self.MIN_ZOOM, factor))
        self._zoom_factor = clamped
        self._auto_fit = auto_fit
        self._web_view.setZoomFactor(clamped)
        self.zoom_changed.emit(round(clamped * 100))

    def _on_load_finished(self, ok: bool) -> None:
        if not self._has_preview:
            return
        if not ok:
            self._has_preview = False
            self.load_failed.emit()
            return
        if self._web_view is not None:
            self._web_view.install_wheel_filters()
        if self._auto_fit:
            QTimer.singleShot(0, self.fit_content)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._auto_fit and self._has_preview:
            QTimer.singleShot(0, self.fit_content)


class ExportPreviewPanel(QWidget):
    """Collapsible text-layout controls and a preview-first SVG workspace."""

    settings_changed = Signal()
    PREFERRED_DEVICE_PANE_PX = 340
    DEFAULT_TEXT_LAYOUT_PANE_PX = 320

    def __init__(self, parent=None):
        super().__init__(parent)
        self._splitter_sized = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        header = QVBoxLayout()
        header.setSpacing(2)
        self.title_label = QLabel("Live preview")
        self.title_label.setStyleSheet("font-weight: 600;")
        header.addWidget(self.title_label)

        self.context_label = QLabel("Select a profile to preview its generated diagram")
        self.context_label.setObjectName("device_help_label")
        self.context_label.setWordWrap(True)
        header.addWidget(self.context_label)
        root.addLayout(header)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setOpaqueResize(True)
        self.content_splitter.setHandleWidth(8)

        self.controls_frame = QFrame()
        self.controls_frame.setMinimumWidth(260)
        self.controls_frame.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        controls_layout = QVBoxLayout(self.controls_frame)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(0)

        self.layout_settings = ExportTextLayoutSettings(
            self.controls_frame, compact=True
        )
        self.layout_settings.settings_changed.connect(self.settings_changed.emit)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        controls_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        controls_scroll.setWidget(self.layout_settings)
        controls_layout.addWidget(controls_scroll)
        self.controls_frame.hide()

        self.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)

        self.text_layout_btn = QPushButton("Text layout")
        self.text_layout_btn.setCheckable(True)
        self.text_layout_btn.setChecked(False)
        self.text_layout_btn.setToolTip("Show or hide live text layout controls")
        toolbar.addWidget(self.text_layout_btn)
        toolbar.addStretch(1)

        self.zoom_out_btn = QPushButton()
        self.zoom_out_btn.setFixedWidth(38)
        self.zoom_out_btn.setIcon(
            qta.icon("fa5s.search-minus", color="white", color_disabled="#6B7280")
        )
        self.zoom_out_btn.setIconSize(QSize(18, 18))
        self.zoom_out_btn.setToolTip("Zoom out (Ctrl + mouse wheel)")
        self.zoom_out_btn.setAccessibleName("Zoom out")
        toolbar.addWidget(self.zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(48)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.zoom_label)

        self.zoom_in_btn = QPushButton()
        self.zoom_in_btn.setFixedWidth(38)
        self.zoom_in_btn.setIcon(
            qta.icon("fa5s.search-plus", color="white", color_disabled="#6B7280")
        )
        self.zoom_in_btn.setIconSize(QSize(18, 18))
        self.zoom_in_btn.setToolTip("Zoom in (Ctrl + mouse wheel)")
        self.zoom_in_btn.setAccessibleName("Zoom in")
        toolbar.addWidget(self.zoom_in_btn)
        preview_layout.addLayout(toolbar)

        self.preview_stack = QStackedWidget()
        self.empty_label = QLabel("Select a profile with a template to preview it here.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setObjectName("device_help_label")
        self.preview_stack.addWidget(self.empty_label)

        self.svg_view = SvgPreviewView()
        self.svg_view.load_failed.connect(self._on_preview_load_failed)
        self.preview_stack.addWidget(self.svg_view)
        preview_layout.addWidget(self.preview_stack, 1)

        self.status_label = QLabel("Preview uses the exact SVG export pipeline.")
        self.status_label.setObjectName("device_help_label")
        self.status_label.setWordWrap(True)
        preview_layout.addWidget(self.status_label)

        self.content_splitter.addWidget(self.controls_frame)
        self.content_splitter.addWidget(self.preview_frame)
        self.content_splitter.setStretchFactor(0, 0)
        self.content_splitter.setStretchFactor(1, 1)
        root.addWidget(self.content_splitter, 1)

        self.text_layout_btn.toggled.connect(self._set_text_layout_visible)
        self.zoom_out_btn.clicked.connect(self.svg_view.zoom_out)
        self.zoom_in_btn.clicked.connect(self.svg_view.zoom_in)
        self.svg_view.zoom_changed.connect(self._on_zoom_changed)

        self.show_empty("Select a profile to preview its generated diagram.")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._splitter_sized:
            return

        splitter = self.parentWidget()
        if not isinstance(splitter, QSplitter) or splitter.count() < 2:
            return

        total_width = max(splitter.width(), sum(splitter.sizes()))
        if total_width <= 0:
            return

        device_width = min(
            self.PREFERRED_DEVICE_PANE_PX,
            max(280, total_width - self.svg_view.minimumWidth()),
        )
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([device_width, max(1, total_width - device_width)])
        self._splitter_sized = True

    def reload_settings(self) -> None:
        self.layout_settings.reload_from_settings()

    def _set_text_layout_visible(self, visible: bool) -> None:
        self.controls_frame.setVisible(visible)
        if visible:
            total_width = max(
                self.content_splitter.width(), sum(self.content_splitter.sizes())
            )
            if total_width > 0:
                controls_width = min(
                    self.DEFAULT_TEXT_LAYOUT_PANE_PX,
                    max(260, total_width - self.svg_view.minimumWidth()),
                )
                self.content_splitter.setSizes(
                    [controls_width, max(1, total_width - controls_width)]
                )

        # Let the Chromium viewport settle before recomputing a fitted preview.
        if self.svg_view.has_preview and self.svg_view._auto_fit:
            QTimer.singleShot(0, self.svg_view.fit_content)

    def set_context(
        self,
        device_name: str,
        profile_name: str,
        template_name: str | None,
        warning_count: int = 0,
    ) -> None:
        template_text = template_name or "No template"
        self.context_label.setText(
            f"{device_name} · {profile_name} · {template_text}"
        )
        options = get_text_layout_options()
        mode = "Auto-fit ON" if options.enabled else "Auto-fit OFF"
        warning_text = (
            f" · {warning_count} template warning{'s' if warning_count != 1 else ''}"
            if warning_count
            else ""
        )
        self.status_label.setText(
            f"{mode} · live Chromium preview · exact export pipeline{warning_text}"
        )

    def show_svg(self, svg_data: str) -> bool:
        if not self.svg_view.load_svg(svg_data):
            self.show_empty("The generated SVG could not be loaded for preview.")
            return False
        self.preview_stack.setCurrentWidget(self.svg_view)
        self._set_zoom_controls_enabled(True)
        return True

    def show_empty(self, message: str) -> None:
        self.svg_view.clear_preview()
        self.empty_label.setText(message)
        self.preview_stack.setCurrentWidget(self.empty_label)
        self._set_zoom_controls_enabled(False)

    def _on_preview_load_failed(self) -> None:
        self.show_empty("Chromium could not render the generated SVG preview.")

    def _set_zoom_controls_enabled(self, enabled: bool) -> None:
        self.zoom_out_btn.setEnabled(enabled)
        self.zoom_in_btn.setEnabled(enabled)

    def _on_zoom_changed(self, percent: int) -> None:
        self.zoom_label.setText(f"{percent}%")
