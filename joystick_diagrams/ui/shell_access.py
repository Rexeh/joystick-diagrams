"""Find the four-stage shell from inside a stage page without importing it.

Stage pages (``bindings_page``, ``diagrams_page``) talk to ``MainWindow``
through duck typing: ``show_banner(text, actions, tone)``, ``clear_banner()``,
``set_status_text(text, progress)``, ``go_to_stage(index, payload)``,
``start_read()``, ``read_in_progress`` and the ``read_started`` /
``read_finished`` signals (``ui/stage_contract.py``). ``find_shell`` walks the
parent chain for the first widget that offers ``show_banner`` so a page works
inside the shell, inside a test harness that mimics it, or on its own.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtWidgets import QWidget

_logger = logging.getLogger(__name__)

SHELL_MARKER = "show_banner"


def find_shell(widget: QWidget | None) -> Any | None:
    """The nearest ancestor (or the widget itself) that behaves like the shell."""
    current = widget
    while current is not None:
        if hasattr(current, SHELL_MARKER):
            return current
        current = current.parentWidget()
    try:
        from joystick_diagrams.app_state import AppState

        if AppState._inst is not None:
            main_window = AppState().main_window
            if main_window is not None and hasattr(main_window, SHELL_MARKER):
                return main_window
    except Exception:  # noqa: BLE001 - never let a lookup break a page
        pass
    return None


def show_banner(
    widget: QWidget,
    text: str,
    actions: list[tuple[str, Any]] | None = None,
    tone: str = "info",
) -> bool:
    """Show ``text`` in the shell's banner slot. Returns False when there is no shell."""
    shell = find_shell(widget)
    if shell is None:
        return False
    try:
        shell.show_banner(text, actions or [], tone)
    except TypeError:
        shell.show_banner(text, actions or [])
    except Exception as error:  # noqa: BLE001
        _logger.debug(f"Banner not shown: {error}")
        return False
    return True


def clear_banner(widget: QWidget) -> None:
    shell = find_shell(widget)
    clear = getattr(shell, "clear_banner", None)
    if callable(clear):
        try:
            clear()
        except Exception as error:  # noqa: BLE001
            _logger.debug(f"Banner not cleared: {error}")


def set_status_text(widget: QWidget, text: str, progress: int | None = None) -> None:
    """Status-bar text and progress (0–100, ``None`` hides or resets the bar)."""
    shell = find_shell(widget)
    setter = getattr(shell, "set_status_text", None)
    if callable(setter):
        try:
            setter(text, progress)
        except TypeError:
            setter(text)
        except Exception as error:  # noqa: BLE001
            _logger.debug(f"Status not set: {error}")


def read_in_progress(widget: QWidget) -> bool:
    shell = find_shell(widget)
    return bool(getattr(shell, "read_in_progress", False)) if shell else False


if __name__ == "__main__":
    pass
