"""User-facing text for 1. Setup (``ui/setup_page.py``): the first-launch game
picker, game cards, the folder card, the results card and the game-list dialogs
(``docs/superpowers/specs/2026-10-25-ux-language.md``, boards J01–J03, J14).
"""

from __future__ import annotations

# ── Page header ──
FIRST_LAUNCH_TITLE = "Which games do you play?"
FIRST_LAUNCH_SUBTITLE = (
    "Tick the games you want diagrams for. We only read their bindings; "
    "your games aren't changed."
)
GAMES_TITLE = "Your games"
GAMES_SUBTITLE = "Choose your games and where they keep their bindings."

# ── First-launch picker ──
PICKER_LOADING = "Finding games…"
PICKER_OFFLINE = (
    "We couldn't load the list of games. Check your internet connection, "
    "then try again."
)
PICKER_EMPTY = "No games are listed. Check your internet connection, then try again."
PICKER_TRY_AGAIN = "Try again"
PICKER_WILL_BE_ADDED = "Will be added"
PICKER_VERIFIED = "Verified"
PICKER_COMMUNITY = "Community"
PICKER_NEEDS_APP = "Needs Joystick Diagrams {version} or later"
PICKER_DONT_SEE = "Don't see your game?"
PICKER_ADD_FROM_FILE = "Add a game from a file…"
PICKER_ADD_FROM_FILE_TITLE = "Add a game from a file"
PICKER_ADD_FROM_FILE_FILTER = "Game files (*.zip)"
ADD_ONE_AND_CONTINUE = "Add {game} and continue ›"
ADD_MANY_AND_CONTINUE = "Add {count} games and continue ›"
ADD_NONE = "Choose a game to add"
FOOTER_HINT_FIRST_LAUNCH = "You can add or remove games here at any time."

# ── Game cards ──
CARD_VERIFIED = "Verified"
CARD_COMMUNITY = "Community"
CARD_VERIFIED_TIP = "Verified games are checked by the Joystick Diagrams team."
CARD_COMMUNITY_TIP = "Community games come from other players."
CARD_READ_THIS_GAME = "Read this game"
CARD_SETTINGS = "Settings…"
CARD_READ_AGAIN = "Read again"
CARD_CHOOSE_FOLDER = "Choose folder…"
CARD_CHOOSE_FILE = "Choose file…"
CARD_REMOVE_TIP = "Remove {game}"

CARD_STATUS_NEEDS_FOLDER = "Added · needs its folder"
CARD_STATUS_NEEDS_FILE = "Added · needs its file"
CARD_STATUS_NOT_READ = "Not read"
CARD_STATUS_TURNED_OFF = "Not read · turned off"
CARD_STATUS_READING = "Reading {game}…"
CARD_STATUS_READ = "{count} {profiles} · read {time}"
CARD_STATUS_NO_BINDINGS = "No bindings found · read {time}"
CARD_STATUS_FAILED = "Couldn't read {game}"

# ── Folder card ──
FOLDER_TITLE = "Where does {game} keep your bindings?"
FOLDER_FOUND = "Found"
FOLDER_ALSO_FOUND = "Also found"
FOLDER_LAST_CHANGED = "Last changed {date}"
FOLDER_USE_AND_READ = "Use this folder and read it"
FOLDER_USE_FILE_AND_READ = "Use this file and read it"
FOLDER_USE_INSTEAD = "Use this one instead"
FOLDER_NOT_RIGHT = "Not the right place?"
FOLDER_NONE_FOUND = "Choose the folder where {game} keeps your bindings."
FILE_NONE_FOUND = "Choose the file where {game} keeps your bindings."
FOLDER_ASKED_NEXT = "Added · needs its folder · asked next"
FOOTER_HINT_FOLDERS = (
    "Choose the folders first. After that, we read your games each time the app "
    "opens, so changed bindings show up on their own."
)
FOLDER_DIALOG_TITLE = "Where does {game} keep your bindings?"
FILE_DIALOG_TITLE = "Where does {game} keep your bindings?"
FILE_DIALOG_FILTER = "Game files ({patterns})"

# ── Reading ──
FOOTER_HINT_READING = "Stages 2 to 4 fill in when this finishes."

# ── Results card ──
RESULTS_TITLE = "We found {controllers} in {profiles}"
RESULTS_NEED_TEMPLATE = "need a template before they can be drawn"
RESULTS_NEED_TEMPLATE_ONE = "needs a template before it can be drawn"
RESULTS_NO_DIAGRAM = "set to No diagram"
RESULTS_NO_DIAGRAM_HINT = "(change this in 2. Controllers)"
RESULTS_READY = "ready"
RESULTS_READY_HINT = "(has a template)"
RESULTS_TEMPLATE_DEFINITION = (
    "A template is a picture of your controller with a box for each button, hat "
    "and axis. Your bindings are written into those boxes. Choosing one takes a "
    "few seconds."
)
RESULTS_NO_CONTROLLERS = "We didn't find any controllers in your bindings."

# ── Zero profiles (amber) ──
NO_BINDINGS_BODY = "We didn't find any bindings in {path}."
NO_BINDINGS_BODY_NO_PATH = "We didn't find any bindings for {game}."

# ── Failed read ──
READ_FAILED_BODY = "We couldn't read {game}: {detail}"
READ_FAILED_BODY_PLAIN = "We couldn't read {game}."
READ_FAILED_PATH_GONE = "{path} isn't there any more"
READ_FAILED_KEPT = "Your templates, labels and layouts are kept."
READ_FAILED_DETAILS = "Details"

# ── Add another game ──
ADD_ANOTHER_GAME = "+ Add another game"
GAME_UPDATES_AVAILABLE = "Updates for {count} {games} are available."
GAME_UPDATES_SEE = "See updates"

# ── Adding a game or other app (install flow messages) ──
ADD_FAILED_TITLE = "Couldn't add this game"
ADD_FAILED_TITLE_APP = "Couldn't add this app"
ADD_FAILED_DOWNLOAD = (
    "{name} couldn't be downloaded. Check your internet connection, then try again."
)
ADD_FAILED_FILE = (
    "This file couldn't be added. Check that it's a .zip file made for "
    "Joystick Diagrams, then try again."
)
ADD_FAILED_INVALID = "This file isn't a game Joystick Diagrams can read."
ADD_FAILED_INVALID_APP = (
    "This file isn't an app Joystick Diagrams can send diagrams to."
)
ADD_NAME_TAKEN = "A game named {name} is already included with the app."
DETAILS = "Details"

# ── Community check (before a game or app that isn't Verified is added) ──
COMMUNITY_TITLE = "Add a community game"
COMMUNITY_TITLE_APP = "Add a community app"
COMMUNITY_HEADING = "{name} isn't checked by the Joystick Diagrams team"
COMMUNITY_BODY = (
    "Game files run code on your computer: they can read, change or delete your "
    "files and use the internet. Only add {name} if you trust where it came from."
)
COMMUNITY_BODY_APP = (
    "App files run code on your computer: they can read, change or delete your "
    "files and use the internet. Only add {name} if you trust where it came from."
)
COMMUNITY_TRUST = "I trust where {name} came from"
COMMUNITY_ADD = "Add {name}"

# ── Game list dialog (games and other apps you can add) ──
STORE_TITLE = "Games and other apps"
STORE_INTRO = (
    "Verified games are checked by the Joystick Diagrams team. Community games "
    "come from other players; add them only if you trust the source."
)
STORE_LOADING = "Loading the list…"
STORE_OFFLINE = (
    "We couldn't load the list of games. Check your internet connection, "
    "then try again."
)
STORE_EMPTY = "There's nothing new to add."
STORE_CHECK_AGAIN = "Check again"
STORE_CLOSE = "Close"
STORE_ADD = "Add"
STORE_ADDED = "Added"
STORE_UPDATE = "Update to {version}"
STORE_UPDATE_TIP = "You have version {version}"
STORE_TYPE_GAME = "Game"
STORE_TYPE_APP = "Other app"
STORE_VERIFIED_TIP = "Checked by the Joystick Diagrams team"
STORE_COMMUNITY_TIP = "From another player. You're asked to confirm before it's added."
STORE_DONE = "✔ Added {name}"
STORE_VERSION = "Version {version}"

# ── Removing a game ──
REMOVE_TITLE = "Remove {game}?"
REMOVE_BODY = "Its folder and settings are kept if you add it again."
REMOVE_CONFIRM = "Remove {game}"
CANCEL = "Cancel"
REMOVE_FAILED = "Couldn't remove {game}"
REMOVE_FAILED_TEXT = (
    "Its files couldn't be deleted. Close any program using them, then try again."
)

# ── Settings panel ──
PANEL_CLOSE = "Close"
PANEL_VERSION = "Version {version}"
PANEL_FOLDER = "Folder"
PANEL_FOLDERS = "Folders"
PANEL_SETTINGS = "Settings"
PANEL_NOT_CHOSEN = "Not chosen"
PANEL_BROWSE = "Choose…"
PANEL_PATH_PROBLEM = "{game} can't use that: {detail}"
SAVED = "Saved"
CARD_READ_THIS_GAME_TIP = "Untick to leave this game out when reading"

# ── Next action ──
NEXT_CHOOSE_TEMPLATES = "Next: Choose {count} {templates} ›"
NEXT_CONTROLLERS = "Next: 2. Controllers ›"
NEXT_READ_ONE = "Read {game}"
NEXT_READ_MANY = "Read {count} games"

# ── Stage status ──
STATUS_CHOOSE_GAMES = "Choose your games"
STATUS_NEEDS_FOLDER = "{game} needs its folder"
STATUS_NEED_FOLDERS = "{count} games need their folders"
STATUS_READY_TO_READ = "Ready to read"
STATUS_READING = "Reading {game}…"
STATUS_READING_MANY = "Reading your games…"
STATUS_UP_TO_DATE = "Up to date · read {time}"
STATUS_UP_TO_DATE_NEW = "Up to date · read {time} · {count} new {controllers}"
STATUS_NO_BINDINGS = "No bindings in {game}"
STATUS_FAILED = "Couldn't read {game}"

PROFILES = ("profile", "profiles")
CONTROLLERS = ("controller", "controllers")
TEMPLATES = ("template", "templates")
GAMES = ("game", "games")


def plural(count: int, words: tuple[str, str]) -> str:
    return words[0] if count == 1 else words[1]


def counted(count: int, words: tuple[str, str]) -> str:
    return f"{count} {plural(count, words)}"


if __name__ == "__main__":
    pass
