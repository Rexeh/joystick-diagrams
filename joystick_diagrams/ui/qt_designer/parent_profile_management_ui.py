# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'parent_profile_management.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(400, 265)
        self._centralWidget = QWidget(Form)
        self._centralWidget.setObjectName("_centralWidget")
        self.verticalLayout = QVBoxLayout(self._centralWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self._centralWidget)
        self.label.setObjectName("label")
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.verticalLayout.addWidget(self.label)

        self.label_2 = QLabel(self._centralWidget)
        self.label_2.setObjectName("label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.listWidget = QListWidget(self._centralWidget)
        self.listWidget.setObjectName("listWidget")

        self.horizontalLayout.addWidget(self.listWidget)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.parentUp = QPushButton(self._centralWidget)
        self.parentUp.setObjectName("parentUp")

        self.verticalLayout_2.addWidget(self.parentUp)

        self.parentDown = QPushButton(self._centralWidget)
        self.parentDown.setObjectName("parentDown")

        self.verticalLayout_2.addWidget(self.parentDown)

        self.deleteParent = QPushButton(self._centralWidget)
        self.deleteParent.setObjectName("deleteParent")

        self.verticalLayout_2.addWidget(self.deleteParent)

        self.horizontalLayout.addLayout(self.verticalLayout_2)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.availableParentsComboBox = QComboBox(self._centralWidget)
        self.availableParentsComboBox.addItem("")
        self.availableParentsComboBox.addItem("")
        self.availableParentsComboBox.addItem("")
        self.availableParentsComboBox.setObjectName("availableParentsComboBox")
        self.availableParentsComboBox.setStyleSheet("color: rgb(255, 255, 255);")

        self.verticalLayout.addWidget(self.availableParentsComboBox)

        self.addParentItem = QPushButton(self._centralWidget)
        self.addParentItem.setObjectName("addParentItem")

        self.verticalLayout.addWidget(self.addParentItem)

        Form.setCentralWidget(self._centralWidget)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.label.setText(QCoreApplication.translate("Form", "Parents", None))
        self.label_2.setText(
            QCoreApplication.translate(
                "Form",
                "Adding parents will automatically add their binds to your profile",
                None,
            )
        )
        self.parentUp.setText(QCoreApplication.translate("Form", "Up", None))
        self.parentDown.setText(QCoreApplication.translate("Form", "Down", None))
        self.deleteParent.setText(QCoreApplication.translate("Form", "Delete", None))
        self.availableParentsComboBox.setItemText(
            0, QCoreApplication.translate("Form", "Profile1", None)
        )
        self.availableParentsComboBox.setItemText(
            1, QCoreApplication.translate("Form", "Profile2", None)
        )
        self.availableParentsComboBox.setItemText(
            2, QCoreApplication.translate("Form", "Profile3", None)
        )

        self.addParentItem.setText(
            QCoreApplication.translate("Form", "Add Parent", None)
        )

    # retranslateUi
