from joystick_diagrams.ui import settings_page
from joystick_diagrams.ui.settings_page_extended import SettingsPage


def test_ui_package_exposes_extended_settings_page():
    assert settings_page.SettingsPage is SettingsPage
