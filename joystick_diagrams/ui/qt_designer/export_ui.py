# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'export.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize
from PySide6.QtGui import QFont
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
        Form.resize(1100, 800)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(1100, 800))
        Form.setMaximumSize(QSize(1100, 16777215))
        font = QFont()
        font.setFamilies(["MS Sans Serif"])
        Form.setFont(font)
        self.layoutWidget = QWidget(Form)
        self.layoutWidget.setObjectName("layoutWidget")
        self.layoutWidget.setGeometry(QRect(0, 0, 1081, 621))
        self.layoutWidget.setMaximumSize(QSize(1100, 16777215))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName("label")
        self.label.setMaximumSize(QSize(1100, 23))

        self.verticalLayout.addWidget(self.label)

        self.line = QFrame(self.layoutWidget)
        self.line.setObjectName("line")
        self.line.setMaximumSize(QSize(1100, 16777215))
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.label_3 = QLabel(self.layoutWidget)
        self.label_3.setObjectName("label_3")
        self.label_3.setMaximumSize(QSize(1100, 16777215))
        font1 = QFont()
        font1.setPointSize(10)
        font1.setBold(True)
        self.label_3.setFont(font1)

        self.verticalLayout_4.addWidget(self.label_3)

        self.label_2 = QLabel(self.layoutWidget)
        self.label_2.setObjectName("label_2")
        self.label_2.setMaximumSize(QSize(1100, 16777215))

        self.verticalLayout_4.addWidget(self.label_2)

        self.horizontalLayout_2.addLayout(self.verticalLayout_4)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.setTemplateButton = QPushButton(self.layoutWidget)
        self.setTemplateButton.setObjectName("setTemplateButton")
        self.setTemplateButton.setMaximumSize(QSize(1100, 16777215))

        self.verticalLayout_5.addWidget(self.setTemplateButton)

        self.horizontalLayout_2.addLayout(self.verticalLayout_5)

        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SetMinAndMaxSize)

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.verticalLayout.addLayout(self.verticalLayout_3)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(-1, 30, -1, -1)
        self.export_settings_container = QHBoxLayout()
        self.export_settings_container.setObjectName("export_settings_container")
        self.export_settings_container.setContentsMargins(-1, -1, 50, -1)

        self.horizontalLayout_5.addLayout(self.export_settings_container)

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

        self.horizontalLayout_5.addWidget(self.ExportButton)

        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.label.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p><span style=" font-size:14pt; font-weight:600;">Export</span></p></body></html>',
                None,
            )
        )
        self.label_3.setText(
            QCoreApplication.translate("Form", "Device Templates", None)
        )
        self.label_2.setText(
            QCoreApplication.translate(
                "Form", "Only devices with templates will be exported", None
            )
        )
        self.setTemplateButton.setText(
            QCoreApplication.translate("Form", "PushButton", None)
        )
        self.ExportButton.setText(QCoreApplication.translate("Form", "Export", None))

    # retranslateUi
