"""User-facing text for 4. Diagrams › Layout, the Auto-add and Save-as-template
dialogs and the Preview window (plan §5.5.9: one module,
plain language, no jargon such as "op", "layer", "slot" or "uid").
"""

from __future__ import annotations

# ── Navigation and header ──
NAV_LAYOUT = "Layout"
HEADER_DIAGRAM = "Diagram"
HEADER_PREVIEW_WITH = "Preview with:"
HEADER_SCOPE = "Changes apply to:"
SCOPE_ALL_PROFILES = "All profiles on this diagram"
SCOPE_ONLY_PROFILE = "Only {profile}"
SAVED_AUTOMATICALLY = "Saved automatically"
PREVIEW_ENTRY = "{game} / {profile}"
DIAGRAM_ENTRY = "{controller} · {template}"
PAGE_HELP = (
    "Move, resize or hide boxes, add modifier boxes and notes. "
    "Changes apply to every export of this controller's diagram."
)

# ── Empty and limited states ──
EMPTY_MESSAGE = "None of your controllers has a template yet."
EMPTY_ACTION = "Choose a template"
UNSUPPORTED_BANNER = (
    "Moving boxes isn't available for this template; text styling still works."
)
RENDERING = "Updating…"
RENDER_FAILED = "The diagram couldn't be drawn. Details are in Help › Open log folder."
WEBENGINE_UNAVAILABLE = (
    "The layout editor couldn't start on this computer. Details are in the log."
)

# ── Toolbar ──
TOOL_SELECT = "Select"
TOOL_ADD_MODIFIER_BOX = "+ Modifier box"
TOOL_AUTO_ADD = "Add modifier boxes…"
TOOL_ADD_NOTE = "+ Note"
TOOL_HIDE = "Hide"
TOOL_SHOW = "Show"
TOOL_REMOVE = "Remove"
TOOL_UNDO = "Undo"
TOOL_REDO = "Redo"
TOOL_ZOOM_IN = "Zoom in"
TOOL_ZOOM_OUT = "Zoom out"
TOOL_ZOOM_FIT = "Fit"
TOOL_MORE = "More"
MORE_UNDO_PROFILE = "Undo changes for {profile} only"
MORE_RESET_ALL = "Reset layout…"
MORE_SAVE_AS_TEMPLATE = "Save as new template…"
TOOLTIP_SELECT = "Select and move boxes"
TOOLTIP_ADD_MODIFIER_BOX = "Add a modifier box next to the selected control"
TOOLTIP_AUTO_ADD = "Add modifier boxes for every control that needs them"
TOOLTIP_HIDE = "Hide the selected box (Delete)"
TOOLTIP_UNDO = "Undo (Ctrl+Z)"
TOOLTIP_REDO = "Redo (Ctrl+Y)"
TOOLTIP_ZOOM_FIT = "Fit the whole diagram in the window"
TOOLTIP_ZOOM_100 = "Zoom to 100%"
SELECT_A_CONTROL_FIRST = "Click a control on the diagram first."
NOTES_NEED_NO_PARENT = "Notes aren't controls, so they can't have modifier boxes."
NO_ROOM_FOR_BOX = "There's no room for another box next to {name}."

# ── Reset confirmations ──
RESET_ALL_TITLE = "Reset this layout?"
RESET_ALL_CONFIRM = "Reset layout"
CANCEL = "Cancel"
UNDO_PROFILE_CONFIRM = "Undo changes"
RESET_ALL_TEXT = (
    "This removes every layout change on this diagram, for all profiles. "
    "You can undo it while you stay on this screen."
)
UNDO_PROFILE_TITLE = "Undo your changes for {profile}?"
UNDO_PROFILE_TEXT = (
    "Changes made only for {profile} are removed; changes for all profiles stay."
)
NOTHING_TO_RESET = "There are no layout changes on this diagram."
NOTHING_FOR_PROFILE = "There are no changes made only for {profile}."

# ── Note dialog ──
NOTE_DIALOG_TITLE = "Note text"
NOTE_DIALOG_HELP = (
    "Insert the profile name or today's date; they update on every export."
)
NOTE_INSERT_PROFILE = "Insert profile name"
NOTE_INSERT_DATE = "Insert date"
NOTE_DEFAULT_TEXT = "Note"
NOTE_PROFILE_TOKEN = "PROFILE_NAME"
NOTE_DATE_TOKEN = "CURRENT_DATE"

# ── Right panel ──
PANEL_NOTHING_SELECTED = (
    "Click a box on the diagram to select it. Drag to move, drag a corner to "
    "resize. Arrow keys nudge by 1 px (Shift: 10 px)."
)
PANEL_FROM_TEMPLATE = "from the template"
PANEL_ADDED_BY_YOU = "added by you"
PANEL_NOTE = "note"
PANEL_ORIGIN = "{name} · {origin}"
PANEL_X = "X"
PANEL_Y = "Y"
PANEL_W = "W"
PANEL_H = "H"
# Accessible names: screen readers say the word, not the letter
PANEL_X_NAME = "Left"
PANEL_Y_NAME = "Top"
PANEL_W_NAME = "Width"
PANEL_H_NAME = "Height"
PANEL_NOT_RESIZABLE = "This box can't be resized (it isn't a plain rectangle)."
PANEL_NOT_MOVABLE = "This box can't be moved on this template."
PANEL_MODIFIER_BOXES = "Modifier boxes: {count} · filled in key order"
PANEL_ADD_BOX = "+ Add box"
PANEL_HIDE_BOX = "Hide this box"
PANEL_SHOW_BOX = "Show this box"
PANEL_REMOVE_BOX = "Remove this box"
PANEL_REMOVE_NOTE = "Remove this note"
PANEL_EDIT_NOTE = "Edit note…"
PANEL_UNDO_BOX = "Undo changes to this box"
PANEL_PROFILE_ONLY = "Changed only for {profile}"
PANEL_NOTICES = "Notices"
PANEL_NO_NOTICES = "Nothing to report."
PANEL_UNDO_NOTE = (
    "Undo history clears when you leave this screen. Your changes are already saved."
)

# ── Page panel (a page chosen in the Diagram picker) ──
PAGE_PANEL_HEADING = "Page"
PAGE_NAME = "Name"
PAGE_CONTROLLERS = "Controllers on this page"
PAGE_CONTROLLERS_HELP = "Click a controller to see what you can change for it."
PAGE_CHANGE_CONTROLLERS = "Change controllers…"
PAGE_CONTROLLER_PLACED = "Its place on the page comes from the arrangement."
PAGE_EDIT_CONTROLLER_BOXES = "Edit this controller's boxes ›"
PAGE_EDIT_CONTROLLER_BOXES_TIP = "Opens this controller's own diagram in Layout"
PAGE_ARRANGEMENT = "Arrangement"
PAGE_SIZE = "Page size"
PAGE_ORIENTATION = "Orientation"
PAGE_SCALE = "Scale"
PAGE_SCALE_VALUE = "{percent}%"
PAGE_SCALE_TIP = "100% fills the page; smaller leaves more space around the controllers"
PAGE_GAP = "Gap (mm)"
PAGE_GAP_TIP = "Space between the controllers on this page"
PAGE_TITLE_AND_DATE = "Title and date"
PAGE_SHOW_TITLE = "Show title"
PAGE_SHOW_DATE = "Show date"
PAGE_TITLE = "Title"
PAGE_TITLE_PLACEHOLDER = "Leave empty for “{example}”"
PAGE_TITLE_EXAMPLE_PROFILE = "Profile"
PAGE_RESET = "Reset to defaults"
PAGE_RESET_TIP = (
    "Page size, arrangement, scale, gap, title and date go back to their defaults"
)
PAGE_TOOL_UNAVAILABLE = "Not available for pages"
PAGE_FIX_SCALE = "Move Scale up to make the text larger."
PAGE_FIX_AT_FULL_SCALE = (
    "Scale is already 100%. A bigger page size, or Stacked or Grid, makes the "
    "text larger."
)

# ── Notices (plain language) ──
NOTICE_OVERFLOW = "{name} has {count} more modifier binding{s} than boxes. {tail}"
NOTICE_OVERFLOW_LISTED = "{they}'re still listed under the main text."
NOTICE_OVERFLOW_HIDDEN = "{they} {dont} appear on this diagram."
NOTICE_OVERFLOW_ACTION = "Add boxes"
NOTICE_TEMPLATE_UPDATED = (
    "This template was updated on {date}. {count} of your changes no longer "
    "fit and {was} skipped."
)
NOTICE_TEMPLATE_UPDATED_ACTION = "Show which"
NOTICE_SKIPPED_DETAIL = "Skipped: {items}"
NOTICE_NO_ROOM = "No room for {count} box{es} next to {name}."
NOTICE_UNSUPPORTED = UNSUPPORTED_BANNER
NOTICE_CANT_RESIZE = (
    "{name} can't be resized on this template, so that change was skipped."
)
NOTICE_MISSING_SLOT = (
    "{name} isn't on this template any more, so its changes were skipped."
)

# ── Auto-add dialog ──
AUTO_TITLE = "Add modifier boxes"
AUTO_WHICH = "Which controls?"
AUTO_WHICH_THIS_PROFILE = "Controls with modifiers in {profile}"
AUTO_WHICH_ANY_PROFILE = (
    "Controls with modifiers in any profile using this diagram ({count})"
)
AUTO_HOW_MANY = "How many boxes?"
AUTO_HOW_MANY_HINT = "One per modifier, up to"
AUTO_WHERE = "Where?"
AUTO_WHERE_AUTO = "Wherever there's room"
AUTO_WHERE_BELOW = "Below"
AUTO_WHERE_RIGHT = "To the right"
AUTO_WHERE_LEFT = "To the left"
AUTO_WHERE_ABOVE = "Above"
AUTO_NO_ROOM = "If there isn't enough room:"
AUTO_NO_ROOM_LIST = "List the extra modifiers under the main text"
AUTO_NO_ROOM_NOTICE = "Leave them off and show a notice"
AUTO_SUMMARY_HEADING = "What will happen"
AUTO_SUMMARY_ADDED = "{boxes} box{es} added to {controls} control{s}"
AUTO_SUMMARY_NOTHING = "Nothing to add: every control with modifiers already has boxes."
AUTO_SUMMARY_NONE_FIT = (
    "No box could be placed: there is no room next to these controls."
)
AUTO_SUMMARY_NO_CONTROLS = "No controls with modifiers in {profile}."
AUTO_SUMMARY_NO_ROOM = "{controls} control{s} {dont} have room for {boxes} box{es}."
AUTO_SUMMARY_NO_ROOM_LISTED = (
    "Their extra modifiers will be listed under the main text."
)
AUTO_SUMMARY_NO_ROOM_NOTICE = "Those modifiers will be left off and a notice shown."
AUTO_SUMMARY_DISPLAY_CHANGE = (
    'Turns on "Add them under the main text" in 4. Diagrams › Appearance.'
)
AUTO_SUMMARY_APPLIES = "Applies to: {scope} · Undo removes them in one step"
AUTO_CANCEL = "Cancel"
AUTO_ADD_N = "Add {count} box{es}"
AUTO_ADD_NONE = "Add boxes"

# ── Save as new template ──
SAVE_TITLE = "Save as new template"
SAVE_INTRO = "Makes a copy you can reuse or share. Your current template isn't changed."
SAVE_NAME = "Name"
SAVE_DEFAULT_NAME = "{template} – with modifier boxes"
SAVE_LOCATION = "Saved to My templates. It appears at the top of every template picker."
SAVE_INCLUDE = "Include changes for"
SAVE_INCLUDE_ALL = "All profiles on this diagram ({count} change{s})"
SAVE_INCLUDE_PROFILE = "All profiles + {profile} ({all} + {profile_count} change{s})"
SAVE_EXTRAS = "Extras"
SAVE_STORE_STYLE = "Save the current style with this template"
SAVE_STORE_STYLE_HINT = (
    "Remembered inside the file so this app can offer it as the template's default."
)
SAVE_USE_NOW = "Use it for {controller} now"
SAVE_INFO = (
    "You can keep editing it in draw.io or share it. It works in older versions "
    "of Joystick Diagrams too."
)
SAVE_OPEN_FOLDER = "Open My templates folder"
SAVE_CANCEL = "Cancel"
SAVE_SAVE = "Save template"
SAVE_NAME_REQUIRED = "Give the template a name."
SAVE_EXISTS_TITLE = "Replace {name}?"
SAVE_EXISTS_CONFIRM = "Replace template"
SAVE_EXISTS_TEXT = (
    "A template named {name} is already in My templates. Saving replaces it."
)
SAVE_FAILED_TITLE = "Couldn't save the template"
SAVE_FAILED_TEXT = (
    "The template couldn't be saved to My templates. Your layout changes are kept."
)
DETAILS = "Details"
SAVE_DONE_TEXT = "✔ Saved to {path}."
SAVE_DONE_SKIPPED = " {count} change{s} no longer fit the template and {was} left out."
SAVE_DONE_USED = " {controller} now uses it."
SAVE_DONE_STYLE_SKIPPED = (
    " The style wasn't stored because Original (unchanged) has nothing to store."
)

# ── Preview window ──
PREVIEW_TITLE = "Preview — {controller}"
PREVIEW_PROFILE = "Profile:"
PREVIEW_HELP = "Exactly what Export will produce with your current style and layout."
PREVIEW_RENDERING = "Updating preview…"
PREVIEW_EDIT_LAYOUT = "Edit layout ›"
PREVIEW_CLOSE = "Close"

# ── Controller menus ──
MENU_PREVIEW = "Preview…"
MENU_EDIT_LAYOUT = "Edit layout ›"

# ── Preview notices (the per-diagram reasons) ──
REASON_OVERFLOW = "{count} control{s} with more modifier bindings than boxes"
REASON_SKIPPED = "{count} layout change{s} skipped"
REASON_UNPLACED = "{count} modifier box{es} without room"


def plural(count: int, one: str = "", many: str = "s") -> str:
    return one if count == 1 else many


def pretty_key(key: str) -> str:
    """``button_1#1`` → ``Button 1``; ``pov_1_u`` → ``POV 1 U``; ``axis_x`` → ``Axis X``."""
    base = key.split("#", 1)[0]
    parts = base.split("_")
    if not parts:
        return key
    words = []
    for index, part in enumerate(parts):
        if index == 0:
            words.append(part.upper() if part.lower() == "pov" else part.capitalize())
        elif part.lower() in ("modifier", "modifiers"):
            words.append(part.lower())
        else:
            words.append(part.upper() if len(part) <= 2 else part.capitalize())
    return " ".join(words)


if __name__ == "__main__":
    pass
