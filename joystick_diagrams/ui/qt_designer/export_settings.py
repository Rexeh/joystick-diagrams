# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'export_settings.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
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
        Form.resize(550, 150)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(550, 150))
        Form.setMaximumSize(QSize(550, 150))
        Form.setBaseSize(QSize(500, 150))
        self.verticalLayoutWidget = QWidget(Form)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(9, 9, 531, 131))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetMaximumSize)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.verticalLayoutWidget)
        self.label.setObjectName("label")
        self.label.setMaximumSize(QSize(1100, 23))

        self.verticalLayout.addWidget(self.label)

        self.export_location_container = QHBoxLayout()
        self.export_location_container.setObjectName("export_location_container")
        self.export_location_container.setSizeConstraint(QLayout.SetMaximumSize)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.setSizeConstraint(QLayout.SetMaximumSize)
        self.verticalLayout_2.setContentsMargins(-1, -1, 10, -1)
        self.export_location_label_2 = QLabel(self.verticalLayoutWidget)
        self.export_location_label_2.setObjectName("export_location_label_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.export_location_label_2.sizePolicy().hasHeightForWidth()
        )
        self.export_location_label_2.setSizePolicy(sizePolicy1)
        font = QFont()
        font.setBold(True)
        self.export_location_label_2.setFont(font)

        self.verticalLayout_2.addWidget(self.export_location_label_2)

        self.export_location_directory = QLabel(self.verticalLayoutWidget)
        self.export_location_directory.setObjectName("export_location_directory")
        sizePolicy2 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(
            self.export_location_directory.sizePolicy().hasHeightForWidth()
        )
        self.export_location_directory.setSizePolicy(sizePolicy2)
        self.export_location_directory.setWordWrap(True)
        self.export_location_directory.setMargin(2)

        self.verticalLayout_2.addWidget(self.export_location_directory)

        self.export_location_container.addLayout(self.verticalLayout_2)

        self.setExportLocationButton = QPushButton(self.verticalLayoutWidget)
        self.setExportLocationButton.setObjectName("setExportLocationButton")
        sizePolicy3 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(
            self.setExportLocationButton.sizePolicy().hasHeightForWidth()
        )
        self.setExportLocationButton.setSizePolicy(sizePolicy3)
        self.setExportLocationButton.setMaximumSize(QSize(200, 100))

        self.export_location_container.addWidget(self.setExportLocationButton)

        self.verticalLayout.addLayout(self.export_location_container)

        self.export_format_container = QHBoxLayout()
        self.export_format_container.setObjectName("export_format_container")
        self.export_format_container.setSizeConstraint(QLayout.SetMaximumSize)
        self.export_format_label = QLabel(self.verticalLayoutWidget)
        self.export_format_label.setObjectName("export_format_label")
        self.export_format_label.setFont(font)

        self.export_format_container.addWidget(self.export_format_label)

        self.export_format = QComboBox(self.verticalLayoutWidget)
        self.export_format.addItem("")
        self.export_format.setObjectName("export_format")
        self.export_format.setMaximumSize(QSize(200, 16777215))

        self.export_format_container.addWidget(self.export_format)

        self.verticalLayout.addLayout(self.export_format_container)

        self.verticalLayout.setStretch(0, 1)
        self.verticalLayout.setStretch(1, 1)
        self.verticalLayout.setStretch(2, 1)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.label.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p><span style=" font-size:14pt; font-weight:600;">Export Settings</span></p></body></html>',
                None,
            )
        )
        self.export_location_label_2.setText(
            QCoreApplication.translate("Form", "Export Location", None)
        )
        self.export_location_directory.setText(
            QCoreApplication.translate("Form", "Export Path", None)
        )
        self.setExportLocationButton.setText(
            QCoreApplication.translate("Form", "Set Location", None)
        )
        self.export_format_label.setText(
            QCoreApplication.translate("Form", "Export Format", None)
        )
        self.export_format.setItemText(
            0, QCoreApplication.translate("Form", "SVG", None)
        )

    # retranslateUi
