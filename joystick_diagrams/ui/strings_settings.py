"""User-facing text for Settings (the cog at the end of the stage strip):
General and Other apps (``ui/settings_page.py``), the other-app cards
(``ui/widgets/plugin_card.py``) and the drop zone. Wording follows
``docs/superpowers/specs/2026-10-25-ux-language.md``: output plugins are
"other apps"; games are added and removed in 1. Setup.
"""

from __future__ import annotations

# ── Navigation ──
NAV_GENERAL = "General"
NAV_OTHER_APPS = "Other apps"

# ── General ──
DATE_ON_DIAGRAMS = "Date on diagrams"
AUTO_READ = "Read my games each time the app opens"
AUTO_READ_TIP = "Changed bindings show up on their own. Reading never blocks the app."
LISTED_TWICE = "If a controller listed twice has two bindings on one control"
LISTED_TWICE_CONCATENATE = "Show both on one line (A | B)"
LISTED_TWICE_MODIFIER = "Show one, list the other under it"
SAVED_BINDINGS_UPDATED = "Saved · bindings updated"
MODIFIERS_POINTER = (
    "How modifier bindings are shown is chosen in 4. Diagrams › Appearance."
)
GO_TO_APPEARANCE = "Go to Appearance ›"
GAMES_POINTER = "Games are added, removed and given their folders in 1. Setup."
GO_TO_SETUP = "Go to 1. Setup ›"

# ── Other apps ──
OTHER_APPS_INTRO = (
    "Other apps get your diagrams after each export, such as OpenKneeboard."
)
ADD_APP_FROM_FILE = "Add an app from a file…"
ADD_APP_FROM_FILE_TITLE = "Add an app from a file"
ADD_APP_FILE_FILTER = "App files (*.zip)"
ADD_APP_FROM_WEB = "Add from a web address…"
ADD_APP_FROM_WEB_TITLE = "Add an app from a web address"
ADD_APP_FROM_WEB_LABEL = "Web address of the app's .zip file:"
OPEN_APPS_FOLDER = "Open the apps folder"
DROP_APP_HERE = "Drop an app's .zip file here"
OTHER_APPS_EMPTY = (
    "No other apps added. Add one from a file, or drop its .zip file here."
)
APP_ADDED = "✔ Added {app}"
APP_REMOVED = "✔ Removed {app}"
NAME_TAKEN = (
    "Skipped {names}: an app with the same name is included with Joystick Diagrams."
)

REMOVE_TITLE = "Remove {app}?"
REMOVE_BODY = "Its settings are kept if you add it again."
REMOVE_CONFIRM = "Remove {app}"
CANCEL = "Cancel"
REMOVE_FAILED_TITLE = "Couldn't remove {app}"
REMOVE_FAILED_TEXT = (
    "The app's files couldn't be deleted. Close any program using them, then try again."
)
DETAILS = "Details"

# ── App cards ──
CARD_INCLUDED = "Included with the app"
CARD_VERIFIED = "Verified"
CARD_TRUSTED = "Community · you chose to trust it"
CARD_COMMUNITY = "Community"
CARD_ADDED_BY_YOU = "Added by you"
CARD_READY = "Ready"
CARD_NEEDS_SETUP = "Needs setting up"
CARD_SEND_TO = "Send diagrams to this app"
CARD_SETTINGS = "Settings…"
CARD_REMOVE_TIP = "Remove {app}"
CARD_VERSION = "Version {version}"


if __name__ == "__main__":
    pass
