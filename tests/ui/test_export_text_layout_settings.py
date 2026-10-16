from joystick_diagrams.db.db_settings import get_setting
from joystick_diagrams.export_text_layout import (
    TEXT_FONT_SIZE_SETTING_KEY,
    TEXT_LAYOUT_ENABLED_SETTING_KEY,
    TEXT_MAX_CHARS_SETTING_KEY,
    TEXT_MIN_FONT_SIZE_SETTING_KEY,
)
from joystick_diagrams.ui.export_text_layout_settings import ExportTextLayoutSettings


def test_text_layout_settings_default_to_disabled(qtbot):
    widget = ExportTextLayoutSettings()
    qtbot.addWidget(widget)

    assert widget.enabled_cb.isChecked() is False
    assert widget.font_size_spin.isEnabled() is False
    assert widget.max_chars_spin.isEnabled() is False
    assert widget.min_font_size_spin.isEnabled() is False


def test_enabling_text_layout_enables_controls_and_persists(qtbot):
    widget = ExportTextLayoutSettings()
    qtbot.addWidget(widget)

    # setChecked() is deterministic even when the widget is not shown. Using a
    # synthetic mouse click on a hidden widget is platform-dependent on Qt/Windows.
    widget.enabled_cb.setChecked(True)

    assert widget.enabled_cb.isChecked() is True
    assert widget.font_size_spin.isEnabled() is True
    assert widget.max_chars_spin.isEnabled() is True
    assert widget.min_font_size_spin.isEnabled() is True
    assert get_setting(TEXT_LAYOUT_ENABLED_SETTING_KEY) == "true"


def test_numeric_text_layout_settings_are_persisted(qtbot):
    widget = ExportTextLayoutSettings()
    qtbot.addWidget(widget)

    widget.enabled_cb.setChecked(True)
    widget.font_size_spin.setValue(11)
    widget.max_chars_spin.setValue(22)
    # The default minimum is 7, so choose a different value to ensure
    # QSpinBox.valueChanged is emitted and persistence is exercised.
    widget.min_font_size_spin.setValue(6)

    assert get_setting(TEXT_FONT_SIZE_SETTING_KEY) == "11"
    assert get_setting(TEXT_MAX_CHARS_SETTING_KEY) == "22"
    assert get_setting(TEXT_MIN_FONT_SIZE_SETTING_KEY) == "6"


def test_wrap_and_shrink_toggle_dependent_controls(qtbot):
    widget = ExportTextLayoutSettings()
    qtbot.addWidget(widget)
    widget.enabled_cb.setChecked(True)

    assert widget.max_lines_spin.isEnabled() is True
    assert widget.min_font_size_spin.isEnabled() is True

    widget.wrap_cb.setChecked(False)
    assert widget.max_lines_spin.isEnabled() is False
    assert widget.ellipsis_cb.isEnabled() is False

    widget.shrink_cb.setChecked(False)
    assert widget.min_font_size_spin.isEnabled() is False
