""" "Save as new template" (plan §5.7): bake the layout changes into a new SVG
under My templates, optionally store the current style as the template's look,
and optionally assign it to the device right away.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.db.db_device_management import add_update_device_template_path
from joystick_diagrams.render.layout import TEMPLATE_LAYER, LayoutDocument, LayoutLayers
from joystick_diagrams.render.template_writer import (
    BakeResult,
    TemplateBakeError,
    bake_template,
    safe_template_filename,
    write_template,
)
from joystick_diagrams.ui import strings_layout as S
from joystick_diagrams.ui.widgets.confirm import confirm, show_problem
from joystick_diagrams.utils import user_templates_root

_logger = logging.getLogger(__name__)

HEADING_STYLE = (
    "color: #E8EAED; font-size: 13px; font-weight: bold; background: transparent;"
)
HELP_STYLE = "color: #9AA0A6; font-size: 12px; background: transparent;"


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(HEADING_STYLE)
    return label


def _help(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(HELP_STYLE)
    return label


def default_template_name(template_file_name: str) -> str:
    stem = Path(template_file_name).stem
    return S.SAVE_DEFAULT_NAME.format(template=stem)


class SaveTemplateDialog(QDialog):
    def __init__(
        self,
        *,
        template: Any,
        session: Any,
        export_device: Any,
        device_name: str,
        device_id: str,
        theme: Any = None,
        folder: Path | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(S.SAVE_TITLE)
        self.setMinimumWidth(560)
        self._template = template
        self._session = session
        self._export_device = export_device
        self._device_name = device_name
        self._device_id = device_id
        self._theme = theme
        self._folder = folder
        self.saved_path: Path | None = None
        self.bake_result: BakeResult | None = None
        self.assigned = False
        self.result_text = ""
        self._build()

    def _profile_key(self) -> str | None:
        if self._export_device is None:
            return None
        return self._export_device.profile_wrapper.profile_key

    def _profile_name(self) -> str:
        if self._export_device is None:
            return ""
        return self._export_device.profile_wrapper.profile_name

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(_help(S.SAVE_INTRO))

        layout.addWidget(_heading(S.SAVE_NAME))
        self.name_edit = QLineEdit(
            default_template_name(self._template.template_file_name)
        )
        self.name_edit.setAccessibleName(S.SAVE_NAME)
        layout.addWidget(self.name_edit)
        self.problem_label = QLabel()
        self.problem_label.setStyleSheet("color: #F87171;")
        self.problem_label.hide()
        layout.addWidget(self.problem_label)
        layout.addWidget(_help(S.SAVE_LOCATION))

        layout.addWidget(_heading(S.SAVE_INCLUDE))
        all_count = self._session.change_count(TEMPLATE_LAYER)
        profile_key = self._profile_key()
        profile_count = self._session.change_count(profile_key) if profile_key else 0
        self.include_group = QButtonGroup(self)
        self.include_all = QRadioButton(
            S.SAVE_INCLUDE_ALL.format(count=all_count, s=S.plural(all_count))
        )
        self.include_profile = QRadioButton(
            S.SAVE_INCLUDE_PROFILE.format(
                profile=self._profile_name() or "…",
                all=all_count,
                profile_count=profile_count,
                s=S.plural(profile_count),
            )
        )
        self.include_profile.setEnabled(bool(profile_key) and profile_count > 0)
        self.include_all.setChecked(True)
        self.include_group.addButton(self.include_all, 0)
        self.include_group.addButton(self.include_profile, 1)
        layout.addWidget(self.include_all)
        layout.addWidget(self.include_profile)

        layout.addWidget(_heading(S.SAVE_EXTRAS))
        self.store_style = QCheckBox(S.SAVE_STORE_STYLE)
        self.store_style.setChecked(self._theme is not None)
        self.store_style.setEnabled(self._theme is not None)
        layout.addWidget(self.store_style)
        layout.addWidget(
            _help(
                S.SAVE_STORE_STYLE_HINT
                if self._theme is not None
                else S.SAVE_DONE_STYLE_SKIPPED.strip()
            )
        )
        self.use_now = QCheckBox(S.SAVE_USE_NOW.format(controller=self._device_name))
        self.use_now.setChecked(True)
        layout.addWidget(self.use_now)
        layout.addWidget(_help(S.SAVE_INFO))

        buttons = QHBoxLayout()
        self.open_folder_button = QPushButton(S.SAVE_OPEN_FOLDER)
        self.open_folder_button.setProperty("class", "plugin-setup-button")
        self.open_folder_button.clicked.connect(self.open_folder)
        buttons.addWidget(self.open_folder_button)
        buttons.addStretch(1)
        self.cancel_button = QPushButton(S.SAVE_CANCEL)
        self.cancel_button.setProperty("class", "plugin-setup-button")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton(S.SAVE_SAVE)
        self.save_button.setProperty("class", "run-button")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

    # ── Actions ──

    def folder(self) -> Path:
        return self._folder if self._folder is not None else user_templates_root()

    def open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.folder())))

    def layers_to_bake(self) -> LayoutLayers:
        """This controller's layout (``device_guid``-keyed, via the session)."""
        session = self._session
        device_guid = getattr(session, "device_guid", "") or ""
        template_doc = LayoutDocument(
            template_key=session.template_key,
            device_guid=device_guid,
            ops=session.ops_in(TEMPLATE_LAYER),
        )
        profile_key = self._profile_key()
        if self.include_profile.isChecked() and profile_key:
            profile_doc = LayoutDocument(
                template_key=session.template_key,
                device_guid=device_guid,
                profile_key=profile_key,
                ops=session.ops_in(profile_key),
            )
        else:
            profile_doc = LayoutDocument(
                template_key=session.template_key, device_guid=device_guid
            )
        return LayoutLayers(template_doc, profile_doc)

    def save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.problem_label.setText(S.SAVE_NAME_REQUIRED)
            self.problem_label.show()
            self.name_edit.setFocus()
            return
        folder = self.folder()
        target = folder / safe_template_filename(name)
        if target.exists():
            if not confirm(
                self,
                S.SAVE_EXISTS_TITLE.format(name=target.name),
                S.SAVE_EXISTS_TEXT.format(name=target.name),
                S.SAVE_EXISTS_CONFIRM,
                S.SAVE_CANCEL,
            ):
                return
        store_style = self.store_style.isChecked() and self._theme is not None
        try:
            result = bake_template(
                self._template,
                self.layers_to_bake(),
                device=self._export_device.device
                if self._export_device is not None
                else None,
                theme=self._theme,
                store_theme=store_style,
            )
            path = write_template(result.svg_text, folder, name)
        except (TemplateBakeError, OSError) as error:
            _logger.error(f"Saving template failed: {error}", exc_info=True)
            show_problem(self, S.SAVE_FAILED_TITLE, S.SAVE_FAILED_TEXT, str(error))
            return
        self.bake_result = result
        self.saved_path = path
        if self.use_now.isChecked():
            self.assigned = bool(
                add_update_device_template_path(self._device_id, str(path))
            )
        text = S.SAVE_DONE_TEXT.format(path=path)
        skipped = len(result.skipped_ops)
        if skipped:
            text += S.SAVE_DONE_SKIPPED.format(
                count=skipped, s=S.plural(skipped), was=S.plural(skipped, "was", "were")
            )
        if self.assigned:
            text += S.SAVE_DONE_USED.format(controller=self._device_name)
        if self.store_style.isChecked() and not store_style:
            text += S.SAVE_DONE_STYLE_SKIPPED
        # Success is one inline line on the Layout screen, never a dialog
        self.result_text = text
        self.accept()


if __name__ == "__main__":
    pass
