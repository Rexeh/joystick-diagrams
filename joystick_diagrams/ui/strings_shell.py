"""User-facing text for the four-stage shell: stage tabs, footer, banners,
status bar, the read popover (``docs/superpowers/specs/2026-10-25-ux-language.md``).
"""

from __future__ import annotations


def plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


# ── Window and menu ──
WINDOW_TITLE = "Joystick Diagrams - {version}"
MENU_HELP = "Help"
MENU_SUPPORT = "Support"
MENU_SUPPORT_TIP = "Get help on Discord"
MENU_OPEN_LOG_FOLDER = "Open log folder"
MENU_DETAILED_LOGGING = "Detailed logging (for bug reports)"
MENU_CHECK_FOR_UPDATES = "Check for updates"
MENU_ABOUT = "About Joystick Diagrams"
ABOUT_TITLE = "About Joystick Diagrams"
ABOUT_BODY = "Joystick Diagrams {version}\n\nDiagrams of your controllers, with your game bindings on them."
LINK_WEBSITE = "Website"
LINK_WEBSITE_TIP = "joystick-diagrams.com"
LINK_GITHUB = "GitHub"
LINK_GITHUB_TIP = "View the source on GitHub"
LINK_DISCORD = "Discord"
LINK_DISCORD_TIP = "Join the Discord community"
LINK_COFFEE = "Buy Me a Coffee"
LINK_COFFEE_TIP = "Support development"
SETTINGS_TIP = "Settings"

# ── Status bar ──
STATUS_APP_UP_TO_DATE = "App is up to date"
STATUS_UPDATE_AVAILABLE = "An update is available · joystick-diagrams.com"
STATUS_UPDATE_CHECK_FAILED = "Couldn't check for updates"
STATUS_READING_GAME = "Reading {game}…"
STATUS_READING_GAMES = "Reading your games…"

# ── Stage tabs: default statuses before a page exists ──
STATUS_PLACEHOLDER_BINDINGS = "Optional"
STATUS_PLACEHOLDER_BINDINGS_PROFILES = "Optional · {count} {profiles}"
STATUS_PLACEHOLDER_DIAGRAMS_NONE = "Nothing to export yet"
STATUS_PLACEHOLDER_DIAGRAMS_CHOOSE = "Choose templates first"
STATUS_PLACEHOLDER_DIAGRAMS_READY = "{count} {diagrams} ready"
STATUS_PLACEHOLDER_UNAVAILABLE = "Not available"

# ── Placeholder pages (stage 3 / 4 not installed) ──
PLACEHOLDER_BINDINGS = "Your bindings appear here once a game has been read."
PLACEHOLDER_DIAGRAMS = "Your diagrams appear here once a controller has a template."
PLACEHOLDER_GO_TO_SETUP = "‹ Go to 1. Setup"
PLACEHOLDER_GO_TO_CONTROLLERS = "‹ Go to 2. Controllers"

# ── Footer ──

# ── Background read ──
READ_POPOVER_KEPT = (
    "Your templates, labels, layouts and styles are kept. Only bindings are updated."
)
READ_POPOVER_UP_TO_DATE = "Up to date · read {time}"
READ_AGAIN = "Read again"
TURN_OFF_AUTOMATIC_READING = "Turn off automatic reading"
TURN_ON_AUTOMATIC_READING = "Turn on automatic reading"

BANNER_READ_FAILED = "Couldn't read {game} · your templates and layouts are kept"
BANNER_READ_FAILED_MANY = "Couldn't read {games} · your templates and layouts are kept"
BANNER_CHOOSE_FOLDER = "Choose folder…"
BANNER_NEW_CONTROLLER = "New controller found: {name}"
BANNER_NEW_CONTROLLER_DETAIL = "({game} · {count} {profiles})"
BANNER_NEW_CONTROLLER_DETAIL_NO_GAME = "({count} {profiles})"
BANNER_CHOOSE_TEMPLATE = "Choose template…"
BANNER_NO_DIAGRAM_NEEDED = "No diagram needed"
BANNER_DISMISS = "Dismiss"
BANNER_UPGRADE = (
    "Now in four stages: Setup, Controllers, Bindings, Diagrams. "
    "Your templates and labels are kept: templates are under 2. Controllers, "
    "Appearance and Layout under 4. Diagrams."
)
BANNER_UPGRADE_TURNED_OFF = (
    " {count} {controllers} you had turned off {are} under No diagram."
)
BANNER_UPGRADE_SHOW_ME = "Show me"

PROFILES = ("profile", "profiles")
DIAGRAMS = ("diagram", "diagrams")
CONTROLLERS = ("controller", "controllers")
GAMES = ("game", "games")

if __name__ == "__main__":
    pass
