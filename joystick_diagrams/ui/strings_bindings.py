"""User-facing text for stage 3, Bindings (``ui/bindings_page.py`` and the
screens it wraps). Wording follows
``docs/superpowers/specs/2026-10-25-ux-language.md`` and journey board J07:
"binding", "controller", "label", "uses bindings from"; never "bind",
"device", "alias" or "inheritance" in UI text ("Shared bindings").
"""

from __future__ import annotations


def plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


# ── Page ──
TITLE = "Bindings"
INTRO = (
    "Optional. See which action is on each button, give actions shorter names for "
    "your diagrams, and let one profile reuse another's bindings."
)
NAV_BINDINGS = "Bindings"
NAV_SHARED = "Shared bindings"
NAV_LABELS = "Labels"
NEXT_DIAGRAMS = "Next: 4. Diagrams ›"
STATUS_OPTIONAL = "Optional"
STATUS_OPTIONAL_PROFILES = "Optional · {count} {profiles}"
PROFILES = ("profile", "profiles")
BINDINGS = ("binding", "bindings")

# ── Bindings screen ──
CONTROLLER = "Controller"
PROFILE = "Profile"
ALL_CONTROLLERS = "All controllers (by profile)"
PROFILE_ENTRY = "{game} / {profile} ({count} {bindings})"
SEARCH_PLACEHOLDER = "Search"
SEARCH_ACCESSIBLE = "Search bindings"
EDIT_LABEL = "Edit label"
EDIT_LABEL_TIP = "Change this action's text on your diagrams (F2)"
USE_GAME_TEXT = "Use the game's text"
COLUMN_CONTROL = "Control"
COLUMN_ACTION = "Action"
COLUMN_MODIFIER = "Modifier"
INHERITED_FROM = 'from "{profile}"'
NOTHING_BOUND = "nothing bound"
NO_DIAGRAM_SUFFIX = "No diagram"
SHOWN_AS = 'shown as "{label}"'
RELABEL_HINT = (
    "Double-click an action, or press F2 on it, to change its text on your "
    "diagrams. Your game isn't changed."
)
NO_MATCH = 'No bindings match "{query}"'
EMPTY = "Your bindings appear here once we've read a game."
EMPTY_ACTION = "‹ Go to 1. Setup"
NO_PROFILES_FOR_CONTROLLER = "No profile has bindings on {controller}."
INHERITED_NOTE = 'This binding comes from "{profile}".'
OPEN_SHARED = "Open Shared bindings"
GAME_TEXT_TIP = 'The game calls it "{action}"'
CONTROLLER_TIP = "Show the bindings on one controller"
PROFILE_TIP = "Profiles with bindings on this controller"

# ── Shared bindings screen ──
SHARED_INTRO = "Let one profile use another's bindings, such as a Common profile."
SHARED_LEARN_MORE = "Learn more"
SHARED_LEARN_MORE_URL = "https://joystick-diagrams.com/setup/profile-chaining/"
SHARED_PROFILE = "Profile"
USES_BINDINGS_FROM = "Uses bindings from"
USES_BINDINGS_FROM_HELP = (
    "Drag to reorder. Higher profiles win where both have a binding on a control."
)
ADD_SHARED_PROFILE = "Add a profile"
REMOVE = "Remove"
REMOVE_SHARED_PROFILE = "Stop using this profile's bindings"
NO_PROFILES_TO_ADD = "No other profiles to add"
CLASH_LABEL = "If a profile and the one it uses both have a binding on a control"
CLASH_KEEP = "Show this profile's binding only"
CLASH_CONCATENATE = "Show both on one line (A | B)"
CLASH_MODIFIER = "Show this profile's, list the other under it"
CLASH_SAVED = "Saved · bindings updated"

# ── Labels screen ──
LABELS_INTRO = (
    "Labels change an action's text on your diagrams. Your game isn't changed. "
    "Double-click a label to edit it."
)
LABELS_FILTER = "Only labels used on"
LABELS_FILTER_ALL = "All controllers"
COLUMN_LABEL = "Label"
LABEL_COUNT = "{count} {labels}"
LABELS = ("label", "labels")
LABELS_EMPTY = (
    "No labels yet. Double-click an action in Bindings to give it a shorter name."
)
LABELS_EMPTY_FILTERED = "No labels are used on {controller}."
LABELS_ACTION_PLACEHOLDER = "Action, as the game names it"
LABELS_LABEL_PLACEHOLDER = "Label for your diagrams"
LABELS_ADD = "Add"
LABELS_REMOVE_TIP = "Remove label"
LABELS_REMOVE_ALL = "Remove all labels"
LABELS_REMOVE_ALL_TITLE = "Remove all labels?"
LABELS_REMOVE_ALL_TEXT = "Every action goes back to the game's text on your diagrams. Your game isn't changed."
CANCEL = "Cancel"

if __name__ == "__main__":
    pass
