"""``pick_template``: the one file dialog every "choose a template" action uses.

A ``QFileDialog`` instance (not the static ``getOpenFileName``) so the sidebar
can list the bundled ``templates`` folder and the user's **My templates**
folder (``utils.user_templates_root()``, where "Save as new template…" writes).
The dialog starts in My templates when it holds any SVG, otherwise in the
bundled folder (plan §5.7).
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QFileDialog, QWidget

from joystick_diagrams.utils import install_root, user_templates_root

SVG_FILTER = "SVG Files (*.svg)"


def bundled_templates_dir() -> Path:
    return Path(os.path.join(install_root(), "templates"))


def user_templates_has_files() -> bool:
    try:
        return any(user_templates_root().glob("*.svg"))
    except OSError:
        return False


def default_template_dir() -> Path:
    """My templates when it has files, else the bundled folder."""
    if user_templates_has_files():
        return user_templates_root()
    return bundled_templates_dir()


def template_sidebar_urls() -> list[QUrl]:
    urls = [QUrl.fromLocalFile(str(bundled_templates_dir()))]
    try:
        urls.append(QUrl.fromLocalFile(str(user_templates_root())))
    except OSError:
        pass
    return urls


def pick_template(parent: QWidget | None, title: str) -> Path | None:
    """Open the template picker; ``None`` when the user cancels."""
    dialog = QFileDialog(parent, title, str(default_template_dir()), SVG_FILTER)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dialog.setSidebarUrls(template_sidebar_urls())
    if dialog.exec() != QFileDialog.DialogCode.Accepted:
        return None
    files = dialog.selectedFiles()
    return Path(files[0]) if files else None


if __name__ == "__main__":
    pass
