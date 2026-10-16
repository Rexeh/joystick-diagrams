import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from joystick_diagrams.ui.export_preview import (
    ExportPreviewPanel,
    SvgPreviewView,
    fit_zoom_factor,
    parse_svg_dimensions,
    wheel_navigation_mode,
)


def test_parse_svg_dimensions_prefers_viewbox_over_physical_size():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="396.35mm" height="206.38mm" '
        'viewBox="0 0 1498 780"></svg>'
    )

    assert parse_svg_dimensions(svg) == (1498.0, 780.0)


def test_parse_svg_dimensions_converts_physical_units_without_viewbox():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="25.4mm" height="2.54cm">'
        "</svg>"
    )

    width, height = parse_svg_dimensions(svg)
    assert width == pytest.approx(96.0)
    assert height == pytest.approx(96.0)


def test_parse_svg_dimensions_uses_explicit_pixel_size_without_viewbox():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1498" height="780"></svg>'

    assert parse_svg_dimensions(svg) == (1498.0, 780.0)


def test_parse_svg_dimensions_falls_back_to_default():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

    assert parse_svg_dimensions(svg) == (800.0, 600.0)


def test_wheel_without_modifier_uses_vertical_scroll():
    assert wheel_navigation_mode(Qt.KeyboardModifier.NoModifier) == "vertical"


def test_alt_wheel_uses_horizontal_scroll():
    assert wheel_navigation_mode(Qt.KeyboardModifier.AltModifier) == "horizontal"


def test_ctrl_wheel_uses_zoom():
    assert wheel_navigation_mode(Qt.KeyboardModifier.ControlModifier) == "zoom"


def test_ctrl_takes_priority_when_ctrl_and_alt_are_held():
    modifiers = (
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
    )

    assert wheel_navigation_mode(modifiers) == "zoom"


def test_fit_zoom_factor_fits_entire_svg_inside_css_viewport():
    factor = fit_zoom_factor(
        viewport_width=900,
        viewport_height=450,
        content_width=1498,
        content_height=780,
    )

    assert factor == pytest.approx((450 / 780) * 0.96)


def test_fit_zoom_factor_never_magnifies_above_native_size():
    factor = fit_zoom_factor(
        viewport_width=1600,
        viewport_height=1000,
        content_width=800,
        content_height=600,
    )

    assert factor == 1.0


def test_svg_preview_creates_webengine_lazily(qtbot):
    view = SvgPreviewView()
    qtbot.addWidget(view)

    assert view.has_preview is False
    assert view._web_view is None
    assert view.load_svg("not svg") is False
    assert view._web_view is None


def test_preview_panel_context_reports_warnings(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    panel.set_context("X52 Pro", "Default", "x52.svg", warning_count=2)

    assert "X52 Pro" in panel.context_label.text()
    assert "2 template warnings" in panel.status_label.text()
    assert panel.svg_view._web_view is None


def test_preview_panel_prefers_compact_device_pane():
    assert ExportPreviewPanel.PREFERRED_DEVICE_PANE_PX == 340


def test_text_layout_panel_is_collapsed_by_default(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    assert panel.text_layout_btn.isCheckable() is True
    assert panel.text_layout_btn.isChecked() is False
    assert panel.controls_frame.isHidden() is True


def test_text_layout_and_preview_are_separated_by_resizable_splitter(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    assert isinstance(panel.content_splitter, QSplitter)
    assert panel.content_splitter.count() == 2
    assert panel.content_splitter.widget(0) is panel.controls_frame
    assert panel.content_splitter.widget(1) is panel.preview_frame
    assert panel.content_splitter.childrenCollapsible() is False
    assert panel.controls_frame.maximumWidth() > 360


def test_text_layout_button_toggles_controls_without_hiding_preview(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    panel.text_layout_btn.click()

    assert panel.controls_frame.isHidden() is False
    assert panel.preview_stack.isVisibleTo(panel) is True

    panel.text_layout_btn.click()

    assert panel.controls_frame.isHidden() is True


def test_preview_panel_forwards_text_layout_changes(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)
    changes = []
    panel.settings_changed.connect(lambda: changes.append(True))

    panel.layout_settings.enabled_cb.setChecked(True)

    assert changes


def test_preview_toolbar_has_no_fit_button(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    assert not hasattr(panel, "fit_btn")


def test_preview_zoom_buttons_use_magnifier_icons(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    assert panel.zoom_out_btn.text() == ""
    assert panel.zoom_in_btn.text() == ""
    assert panel.zoom_out_btn.icon().isNull() is False
    assert panel.zoom_in_btn.icon().isNull() is False
