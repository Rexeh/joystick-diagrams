"""User-facing text for 2. Controllers (``ui/controllers_page.py``) and the
template picker (``ui/template_picker.py``), boards J04–J06 and
``docs/superpowers/specs/2026-10-25-ux-language.md``.
"""

from __future__ import annotations

# ── Page ──
TITLE = "Your controllers"
SUBTITLE_CHOOSE = (
    "Choose a template for each one. This list comes from your game bindings, "
    "so a controller you haven't bound in any game won't be here."
)
SUBTITLE_ALL_SET = (
    "All set. Check which action is on each button in 3. Bindings, "
    "or go straight to 4. Diagrams."
)
SUBTITLE_NONE = (
    "This list comes from your game bindings. A controller you haven't bound "
    "in any game won't be here."
)
EMPTY_MESSAGE = "Your controllers appear here once we've read a game."
EMPTY_ACTION = "‹ Go to 1. Setup"
SELECT_A_CONTROLLER = "Choose a controller to see its template"

# ── Groups ──
GROUP_NEEDS_TEMPLATE = "Needs a template"
GROUP_READY = "Ready"
GROUP_NO_DIAGRAM = "No diagram"
GROUP_NOT_SEEN = "Not in your latest bindings"

# ── Rows ──
ROW_NO_TEMPLATE = "No template · {count} {profiles}"
ROW_TEMPLATE_MISSING = "Template {name} can't be found · {count} {profiles}"
ROW_READY = "{template} · {count} {profiles}"
ROW_READY_GAPS = "{template} · {count} {bindings} won't show"
ROW_NEW = "New"
ROW_NOT_SEEN = "Last read {date}"
ROW_NOT_SEEN_NO_DATE = "Not in your latest bindings"
ROW_MY_TEMPLATE = "{name} (My templates)"
GROUP_COUNT = "{group} ({count})"

# ── Detail: template section ──
SECTION_TEMPLATE = "Template"
TEMPLATE_NONE = "No template yet. Choose the one that matches this controller."
TEMPLATE_MISSING = "Template {name} can't be found. Choose it again or choose another."
TEMPLATE_UNREADABLE = "Template {name} can't be read. Choose another."
CHOOSE_TEMPLATE = "Choose template…"
CHANGE_TEMPLATE = "Change template…"
INCLUDED_WITH_APP = "Included with the app"
MY_TEMPLATES = "My templates"
PREVIEW = "Preview…"
EDIT_LAYOUT = "Edit layout ›"
VIEW_BINDINGS = "View bindings ›"
MISSING_CONTROLS = "{count} {controls} missing"
MISSING_CONTROLS_TIP = "Controls you use that have no box on this template"

# ── Detail: diagram, usage, more ──
MAKE_DIAGRAM = "Make a diagram for this controller"
MAKE_DIAGRAM_TIP = "Set by you. Untick to leave this controller out of every export."
REASON_SET_BY_YOU = "Set by you"
USED_IN = "Used in: {games}"
USED_IN_ENTRY = "{game} · {count} {profiles}"
USED_IN_NONE = "Not in your latest bindings"
MORE_SUMMARY = "More: Name on diagrams · Same controller as… · Controller ID"
NAME_ON_DIAGRAMS = "Name on diagrams"
NAME_RESET_TIP = "Use the game's name"
SAME_CONTROLLER_AS = "Same controller as"
SAME_CONTROLLER_NONE = "None"
SAME_CONTROLLER_HELP = "Its bindings go on that controller's diagram."
SAME_CONTROLLER_PROBLEM = (
    "That controller is already listed under another one. Choose that one instead."
)
CONTROLLER_ID = "Controller ID"
COPY_ID = "Copy controller ID (for support)"
COPIED = "Copied"
SAVED = "Saved"

# ── Next action ──
NEXT_BINDINGS = "Next: 3. Bindings ›"
SKIP_TO_BINDINGS = "Skip to 3. Bindings ›"
NEXT_DIAGRAMS = "Next: 4. Diagrams ›"
CHOOSE_N_TEMPLATES = "Choose {count} {templates}"
CHOOSE_N_TEMPLATES_TIP = "Choose a template for each controller under Needs a template."

# ── Stage status ──
STATUS_WAITING = "Found when a game is read"
STATUS_NEED_TEMPLATE = "{count} need a template"
STATUS_NEED_TEMPLATE_ONE = "1 needs a template"
STATUS_NEW_NEEDS_TEMPLATE = "{count} new · needs a template"
STATUS_ALL_READY = "All {count} ready"
STATUS_ONE_READY = "1 ready"
STATUS_NONE = "No controllers found"
STATUS_NO_DIAGRAMS = "All set to No diagram"

# ── Picker ──
PICKER_TITLE = 'Choose a template for "{name}"'
PICKER_TITLE_NO_DEVICE = "Choose a template"
PICKER_SEARCH = "Search"
PICKER_SEARCH_TIP = "Search by template or maker"
PICKER_SORT_BY_FIT = "Show best matches first"
PICKER_COUNTS_HELP = "Counts show how many controls you use are on each template."
PICKER_ALL_BY_MAKER = "All templates by maker"
PICKER_MY_TEMPLATES = "My templates"
PICKER_NO_RESULTS = 'No templates match "{query}"'
PICKER_FIT_PENDING = "Checking…"
PICKER_CANT_FIND = "Can't find yours?"
PICKER_USE_STARTER = "Use the Starter Template"
PICKER_STARTER_HELP = 'A plain template you can rearrange later in Layout. Saved to My templates as "{name}".'
PICKER_STARTER_HELP_NO_DEVICE = "A plain template you can rearrange later in Layout."
PICKER_COMMUNITY = "Find community templates ↗"
PICKER_COMMUNITY_URL = "https://joystick-diagrams.com/templates/"
PICKER_FROM_FILE = "Use a template file from this computer…"
PICKER_FILE_DIALOG_TITLE = "Choose a template file"
PICKER_FILE_FILTER = "Templates (*.svg)"
PICKER_PREVIEW_EMPTY = "Choose a template to see it here"
PICKER_FITS_ALL = (
    "Every control you use in your {count} {profiles} is on this template."
)
PICKER_FITS_ALL_NO_PROFILES = "Every control you use is on this template."
PICKER_NO_BINDINGS = "No bindings to check against."
PICKER_PARTIAL = "{fitted} of {total} controls you use are on this template."
PICKER_SHOW_MISSING = "{count} {controls} missing"
PICKER_HIDE_MISSING = "Hide the missing controls"
PICKER_CANCEL = "Cancel"
PICKER_USE = "Use this template"
PICKER_REMOVE = "Remove template"
PICKER_STARTER_FAILED = "The Starter Template couldn't be copied: {detail}"

PROFILES = ("profile", "profiles")
BINDINGS = ("binding", "bindings")
CONTROLS = ("control", "controls")
TEMPLATES = ("template", "templates")


def plural(count: int, words: tuple[str, str]) -> str:
    return words[0] if count == 1 else words[1]


def counted(count: int, words: tuple[str, str]) -> str:
    return f"{count} {plural(count, words)}"


def lower_first(text: str) -> str:
    """For a reason inside brackets: "keyboard (listed as a keyboard by …)"."""
    return text[:1].lower() + text[1:] if text else text


if __name__ == "__main__":
    pass
