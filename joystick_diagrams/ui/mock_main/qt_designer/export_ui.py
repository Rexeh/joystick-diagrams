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
        Form.resize(1100, 800)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(1100, 800))
        font = QFont()
        font.setFamilies(["MS Sans Serif"])
        Form.setFont(font)
        self.layoutWidget = QWidget(Form)
        self.layoutWidget.setObjectName("layoutWidget")
        self.layoutWidget.setGeometry(QRect(0, 0, 981, 621))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName("label")
        self.label.setMaximumSize(QSize(16777215, 23))

        self.verticalLayout.addWidget(self.label)

        self.line = QFrame(self.layoutWidget)
        self.line.setObjectName("line")
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
        font1 = QFont()
        font1.setPointSize(10)
        font1.setBold(True)
        self.label_3.setFont(font1)

        self.verticalLayout_4.addWidget(self.label_3)

        self.label_2 = QLabel(self.layoutWidget)
        self.label_2.setObjectName("label_2")

        self.verticalLayout_4.addWidget(self.label_2)

        self.horizontalLayout_2.addLayout(self.verticalLayout_4)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.pushButton = QPushButton(self.layoutWidget)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setMaximumSize(QSize(250, 16777215))

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
        self.label_4 = QLabel(self.layoutWidget)
        self.label_4.setObjectName("label_4")
        self.label_4.setFont(font1)

        self.verticalLayout_6.addWidget(self.label_4)

        self.label_5 = QLabel(self.layoutWidget)
        self.label_5.setObjectName("label_5")

        self.verticalLayout_6.addWidget(self.label_5)

        self.pushButton_2 = QPushButton(self.layoutWidget)
        self.pushButton_2.setObjectName("pushButton_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.pushButton_2.sizePolicy().hasHeightForWidth()
        )
        self.pushButton_2.setSizePolicy(sizePolicy1)

        self.verticalLayout_6.addWidget(self.pushButton_2)

        self.horizontalLayout_4.addLayout(self.verticalLayout_6)

        self.horizontalLayout_3.addLayout(self.horizontalLayout_4)

        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.ExportButton = QPushButton(self.layoutWidget)
        self.ExportButton.setObjectName("ExportButton")

        self.verticalLayout.addWidget(self.ExportButton)

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
