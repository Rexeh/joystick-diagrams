# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'device_templates.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QMetaObject,
    QRect,
)
from PySide6.QtGui import (
    QFont,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
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
        Form.resize(453, 300)
        self.verticalLayoutWidget = QWidget(Form)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(0, 0, 451, 301))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.verticalLayoutWidget)
        self.label_2.setObjectName("label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.label = QLabel(self.verticalLayoutWidget)
        self.label.setObjectName("label")

        self.verticalLayout.addWidget(self.label)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.listWidget = QListWidget(self.verticalLayoutWidget)
        QListWidgetItem(self.listWidget)
        self.listWidget.setObjectName("listWidget")
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.listWidget.setFont(font)

        self.horizontalLayout.addWidget(self.listWidget)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.pushButton = QPushButton(self.verticalLayoutWidget)
        self.pushButton.setObjectName("pushButton")

        self.verticalLayout_2.addWidget(self.pushButton)

        self.horizontalLayout.addLayout(self.verticalLayout_2)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.verticalSpacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.verticalLayout.addItem(self.verticalSpacer)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.label_2.setText(QCoreApplication.translate("Form", "Devices", None))
        self.label.setText(
            QCoreApplication.translate(
                "Form", "Map your devices to a template file", None
            )
        )

        __sortingEnabled = self.listWidget.isSortingEnabled()
        self.listWidget.setSortingEnabled(False)
        ___qlistwidgetitem = self.listWidget.item(0)
        ___qlistwidgetitem.setText(
            QCoreApplication.translate(
                "Form", "Device Name - {2020202-022930293-923929320}", None
            )
        )
        self.listWidget.setSortingEnabled(__sortingEnabled)

        self.pushButton.setText(QCoreApplication.translate("Form", "PushButton", None))

    # retranslateUi
