# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'export.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QMetaObject,
    QRect,
    QSize,
)
from PySide6.QtGui import (
    QFont,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(1100, 700)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(1100, 700))
        Form.setMaximumSize(QSize(1100, 700))
        font = QFont()
        font.setFamilies(["MS Sans Serif"])
        Form.setFont(font)
        self.layoutWidget = QWidget(Form)
        self.layoutWidget.setObjectName("layoutWidget")
        self.layoutWidget.setGeometry(QRect(0, 0, 1081, 691))
        self.layoutWidget.setMaximumSize(QSize(1100, 16777215))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 10, 0, 0)
        self.heading_label = QLabel(self.layoutWidget)
        self.heading_label.setObjectName("heading_label")
        self.heading_label.setMaximumSize(QSize(1100, 23))

        self.verticalLayout.addWidget(self.heading_label)

        self.line = QFrame(self.layoutWidget)
        self.line.setObjectName("line")
        self.line.setMaximumSize(QSize(1100, 16777215))
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.devices_layout = QVBoxLayout()
        self.devices_layout.setObjectName("devices_layout")
        self.devices_layout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.devices_header = QHBoxLayout()
        self.devices_header.setObjectName("devices_header")
        self.devices_header.setSizeConstraint(QLayout.SetMinimumSize)
        self.device_text_layout = QVBoxLayout()
        self.device_text_layout.setObjectName("device_text_layout")
        self.device_text_layout.setContentsMargins(5, -1, -1, -1)
        self.device_header_label = QLabel(self.layoutWidget)
        self.device_header_label.setObjectName("device_header_label")
        self.device_header_label.setMaximumSize(QSize(1100, 16777215))
        font1 = QFont()
        font1.setPointSize(10)
        font1.setBold(True)
        self.device_header_label.setFont(font1)

        self.device_text_layout.addWidget(self.device_header_label)

        self.device_help_label = QLabel(self.layoutWidget)
        self.device_help_label.setObjectName("device_help_label")
        self.device_help_label.setMaximumSize(QSize(1100, 16777215))

        self.device_text_layout.addWidget(self.device_help_label)

        self.devices_header.addLayout(self.device_text_layout)

        self.device_controls_layout = QVBoxLayout()
        self.device_controls_layout.setObjectName("device_controls_layout")
        self.setTemplateButton = QPushButton(self.layoutWidget)
        self.setTemplateButton.setObjectName("setTemplateButton")
        self.setTemplateButton.setMaximumSize(QSize(1100, 16777215))

        self.device_controls_layout.addWidget(self.setTemplateButton)

        self.devices_header.addLayout(self.device_controls_layout)

        self.devices_layout.addLayout(self.devices_header)

        self.devices_container = QHBoxLayout()
        self.devices_container.setObjectName("devices_container")
        self.devices_container.setSizeConstraint(QLayout.SetDefaultConstraint)

        self.devices_layout.addLayout(self.devices_container)

        self.verticalLayout.addLayout(self.devices_layout)

        self.export_bottom_section = QHBoxLayout()
        self.export_bottom_section.setObjectName("export_bottom_section")
        self.export_bottom_section.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.export_bottom_section.setContentsMargins(-1, 0, -1, -1)
        self.export_settings_container = QHBoxLayout()
        self.export_settings_container.setObjectName("export_settings_container")
        self.export_settings_container.setContentsMargins(-1, -1, 50, -1)

        self.export_bottom_section.addLayout(self.export_settings_container)

        self.ExportButton = QPushButton(self.layoutWidget)
        self.ExportButton.setObjectName("ExportButton")
        sizePolicy1 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.ExportButton.sizePolicy().hasHeightForWidth()
        )
        self.ExportButton.setSizePolicy(sizePolicy1)
        self.ExportButton.setMinimumSize(QSize(300, 100))
        self.ExportButton.setMaximumSize(QSize(300, 100))

        self.export_bottom_section.addWidget(self.ExportButton)

        self.verticalLayout.addLayout(self.export_bottom_section)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.heading_label.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p><span style=" font-size:14pt; font-weight:600;">Export</span></p></body></html>',
                None,
            )
        )
        self.device_header_label.setText(
            QCoreApplication.translate("Form", "Device Templates", None)
        )
        self.device_help_label.setText(
            QCoreApplication.translate(
                "Form", "Only devices with templates will be exported", None
            )
        )
        self.setTemplateButton.setText(
            QCoreApplication.translate("Form", "PushButton", None)
        )
        self.ExportButton.setText(QCoreApplication.translate("Form", "Export", None))

    # retranslateUi
