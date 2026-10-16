"""UI package exports."""

# MainWindow imports ``settings_page`` from this package. Point that public module
# name at the small extension so the existing settings implementation stays
# untouched while core export-text controls are added to the General tab.
from joystick_diagrams.ui import settings_page_extended as settings_page

__all__ = ["settings_page"]
