"""User-facing text for stage 4, Diagrams (``ui/diagrams_page.py``, the Export
screen, Pages and the Combine dialog). Wording follows
``docs/superpowers/specs/2026-10-25-ux-language.md`` and journey boards
J08, J09, J12, J13 and J14: "diagram" is one file written; "page" is two or more
controllers on one sheet; "other app" is an output plugin.
"""

from __future__ import annotations


def plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


def join_names(names: list[str]) -> str:
    """ "A", "A and B", "A, B or C" style list for sentences ("Button 31, Button 32 or Hat 3 Up")."""
    names = [n for n in names if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " or " + names[-1]


def join_and(names: list[str]) -> str:
    """ "A", "A and B", "A, B and C"."""
    names = [n for n in names if n]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def counted(count: int, words: tuple[str, str]) -> str:
    return f"{count} {plural(count, *words)}"


DIAGRAMS = ("diagram", "diagrams")
PROFILES = ("profile", "profiles")
CONTROLLERS = ("controller", "controllers")
BINDINGS = ("binding", "bindings")

# ── Stage ──
TITLE = "Diagrams"
NAV_EXPORT = "Export"
NAV_MAKE_CHANGES = "Make changes"
NAV_APPEARANCE = "Appearance"
NAV_LAYOUT = "Layout"
NAV_PAGES = "Pages"
STATUS_READY = "{count} {diagrams} ready"
STATUS_CHOOSE_TEMPLATES = "Choose templates first"
STATUS_NOTHING_TO_EXPORT = "Nothing to export yet"
STATUS_EXPORTING = "Exporting {done} of {total}…"
STATUS_EXPORTED_AT = "Exported {count} at {time}"
STATUS_EXPORT_STOPPED = "Export stopped · {reason}"

# ── Export screen ──
EXPORT_INTRO = "Everything ready is ticked."
BINDINGS_READ = "Bindings read {time}"
BINDINGS_READ_NOW = "Bindings read {time} · reading now"
READ_AGAIN = "Read again"
COLUMN_CONTROLLER = "Controller"
COLUMN_PROFILES = "Profiles"
COLUMN_STATUS = "Status"
GAME_FILTER_ALL = "All games"
PROFILE_SEARCH = "Search profiles"
ROW_PROFILES_TICKED = "{ticked} of {count}"
ROW_PROFILES_COUNT = "{count} {profiles}"
ROW_READY = "✔ Ready"
ROW_GAPS = "⚠ {count} {bindings} won't show"
ROW_WHY = "Why?"
ROW_ON_PAGE = "(on {page} page)"
ROW_ON_PAGES = "(on {page} page +{more} more)"
ROW_ON_PAGE_TIP = (
    "Exported on the {page} page. Untick 'Export them only on this page' on the "
    "page to also export it on its own."
)
ROW_TEMPLATE_TIP = "Template: {template}"
NOT_INCLUDED = "Not included: {controller} · no template yet"
NOT_INCLUDED_MISSING = "Not included: {controller} · template {template} can't be found"
NOT_INCLUDED_PAGE = "Not included: {page} · {controller} needs a template"
CHOOSE_TEMPLATE = "Choose template…"
NO_DIAGRAM_LINE = "No diagram: {items}"
NO_DIAGRAM_ITEM = "{controller} ({reason})"
CHANGE = "Change"
COMBINE = "Combine onto one page…"
TICK = "Tick:"
TICK_ALL = "All"
TICK_NONE = "None"
TICK_LAST = "Same as last export"
FORMAT = "Format"
STYLE = "Style"
CHANGE_ELLIPSIS = "Change…"
SAVE_TO = "Save to"
SAVE_TO_UNSET = "Not chosen yet. We'll ask when you export."
SAVE_TO_HINT = "Exporting replaces files with the same name in this folder; other files are left alone."
ALSO_SEND_TO = "Also send to"
ALSO_SEND_NONE = "No other apps"
APP_ON = "{name} · On"
APP_NEEDS_SETUP = "{name} · Needs setting up"
NOTHING_TO_EXPORT = "Nothing to export yet. Choose a template in 2. Controllers."
WAITING_FOR_READ = "Your diagrams appear here when reading finishes."
STATUS_WAITING_FOR_READ = "Waiting for your bindings"
STATUS_QUEUED = "Exports when reading finishes"
GO_TO_CONTROLLERS = "‹ Go to 2. Controllers"

BINDINGS_NOT_READ = "Bindings not read"
OPEN_FOLDER_TIP = "Open the export folder"
DISMISS_TIP = "Dismiss"

# ── Footer (shell) ──
EXPORT_N = "Export {count} {diagrams}"
EXPORT_DISABLED = "Export"
EXPORT_DISABLED_TIP = "Tick at least one profile"
EXPORT_WHEN_READ_FINISHES = "Export when reading finishes"
EXPORT_QUEUED_HINT = "Export starts by itself when reading finishes."
EXPORT_RUNNING = "Exporting…"

# ── Folder dialogs ──
CHOOSE_FOLDER_TITLE = "Choose where to save your diagrams"
FOLDER_GONE_TITLE = "Couldn't find {folder}"
FOLDER_GONE_TEXT = (
    "The folder you last exported to isn't available. If it's on a removable drive, "
    "plug it back in, or choose another folder. No diagrams were saved; nothing in the "
    "app has changed."
)
CHOOSE_FOLDER = "Choose folder…"
EXPORT_HERE = "Export here"
STOP_REASON_FOLDER = "no folder"
STOP_REASON_DISK_FULL = "drive full"
STATUS_SAVED_AT = "{count} {diagrams} saved · {time}"
CANCEL = "Cancel"
CANT_WRITE_TITLE = "Couldn't export to {folder}"
CANT_WRITE_TEXT = (
    "Joystick Diagrams isn't allowed to write there. {saved} Choose another folder, or "
    "change the folder's permissions and try again."
)
DISK_FULL_TITLE = "Couldn't export to {folder}"
DISK_FULL_TEXT = "The drive is full. {saved} Free some space or choose another folder, then try again."
SAVED_SO_FAR_NONE = "No diagrams were saved."
SAVED_SO_FAR = "{count} of {total} {diagrams} were saved before it stopped."
DETAILS = "Details"

# ── Progress and result ──
PROGRESS_MAKING_PNG = "Making PNG files…"
PROGRESS_MAKING_PDF = "Making PDF files…"
PROGRESS_OTHER_APPS = "Sending to other apps…"
RESULT_SAVED = "{count} {diagrams} saved to {folder}"
RESULT_SAVED_PARTIAL = "{count} of {total} {diagrams} saved to {folder}."
RESULT_LOCKED = (
    "{count} couldn't be replaced because they're open in another app or a viewer. "
    "Close them, then try {them} again."
)
RESULT_THOSE = ("it", "those {count}")
TRY_THOSE_AGAIN = ("Try it again", "Try those {count} again")
SHOW_WHICH = "Show which"
SHOW_WHICH_TITLE = "Files that couldn't be replaced"
RESULT_FAILED_SOME = "{count} couldn't be made; details are in Help › Open log folder."
OPEN_FOLDER = "Open folder"
DISMISS = "Dismiss"
CHECK_BEFORE_PRINT = "Check before you print"
NOTICE_GAPS = "{controller}: {count} {bindings} won't show because the template has no box for {controls}."
NOTICE_GAPS_ACTION_LAYOUT = "Add boxes in Layout"
NOTICE_GAPS_ACTION_TEMPLATE = "Try another template"
NOTICE_STYLE_FAILED = (
    "{count} {diagrams} {were} exported without your style: {their} can't take styles."
)
NOTICE_STYLE_LIMITED = (
    "Only the text took your style on {count} {diagrams}; "
    "{their} boxes and lines keep their look."
)
NOTICE_OVERFLOW_LISTED = "{count} {controls} had more modifier bindings than boxes; the extra ones are listed under the main text."
NOTICE_OVERFLOW_HIDDEN = "{count} {controls} had more modifier bindings than boxes; the extra ones aren't shown."
NOTICE_LAYOUT_SKIPPED = (
    "{count} layout {changes} {were} skipped because the template changed."
)
NOTICE_BOXES_UNPLACED = "{count} modifier {boxes} had no room and {were} left out."
CONTROLS = ("control", "controls")
CHANGES = ("change", "changes")
BOXES = ("box", "boxes")

# ── Why? ──
WHY_TITLE = "{controller}"
WHY_CHOOSE_ANOTHER = "Choose another template…"
WHY_CLOSE = "Close"
MENU_PREVIEW = "Preview…"
MENU_EDIT_LAYOUT = "Edit layout ›"
PAGE_ROW_NAME = "▣ {name} · page · {size} · {profiles}"
ROW_DRAWN_EMPTY = "⚠ {controllers} drawn empty"
PAGE_SIZE_ORIENTED = "{size} {orientation}"
ROW_PROFILE_GAPS = "⚠ {count} won't show"

# ── Pages screen ──
PAGES_INTRO = (
    "A page puts two or more controllers on one sheet, such as stick and throttle on "
    "one A4. You get one page for each profile."
)
PAGES_NEW = "New page…"
PAGES_RENAME = "Rename"
PAGES_DUPLICATE = "Duplicate"
PAGES_DELETE = "Delete"
PAGES_EDIT_LAYOUT = "Edit in Layout ›"
PAGES_EMPTY = "No pages yet. A page puts two or more controllers on one sheet."
PAGES_DELETE_TITLE = "Delete {page}?"
PAGES_DELETE_TEXT = "Its controllers go back to their own diagrams. Your templates and layouts are kept."
PAGES_DELETE_BUTTON = "Delete page"
PAGES_RENAME_TITLE = "Rename page"
PAGES_RENAME_LABEL = "Name"
PAGES_SUMMARY = "{arrangement} · {size} · {profiles} {profiles_word}"
PAGES_EDIT = "Edit…"
PAGE_ONE_FILE_PER_PROFILE = (
    "One file per profile. PDF, PNG and SVG all work; PNG draws the page at the "
    "quality you've chosen."
)
PAGE_PREVIEW_UPDATING = "Updating preview…"
PAGE_PREVIEW_UNAVAILABLE = "A preview appears once two controllers are ticked."

# ── Combine dialog (J12) ──
COMBINE_TITLE = "Combine controllers onto one page"
COMBINE_EDIT_TITLE = "Page"
COMBINE_NAME = "Name"
COMBINE_DEFAULT_NAME = "Page {number}"
COMBINE_CONTROLLERS = "Controllers"
COMBINE_NEEDS_TEMPLATE = "{controller} (needs a template)"
COMBINE_ARRANGEMENT = "Arrangement"
ARRANGE_SIDE_BY_SIDE = "Side by side — left to right in one row"
ARRANGE_STACKED = "Stacked — one above the other"
ARRANGE_GRID = "Grid — rows and columns, for three or more"
COMBINE_PAGE_SIZE = "Page size"
SIZE_CUSTOM = "Custom…"
SIZE_CUSTOM_WIDTH = "Width (mm)"
SIZE_CUSTOM_HEIGHT = "Height (mm)"
COMBINE_SCALING = (
    "Each controller keeps its proportions and is scaled to fit the page; Fit to "
    "content keeps them at full size and makes the sheet bigger."
)
COMBINE_SCALE = "Scale"
COMBINE_SCALE_VALUE = "{percent}%"
COMBINE_MAKE_FOR = "Make this page for"
RULE_SHARED = "Profiles that use {controllers} · {profiles}"
RULE_BOTH_CONTROLLERS = "both controllers"
RULE_ALL_CONTROLLERS = "all {count} controllers"
RULE_ANY = "Any profile that uses one of them · {profiles}"
RULE_ANY_HELP = "Controllers a profile doesn't use are drawn empty."
RULE_SHOW_LIST = "Show which profiles"
RULE_HIDE_LIST = "Hide the profiles"
RULE_LIST_ENTRY = "{game} / {profile}"
RULE_LIST_MISSING = "{entry} — no {controllers} bindings"
RULE_NONE_SHARED = (
    'These controllers don\'t share any profile. Choose "Any profile…" or '
    "different controllers."
)
RULE_NONE_ANY = "None of these controllers has bindings in any profile."
COMBINE_ONLY_ON_PAGE = "Export them only on this page, not as separate diagrams"
COMBINE_ONLY_ON_PAGE_HELP = (
    "Its controllers' own diagrams are skipped for the profiles this page covers."
)
COMBINE_CREATE = "Create page"
COMBINE_SAVE = "Save"
COMBINE_CANCEL = "Cancel"
PAGE_CREATED_BANNER = "Page created and ticked for export."
PAGE_CREATED_ACTION = "Fine-tune in Layout"
COMBINE_ORIENTATION = "Orientation"
ORIENTATION_CHOICES = ("Auto", "Portrait", "Landscape")
COMBINE_PREVIEW_WITH = "Preview with {profile}"
COMBINE_PREVIEW_NONE = "A preview appears once two controllers are ticked."
COMBINE_PREVIEW_FAILED = "The preview couldn't be made. Details are in the log."
SIZE_KNEEBOARD = "Kneeboard 5.5×8.5in"
ORIENTATION_LANDSCAPE = "landscape"
ORIENTATION_PORTRAIT = "portrait"

# ── Layout picker (stage 4 › Layout) ──
LAYOUT_PICKER_NEEDS_TEMPLATE = "{controller} · needs a template"
LAYOUT_PICKER_PAGE = "▣ {page}"
LAYOUT_NEEDS_TEMPLATE_EMPTY = (
    "{controller} needs a template before its layout can be changed."
)
LAYOUT_NONE_READY = "None of your controllers has a template yet."
GO_TO_CONTROLLERS_NEXT = "Go to 2. Controllers ›"
LAYOUT_PAGE_PREVIEW_HELP = (
    "Change this page on the right; every change is saved as you go. Boxes inside "
    "a controller are changed on that controller's own diagram."
)

if __name__ == "__main__":
    pass
