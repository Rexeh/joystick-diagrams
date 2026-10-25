"""The two dialogs the app is allowed to show (language guide §3).

- ``confirm``: only for an action that loses the player's work. The title asks
  the question naming the object ("Reset this layout?"), the text says the
  consequence and what is kept, and the buttons are the verb and Cancel
  (never Yes/No/OK).
- ``show_problem``: one plain sentence saying what failed and what is kept;
  system text (exception strings, paths of code) goes behind Details.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

CANCEL = "Cancel"
DETAILS_ONLY = "Details"


def confirm(
    parent: QWidget | None,
    title: str,
    text: str,
    confirm_label: str,
    cancel_label: str = CANCEL,
    destructive: bool = True,
) -> bool:
    """True when the player pressed ``confirm_label``."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(title)
    box.setInformativeText(text)
    role = (
        QMessageBox.ButtonRole.DestructiveRole
        if destructive
        else QMessageBox.ButtonRole.AcceptRole
    )
    yes = box.addButton(confirm_label, role)
    cancel = box.addButton(cancel_label, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    return box.clickedButton() is yes


def show_problem(
    parent: QWidget | None, title: str, text: str, detail: str | None = None
) -> None:
    """A warning with one plain sentence; ``detail`` sits behind Details."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    if detail:
        box.setDetailedText(detail)
    box.exec()


def show_list(parent: QWidget | None, title: str, text: str) -> None:
    """A plain read-only list (such as "Show which"), with one Close button."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.NoIcon)
    box.setWindowTitle(title)
    box.setText(text)
    box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
    box.exec()
