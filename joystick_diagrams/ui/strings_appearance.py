"""User-facing text for the Appearance screens, the Export style row and the
settings pointer (plan §5.5.9: one module, no i18n infrastructure yet).

Rules followed here: never "alias", "canonical" or "Template original"; the
first style is always "Original (unchanged)"; wording is plain language.
"""

from joystick_diagrams.render.theme import ORIGINAL_THEME_NAME

# ── Navigation ──
NAV_APPEARANCE = "Appearance"
CUSTOMISE_SUBTITLE = (
    "View binds, edit labels, manage devices and inheritance, "
    "and change how your diagrams look"
)
TAB_STYLE = "Style"
TAB_MODIFIER_KEYS = "Modifier keys"

# ── Style tab ──
STYLE_GALLERY_HEADING = "Choose a style"
STYLE_GALLERY_HELP = (
    "Styles change fonts, colours and box borders on every diagram you export. "
    "Pick one, adjust it on the right, then use it for all exports."
)
ORIGINAL_CARD_TITLE = ORIGINAL_THEME_NAME
ORIGINAL_CARD_BLURB = (
    "Exactly as the template was designed; your diagrams look the same as before."
)
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
    "Modifier bindings are the ones that need a key held (Shift + button). "
    "Most templates have no space set aside for them."
)
SHOWING_TEMPLATE_BOXES = "Only where the template has modifier boxes"
SHOWING_TEMPLATE_BOXES_HELP = (
    "Today's behaviour. Controls without boxes show only their main binding."
)
SHOWING_UNDER_MAIN_TEXT = "Add them under the main text"
SHOWING_UNDER_MAIN_TEXT_HELP = (
    "Each modifier on its own line, coloured by its key when colouring is on."
)
SHOWING_MERGED_SAME_LINE = "Add them to the main text on one line"
SHOWING_MERGED_SAME_LINE_HELP = (
    'Joined with " | ", as the old "Merge modifiers" option did.'
)

EDITOR_HEADING = "Adjust this style"
EDITOR_ORIGINAL_HINT = (
    "Original (unchanged) keeps every template exactly as designed. "
    "Pick another style to adjust fonts, colours and borders."
)
EDITOR_COPY_NOTE = "Changing a built-in style creates your own copy of it."
FIELD_FONT = "Font"
FIELD_FONT_TEMPLATE = "Template font"
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
FONT_GAP_NOTE = (
    "Fonts are not bundled yet: a font only shows in PNG exports and previews "
    "when it is installed on this computer. SVGs keep the font name."
)

PREVIEW_HEADING = "Preview with:"
PREVIEW_DEVICE_PROFILE = "{device} · {profile}"
PREVIEW_EMPTY = "Pick a template for a device to see your diagram here"
PREVIEW_EMPTY_ACTION = "Choose a template"
PREVIEW_RENDERING = "Updating preview…"
PREVIEW_ORIGINAL = "Showing the template exactly as designed."
PREVIEW_STYLED = "Styled with {style}."
PREVIEW_LIMITED = (
    "Style: limited — this template only supports text styling "
    "(boxes and lines keep their original look)."
)
PREVIEW_FELL_BACK = (
    "This template isn't supported for styling yet; it is shown with its original look."
)
PREVIEW_OVERFLOW = (
    "{count} control(s) had more modifiers than space — all are still listed in "
    "the control's modifier list."
)

# ── Modifier keys tab ──
COLOUR_BY_KEY_HEADING = "Colour by modifier key"
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
    "When a bind uses several keys (Ctrl+Shift), the box takes the colour of the "
    "key highest in this list."
)
GROUPS_HEADING = "Keys found in your profiles"
COLUMN_ORDER = "Order"
COLUMN_COLOUR = "Colour"
COLUMN_GROUP = "Group"
COLUMN_KEYS = "Keys found in your profiles"
MOVE_UP = "Move up"
MOVE_DOWN = "Move down"
MOVE_UP_NAMED = "Move {name} up"  # accessible name / tooltip of the order buttons
MOVE_DOWN_NAMED = "Move {name} down"
DEVICE_BUTTONS_HINT = "This number means a different button on each device."
NO_KEYS_SEEN = "None seen yet"
KEY_CHIP = "{key} · seen in {plugin} · {count} bind{s}"
KEY_CHIP_MANY = "{key} · seen in {plugins} · {count} bind{s}"
OTHER_LABELS_HEADING = "Other labels (from merged profiles or devices)"
OTHER_LABELS_HELP = "These are names, not keys, so they are never coloured."
OTHER_LABELS_NONE = "None in your profiles."
UNGROUPED_HEADING = "Keys without a group"
UNGROUPED_HELP = "These keys are shown but not coloured yet."
BUTTON_RESTORE_DEFAULTS = "Restore defaults"
RESTORE_DEFAULTS_CONFIRM = (
    "Put the key groups, colours and order back to the defaults? "
    "Your own groups are kept."
)
LOW_CONTRAST = (
    "Hard to read: low contrast ({ratio:.1f}:1); a darker shade is used for text"
)
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

# ── Export page ──
EXPORT_STYLE_LABEL = "Style"
EXPORT_STYLE_EDIT = "Edit…"
EXPORT_CONFIRM_STYLE = "Style: {style}"
WHATS_NEW_TEXT = (
    "New: colour your modifiers and change fonts and borders on every diagram."
)
WHATS_NEW_TRY = "Try styles"
WHATS_NEW_DISMISS = "Not now"
EXPORT_SUMMARY_LIMITED = (
    "Your style couldn't be fully applied to {count} diagram(s): {details}. "
    "They were exported with their original look."
)

# ── Settings → General pointer ──
SETTINGS_MODIFIERS_MOVED = (
    '"Merge modifiers into the main binding text" has moved: choose how modifiers '
    "are shown under Customise → Appearance → Style."
)
SETTINGS_OPEN_APPEARANCE = "Open Appearance"
