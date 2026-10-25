"""Read-only Preview window (plan §5.5.6), opened from the Export page's
"Preview…": renders exactly what Export will produce for a device, with the
current style and layout, through ``export.render_template`` on the thread
pool, and shows it in a WebEngine view served over ``jdeditor://``.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.render import (
    Capability,
    Engine,
    RenderContext,
    RenderNotice,
    RenderOutcome,
    build_render_context,
)
from joystick_diagrams.ui import strings_layout as S
from joystick_diagrams.ui import ui_consts

_logger = logging.getLogger(__name__)

HELP_STYLE = "color: #9AA0A6; font-size: 12px; background: transparent;"
TOOL_STYLE = """
QToolButton {
    background: #2c2f38; color: #E8EAED; border: 1px solid #3C4043; border-radius: 4px;
    margin: 0px; padding: 4px 10px; min-height: 24px;
}
QToolButton:hover { background: #3C4043; border-color: #5F6368; }
"""
ZOOM_STEPS = (0.25, 0.33, 0.5, 0.67, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0)


class _Signals(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)


class _PreviewRunnable(QRunnable):
    def __init__(self, generation: int, export_device: Any, ctx: RenderContext):
        super().__init__()
        self.generation = generation
        self.export_device = export_device
        self.ctx = ctx
        self.signals = _Signals()

    @Slot()
    def run(self) -> None:
        from joystick_diagrams.export import render_template

        try:
            outcome = render_template(self.export_device, self.ctx)
        except Exception as e:  # noqa: BLE001 - render_template falls back itself
            _logger.error(f"Preview render failed: {e}", exc_info=True)
            self.signals.failed.emit(self.generation, str(e))
            return
        self.signals.done.emit(self.generation, outcome)


def summarise_outcome(outcome: RenderOutcome) -> str:
    report = outcome.report
    if RenderNotice.FELL_BACK_TO_LEGACY in report.notices:
        return S.PREVIEW_ENGINE_ORIGINAL + " " + S.NOTICE_UNSUPPORTED
    if report.engine is Engine.LEGACY:
        return S.PREVIEW_ENGINE_ORIGINAL
    text = S.PREVIEW_ENGINE_STYLED
    if Capability.SHAPE_STYLE not in report.capabilities:
        text += " " + S.UNSUPPORTED_BANNER
    extras = []
    if report.overflow:
        count = len(report.overflow)
        extras.append(S.REASON_OVERFLOW.format(count=count, s=S.plural(count)))
    if report.skipped_ops:
        count = len(report.skipped_ops)
        extras.append(S.REASON_SKIPPED.format(count=count, s=S.plural(count)))
    if RenderNotice.BOXES_UNPLACED in report.notices:
        extras.append(S.REASON_UNPLACED.format(count="some", es="es"))
    if extras:
        text += " (" + "; ".join(extras) + ")"
    return text


class PreviewWindow(QDialog):
    """``PreviewWindow(export_devices, current)``: one device, a profile picker, zoom."""

    edit_layout_requested = Signal(str)  # device id

    def __init__(
        self,
        export_devices: list[Any],
        current: Any,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowIcon(QIcon(ui_consts.JD_ICON))
        self.setWindowTitle(S.PREVIEW_TITLE.format(device=current.device_name))
        self.resize(1100, 760)
        self._devices = export_devices
        self._generation = 0
        self._view = None
        self._last_outcome: RenderOutcome | None = None
        self._pool = QThreadPool.globalInstance()
        self._zoom = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        header = QHBoxLayout()
        label = QLabel(S.PREVIEW_PROFILE)
        label.setStyleSheet(
            "color: #E8EAED; font-weight: bold; background: transparent;"
        )
        header.addWidget(label)
        self.profile_combo = QComboBox()
        self.profile_combo.setProperty("class", "view-binds-list")
        self.profile_combo.setMinimumWidth(240)
        for ed in export_devices:
            self.profile_combo.addItem(
                S.PREVIEW_ENTRY.format(
                    plugin=ed.profile_wrapper.profile_origin.name,
                    profile=ed.profile_wrapper.profile_name,
                )
            )
        self.profile_combo.setCurrentIndex(
            max(0, export_devices.index(current)) if current in export_devices else 0
        )
        self.profile_combo.currentIndexChanged.connect(lambda _i: self.render())
        header.addWidget(self.profile_combo)
        header.addStretch(1)
        self.zoom_out = self._tool("−", S.TOOL_ZOOM_OUT)
        self.zoom_out.clicked.connect(lambda: self.zoom_step(-1))
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet(
            "color: #E8EAED; min-width: 44px; background: transparent;"
        )
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_in = self._tool("+", S.TOOL_ZOOM_IN)
        self.zoom_in.clicked.connect(lambda: self.zoom_step(1))
        self.fit_button = self._tool(S.TOOL_ZOOM_FIT, S.TOOLTIP_ZOOM_FIT)
        self.fit_button.clicked.connect(self.fit)
        for widget in (self.zoom_out, self.zoom_label, self.zoom_in, self.fit_button):
            header.addWidget(widget)
        layout.addLayout(header)

        self.help_label = QLabel(S.PREVIEW_HELP)
        self.help_label.setStyleSheet(HELP_STYLE)
        layout.addWidget(self.help_label)

        self.view_host = QWidget()
        self.view_host.setStyleSheet(
            "background: #1a1d23; border: 1px solid #3C4043; border-radius: 6px;"
        )
        host_layout = QVBoxLayout(self.view_host)
        host_layout.setContentsMargins(1, 1, 1, 1)
        self.placeholder = QLabel(S.PREVIEW_RENDERING)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: #9AA0A6; font-style: italic;")
        host_layout.addWidget(self.placeholder)
        layout.addWidget(self.view_host, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(HELP_STYLE)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.edit_button = QPushButton(S.PREVIEW_EDIT_LAYOUT)
        self.edit_button.setProperty("class", "plugin-setup-button")
        self.edit_button.clicked.connect(self._on_edit_layout)
        buttons.addWidget(self.edit_button)
        buttons.addStretch(1)
        self.close_button = QPushButton(S.PREVIEW_CLOSE)
        self.close_button.setProperty("class", "plugin-setup-button")
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    @staticmethod
    def _tool(text: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setStyleSheet(TOOL_STYLE)
        return button

    # ── Rendering ──

    def current_export_device(self) -> Any:
        index = self.profile_combo.currentIndex()
        if 0 <= index < len(self._devices):
            return self._devices[index]
        return None

    def render(self) -> None:
        export_device = self.current_export_device()
        if export_device is None:
            return
        self._generation += 1
        self.status_label.setText(S.PREVIEW_RENDERING)
        runnable = _PreviewRunnable(
            self._generation, export_device, build_render_context()
        )
        runnable.signals.done.connect(self._on_rendered)
        runnable.signals.failed.connect(self._on_failed)
        self._pool.start(runnable)

    def render_synchronously(self) -> RenderOutcome | None:
        from joystick_diagrams.export import render_template

        export_device = self.current_export_device()
        if export_device is None:
            return None
        self._generation += 1
        outcome = render_template(export_device, build_render_context())
        self._on_rendered(self._generation, outcome)
        return outcome

    @property
    def last_outcome(self) -> RenderOutcome | None:
        return self._last_outcome

    def _on_rendered(self, generation: int, outcome: RenderOutcome) -> None:
        if generation != self._generation:
            return
        self._last_outcome = outcome
        self.status_label.setText(summarise_outcome(outcome))
        view = self._ensure_view()
        if view is not None:
            view.show_svg(outcome.svg_text)

    def _on_failed(self, generation: int, message: str) -> None:
        if generation != self._generation:
            return
        self.status_label.setText(S.RENDER_FAILED.format(error=message))

    def _ensure_view(self):
        if self._view is not None:
            return self._view
        try:
            from joystick_diagrams.ui.layout_editor.view import SvgDocumentView
        except ImportError as e:  # pragma: no cover
            _logger.error(f"QtWebEngine unavailable for the preview: {e}")
            self.placeholder.setText(S.WEBENGINE_UNAVAILABLE)
            return None
        self._view = SvgDocumentView(self.view_host)
        self._view.loadFinished.connect(lambda _ok: self.fit())
        host = self.view_host.layout()
        host.removeWidget(self.placeholder)
        self.placeholder.hide()
        host.addWidget(self._view)
        return self._view

    # ── Zoom ──

    def _set_zoom(self, factor: float) -> None:
        self._zoom = factor
        if self._view is not None:
            self._view.set_zoom(factor)
        self.zoom_label.setText(f"{round(factor * 100)}%")

    def zoom_step(self, direction: int) -> None:
        current = self._zoom
        if direction > 0:
            nxt = next((z for z in ZOOM_STEPS if z > current + 1e-6), ZOOM_STEPS[-1])
        else:
            nxt = next(
                (z for z in reversed(ZOOM_STEPS) if z < current - 1e-6), ZOOM_STEPS[0]
            )
        self._set_zoom(nxt)

    def fit(self) -> None:
        if self._view is None:
            return
        factor = self._view.fit_width()
        if factor is not None:
            self._set_zoom(factor)

    # ── Lifecycle ──

    def _on_edit_layout(self) -> None:
        export_device = self.current_export_device()
        if export_device is not None:
            self.edit_layout_requested.emit(export_device.device_id)
        self.close()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if self._last_outcome is None:
            self.render()

    def shutdown(self) -> None:
        self._generation += 1
        if self._view is not None:
            self._view.shutdown()
            self._view.setParent(None)
            self._view = None

    def closeEvent(self, event):  # noqa: N802
        self.shutdown()
        super().closeEvent(event)


if __name__ == "__main__":
    pass
