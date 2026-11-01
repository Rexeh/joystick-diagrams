"""The contract between the four-stage shell (``ui/main_window.py``) and its
stage pages (``ui/setup_page.py``, ``ui/controllers_page.py`` from F2;
``ui/bindings_page.py``, ``ui/diagrams_page.py`` from F3).

A stage page is a ``QWidget`` that exposes:

- ``refresh()``: re-read the app state and redraw in place. Called after every
  game read, after a template is chosen on another stage, and when the stage
  is shown. Pages are never destroyed on a re-read, so keep widgets and
  update them.
- ``stage_status() -> StageStatus``: the one-line status drawn on the stage
  tab ("Up to date · read 09:41", "4 need a template"). The icon *shape*
  carries the state; the shell draws it.
- ``next_action() -> NextAction | None``: the single primary action in the
  pinned footer ("Next: Choose 4 templates ›"). ``None`` hides the button.
- ``request_stage`` (``Signal(int, dict)``): a deep link to another stage with a
  payload, e.g. ``{"device_guid": "…"}`` or ``{"section": "layout"}``. The
  shell switches stage, calls ``refresh()`` and then ``handle_request(payload)``
  on the target page (``navigate(payload)`` is accepted as an older name).

Optional hooks the shell calls when present (``getattr``):

- ``handle_request(payload: dict)`` (or ``navigate``): act on a deep-link
  payload (select a controller, open a section). Extra keys a page may get:
  ``"action": "choose_template"`` (stage 2 opens the picker for
  ``device_guid``), ``"game"`` + ``"action": "choose_folder"`` (stage 1).
- ``secondary_action() -> NextAction | None``: a quieter action at the left of
  the footer.
- ``footer_hint() -> str | None``: the grey sentence at the left of the footer.
- ``on_read_started(games: list[str])`` / ``on_read_finished(outcome: ReadOutcome)``:
  the background game read lifecycle (also available as the shell's
  ``read_started``/``read_finished`` signals and ``read_in_progress`` attribute,
  which stage 4 uses to queue an export).
- ``shutdown()``: tear down WebEngine views before the window closes.

The shell itself offers ``show_banner(text, actions, tone)`` / ``clear_banner()``
for the reserved notice slot under the strip, ``set_status_text(text, progress)``
for the status bar, ``go_to_stage(index, payload=None)`` and ``start_read()``.

Payload keys: ``PAYLOAD_DEVICE_GUID`` ("device_guid"), ``PAYLOAD_SECTION``
("section", one of ``SECTION_LAYOUT``, ``SECTION_EXPORT``, ``SECTION_APPEARANCE``,
``SECTION_PAGES``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

StatusIcon = Literal["ok", "warning", "error", "busy", "none"]

STAGE_SETUP = 0
STAGE_CONTROLLERS = 1
STAGE_BINDINGS = 2
STAGE_DIAGRAMS = 3
STAGE_COUNT = 4

STAGE_TITLES: tuple[str, ...] = (
    "1. Setup",
    "2. Controllers",
    "3. Bindings",
    "4. Diagrams",
)

PAYLOAD_DEVICE_GUID = "device_guid"
PAYLOAD_SECTION = "section"
SECTION_LAYOUT = "layout"
SECTION_EXPORT = "export"
SECTION_APPEARANCE = "appearance"
SECTION_PAGES = "pages"


@dataclass(frozen=True)
class StageStatus:
    """One line on a stage tab. ``done`` overrides the "completed" chevron
    (``None``: completed when ``icon == "ok"``)."""

    icon: StatusIcon = "none"
    text: str = ""
    done: bool | None = None

    @property
    def is_done(self) -> bool:
        return self.icon == "ok" if self.done is None else self.done


@dataclass(frozen=True)
class NextAction:
    """The footer button: ``label`` is shown as given ("Next: 2. Controllers ›")."""

    label: str
    callback: Callable[[], None]
    enabled: bool = True
    tooltip: str | None = None


@dataclass
class ReadOutcome:
    """What a background game read produced (``MainWindow.read_finished``).

    ``inventory`` is the ``DeviceInventoryService.ReadResult`` from
    ``AppState.record_device_read()`` (``None`` when no game could be read).
    ``failed`` lists the games whose read failed, with the plain error text.
    """

    games: list[str] = field(default_factory=list)
    profile_count: int = 0
    failed: dict[str, str] = field(default_factory=dict)
    inventory: Any = None
    finished_at: str = ""  # "09:41", for status lines
    profiles_per_game: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.failed

    @property
    def new_guids(self) -> list[str]:
        return list(getattr(self.inventory, "new", []) or [])

    @property
    def is_first_read(self) -> bool:
        """Every controller in this read is new: nothing was known before."""
        seen = set(getattr(self.inventory, "seen", []) or [])
        return bool(seen) and seen <= set(self.new_guids)

    @property
    def arrived_guids(self) -> list[str]:
        """Controllers that are new since an earlier read (none on the first read)."""
        return [] if self.is_first_read else self.new_guids


if __name__ == "__main__":
    pass
