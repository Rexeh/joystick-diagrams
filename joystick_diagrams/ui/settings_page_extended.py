"""Settings page extension that adds export text layout controls.

Kept separate from the large plugin-management settings page so the text-layout
feature remains isolated and easy to review.
"""

from joystick_diagrams.ui.export_text_layout_settings import ExportTextLayoutSettings
from joystick_diagrams.ui.settings_page import SettingsPage as BaseSettingsPage


class SettingsPage(BaseSettingsPage):
    """Core settings page with the export text layout section appended."""

    def _create_general_tab(self):
        tab = super()._create_general_tab()
        layout = tab.layout()
        insert_at = max(0, layout.count() - 1)
        self.export_text_layout_settings = ExportTextLayoutSettings(tab)
        layout.insertWidget(insert_at, self.export_text_layout_settings)
        return tab

    def refresh(self):
        super().refresh()
        if hasattr(self, "export_text_layout_settings"):
            self.export_text_layout_settings.reload_from_settings()
