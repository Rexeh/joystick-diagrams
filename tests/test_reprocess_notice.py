"""Tests for AppState.reprocess_profiles_with_notice.

The helper is the canonical entry point for UI handlers that mutate a
*process-time* setting (alias/inheritance merge strategy, etc.) and need
the profile pipeline rebuilt. It must:
    1. Invoke process_profiles_from_collections unconditionally (safe no-op
       when no plugins are enabled).
    2. Flash the message onto main_window.statusLabel (we don't use
       statusBar().showMessage because the main window adds permanent
       widgets that crowd out the temporary-message area).
    3. Invalidate cached data pages so Customise/Export rebuild fresh
       on the next visit.
    4. Tolerate a missing/torn-down main_window without crashing.
"""

from unittest.mock import MagicMock, patch

from joystick_diagrams.app_state import AppState


def _bare_app_state() -> AppState:
    """Construct an AppState instance without triggering the singleton's
    plugin-manager-dependent _init. Tests can then inject attributes
    directly."""
    return object.__new__(AppState)


def test_reprocess_calls_process_profiles_and_flashes_status_label():
    state = _bare_app_state()
    state.main_window = MagicMock()
    state.main_window.statusLabel.text.return_value = "Waiting..."

    with (
        patch.object(
            AppState, "process_profiles_from_collections", autospec=True
        ) as mock_proc,
        patch("joystick_diagrams.app_state.QTimer") as mock_timer,
    ):
        state.reprocess_profiles_with_notice("custom message")

    mock_proc.assert_called_once_with(state)
    state.main_window.statusLabel.setText.assert_called_once_with("custom message")
    # QTimer.singleShot was scheduled to restore after 3000ms.
    mock_timer.singleShot.assert_called_once()
    args, _ = mock_timer.singleShot.call_args
    assert args[0] == 3000


def test_reprocess_invalidates_data_pages():
    state = _bare_app_state()
    state.main_window = MagicMock()
    state.main_window.statusLabel.text.return_value = "Waiting..."

    with (
        patch.object(AppState, "process_profiles_from_collections", autospec=True),
        patch("joystick_diagrams.app_state.QTimer"),
    ):
        state.reprocess_profiles_with_notice("msg")

    state.main_window._invalidate_data_pages.assert_called_once_with()


def test_reprocess_with_default_message():
    state = _bare_app_state()
    state.main_window = MagicMock()
    state.main_window.statusLabel.text.return_value = ""

    with (
        patch.object(AppState, "process_profiles_from_collections", autospec=True),
        patch("joystick_diagrams.app_state.QTimer"),
    ):
        state.reprocess_profiles_with_notice()

    args, _ = state.main_window.statusLabel.setText.call_args
    assert "reprocessed" in args[0].lower()


def test_reprocess_without_main_window_is_silent():
    """During app startup/shutdown main_window may be None — no crash."""
    state = _bare_app_state()
    state.main_window = None

    with patch.object(
        AppState, "process_profiles_from_collections", autospec=True
    ) as mock_proc:
        state.reprocess_profiles_with_notice("msg")

    mock_proc.assert_called_once_with(state)


def test_reprocess_swallows_status_label_errors():
    """If statusLabel raises (window torn down), pipeline has already done
    its work and the caller shouldn't crash."""
    state = _bare_app_state()
    state.main_window = MagicMock()
    state.main_window.statusLabel.text.side_effect = RuntimeError("label deleted")

    with patch.object(AppState, "process_profiles_from_collections", autospec=True):
        state.reprocess_profiles_with_notice("msg")


def test_reprocess_swallows_invalidate_errors():
    """If _invalidate_data_pages raises, the earlier pipeline work is
    preserved and the user still got their toast."""
    state = _bare_app_state()
    state.main_window = MagicMock()
    state.main_window.statusLabel.text.return_value = ""
    state.main_window._invalidate_data_pages.side_effect = RuntimeError("stale")

    with (
        patch.object(AppState, "process_profiles_from_collections", autospec=True),
        patch("joystick_diagrams.app_state.QTimer"),
    ):
        state.reprocess_profiles_with_notice("msg")  # must not raise
