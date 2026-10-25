"""User-facing text for 4. Diagrams › Appearance (plan §5.5.9: one module, no
i18n infrastructure yet).

Rules followed here: never "alias", "canonical" or "Template original"; the
first style is always "Original (unchanged)"; wording is plain language.
"""

from joystick_diagrams.render.theme import ORIGINAL_THEME_NAME

# ── Navigation ──
NAV_APPEARANCE = "Appearance"
TAB_STYLE = "Style"
TAB_MODIFIER_KEYS = "Modifier keys"

# ── Style tab ──
STYLE_GALLERY_HEADING = "Choose a style"
STYLE_GALLERY_HELP = (
    "Applies to every diagram you export. Your template files aren't changed."
)
ORIGINAL_CARD_TITLE = ORIGINAL_THEME_NAME
ORIGINAL_CARD_BLURB = "Exactly as the template was drawn."
BUILTIN_BLURBS = {
    "clean": "Tidy dark-grey text, softer borders, faded empty boxes.",
    "print_friendly": "Black on white for printing; empty boxes stay quiet.",
    "high_contrast": "Bold text, heavy borders and shaded empty boxes for kneeboards.",
}
USER_STYLE_BLURB = "Your own adjustments."
CARD_IN_USE = "In use"
CARD_BASED_ON = "Based on {base}"

SHOWING_MODIFIERS_HEADING = "Showing modifiers"
SHOWING_MODIFIERS_HELP = (
    "Modifier bindings need a key held, such as Shift + Button 1. "
    "Most templates have no boxes for them."
)
SHOWING_TEMPLATE_BOXES = "Only where the template has modifier boxes"
SHOWING_TEMPLATE_BOXES_HELP = (
    "Controls without modifier boxes show only their main binding."
)
SHOWING_UNDER_MAIN_TEXT = "Add them under the main text (works on every template)"
SHOWING_UNDER_MAIN_TEXT_HELP = (
    "Each modifier on its own line, coloured by its key when colouring is on."
)
SHOWING_MERGED_SAME_LINE = "Add them to the main text on one line"
SHOWING_MERGED_SAME_LINE_HELP = 'Joined to the main binding with " | ".'

EDITOR_HEADING = "Adjust this style"
EDITOR_ORIGINAL_HINT = "Choose another style to change fonts, colours and borders."
EDITOR_COPY_NOTE = "Changing a built-in style creates your own copy of it."
FIELD_FONT = "Font"
FIELD_FONT_TEMPLATE = "Template font"
FIELD_RADIUS_TEMPLATE = "Template corners"
FIELD_WIDTH_TEMPLATE = "Template width"
FIELD_FONT_SIZE = "Text size"
FIELD_FONT_SIZE_TEMPLATE = "Template size"
FIELD_TEXT_COLOUR = "Text colour"
FIELD_BOX_COLOUR = "Box border"
FIELD_BOX_RADIUS = "Corner radius"
FIELD_UNBOUND = "Empty boxes"
UNBOUND_TEMPLATE = "As the template"
UNBOUND_FADED = "Faded border and text"
UNBOUND_LIGHT_FILL = "Faded with a light fill"
FIELD_LEADER_COLOUR = "Leader lines"
FIELD_LEADER_WIDTH = "Line width"
COLOUR_TEMPLATE = "Template colour"
BUTTON_RESET_TO = "Reset to {base}"
BUTTON_DELETE_STYLE = "Delete this style"
BUTTON_USE_FOR_EXPORTS = "Use for all exports"
BUTTON_IN_USE = "Used for all exports"
FONT_GAP_NOTE = "This font shows only on computers that have it installed."

PREVIEW_HEADING = "Preview with:"
PREVIEW_DEVICE_PROFILE = "{controller} · {profile}"
PREVIEW_EMPTY = "Showing a sample. Choose a template in 2. Controllers to see your own diagram here."
PREVIEW_EMPTY_ACTION = "Choose a template"
PREVIEW_RENDERING = "Updating preview…"
PREVIEW_FAILED = "The preview couldn't be drawn. Details are in Help › Open log folder."
PREVIEW_LIMITED = (
    "Only the text takes this style; this template's boxes and lines keep their look."
)
PREVIEW_FELL_BACK = "This template can't take styles, so it's shown as drawn."
PREVIEW_OVERFLOW = (
    "{count} {controls} had more modifier bindings than boxes; all of them are "
    "still listed under the main text."
)
CONTROLS = ("control", "controls")

# ── Modifier keys tab ──
COLOUR_BY_KEY_HEADING = "Colour by modifier key"
COLOUR_BY_KEY_CHANGE = "· change them on the Modifier keys tab"
COLOUR_BY_KEY_HELP = (
    "Give every modifier key its own colour so Shift, Ctrl and Alt bindings are "
    "easy to tell apart. Key names are always printed, so black and white prints "
    "still read fine."
)
SIDES_SAME = "Treat left and right keys as the same"
SIDES_SAME_HELP = "LShift and RShift share one colour and one group."
KEY_NAMES_HEADING = "Show key names:"
KEY_NAMES_ORIGINAL = "As in the game (LShift)"
KEY_NAMES_SIMPLIFIED = "Simplified (L Shift)"
PRIORITY_HELP = (
    "When a binding uses several keys (Ctrl+Shift), its box takes the colour of "
    "the key highest in this list."
)
GROUPS_HEADING = "Keys found in your profiles"
COLUMN_ORDER = "Order"
COLUMN_COLOUR = "Colour"
COLUMN_GROUP = "Group"
COLUMN_KEYS = "Keys found in your profiles"
MOVE_UP_NAMED = "Move {name} up"  # accessible name / tooltip of the order buttons
MOVE_DOWN_NAMED = "Move {name} down"
CONTROLLER_BUTTONS_GROUP = "Controller buttons"
DEVICE_BUTTONS_HINT = "This number means a different button on each controller."
NO_KEYS_SEEN = "None in your profiles"
KEY_CHIP = "{key} · seen in {games} · {count} binding{s}"
OTHER_LABELS_HEADING = "Profile and controller names"
OTHER_LABELS_HELP = "These are names, not keys, so they are never coloured."
OTHER_LABELS_NONE = "None in your profiles."
UNGROUPED_HEADING = "Keys without a group"
UNGROUPED_HELP = "These keys are shown but not coloured."
BUTTON_RESTORE_DEFAULTS = "Restore defaults"
RESTORE_DEFAULTS_TITLE = "Restore the default key colours?"
RESTORE_DEFAULTS_CONFIRM = (
    "The key groups, colours and order go back to the defaults. "
    "Your own groups are kept."
)
CANCEL = "Cancel"
LOW_CONTRAST = "Hard to read. Text uses a darker shade of this colour."
MORE_COLOURS = "More colours…"
SWATCH_NAMES = {
    "#0072B2": "Blue",
    "#D55E00": "Vermilion",
    "#009E73": "Green",
    "#CC79A7": "Pink",
    "#E69F00": "Orange",
    "#56B4E9": "Sky blue",
    "#F0E442": "Yellow",
    "#000000": "Black",
}
