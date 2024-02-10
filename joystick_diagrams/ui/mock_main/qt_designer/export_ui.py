# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'export.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(1041, 633)
        self.activeScreenWidget = QWidget(Form)
        self.activeScreenWidget.setObjectName("activeScreenWidget")
        self.activeScreenWidget.setGeometry(QRect(0, 0, 1041, 631))
        self.verticalLayout_2 = QVBoxLayout(self.activeScreenWidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QLabel(self.activeScreenWidget)
        self.label.setObjectName("label")

        self.verticalLayout.addWidget(self.label)

        self.verticalSpacer_2 = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Minimum
        )

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.label_3 = QLabel(self.activeScreenWidget)
        self.label_3.setObjectName("label_3")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.label_3.setFont(font)

        self.verticalLayout_4.addWidget(self.label_3)

        self.label_2 = QLabel(self.activeScreenWidget)
        self.label_2.setObjectName("label_2")

        self.verticalLayout_4.addWidget(self.label_2)

        self.horizontalLayout_2.addLayout(self.verticalLayout_4)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.pushButton = QPushButton(self.activeScreenWidget)
        self.pushButton.setObjectName("pushButton")

        self.verticalLayout_5.addWidget(self.pushButton)

        self.horizontalLayout_2.addLayout(self.verticalLayout_5)

        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.verticalLayout.addLayout(self.verticalLayout_3)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum
        )

        self.horizontalLayout_3.addItem(self.horizontalSpacer)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.label_4 = QLabel(self.activeScreenWidget)
        self.label_4.setObjectName("label_4")
        self.label_4.setFont(font)

        self.verticalLayout_6.addWidget(self.label_4)

        self.label_5 = QLabel(self.activeScreenWidget)
        self.label_5.setObjectName("label_5")

        self.verticalLayout_6.addWidget(self.label_5)

        self.pushButton_2 = QPushButton(self.activeScreenWidget)
        self.pushButton_2.setObjectName("pushButton_2")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_2.sizePolicy().hasHeightForWidth())
        self.pushButton_2.setSizePolicy(sizePolicy)

        self.verticalLayout_6.addWidget(self.pushButton_2)

        self.horizontalLayout_4.addLayout(self.verticalLayout_6)

        self.horizontalLayout_3.addLayout(self.horizontalLayout_4)

        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.ExportButton = QPushButton(self.activeScreenWidget)
        self.ExportButton.setObjectName("ExportButton")

        self.verticalLayout.addWidget(self.ExportButton)

        self.verticalLayout_2.addLayout(self.verticalLayout)

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
        self.pushButton.setText(QCoreApplication.translate("Form", "PushButton", None))
        self.label_4.setText(
            QCoreApplication.translate("Form", "Export Location", None)
        )
        self.label_5.setText(
            QCoreApplication.translate(
                "Form", "Where your diagrams will be exported", None
            )
        )
        self.pushButton_2.setText(
            QCoreApplication.translate("Form", "Sekect Folder", None)
        )
        self.ExportButton.setText(QCoreApplication.translate("Form", "Export", None))

    # retranslateUi
