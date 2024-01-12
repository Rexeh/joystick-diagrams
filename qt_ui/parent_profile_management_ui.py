# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'parent_profile_management.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(400, 265)
        self.verticalLayoutWidget = QWidget(Form)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(0, 0, 401, 261))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.verticalLayoutWidget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.verticalLayout.addWidget(self.label)

        self.label_2 = QLabel(self.verticalLayoutWidget)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.listWidget = QListWidget(self.verticalLayoutWidget)
        self.listWidget.setObjectName(u"listWidget")

        self.horizontalLayout.addWidget(self.listWidget)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.parentUp = QPushButton(self.verticalLayoutWidget)
        self.parentUp.setObjectName(u"parentUp")

        self.verticalLayout_2.addWidget(self.parentUp)

        self.parentDown = QPushButton(self.verticalLayoutWidget)
        self.parentDown.setObjectName(u"parentDown")

        self.verticalLayout_2.addWidget(self.parentDown)

        self.deleteParent = QPushButton(self.verticalLayoutWidget)
        self.deleteParent.setObjectName(u"deleteParent")

        self.verticalLayout_2.addWidget(self.deleteParent)


        self.horizontalLayout.addLayout(self.verticalLayout_2)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.availableParentsComboBox = QComboBox(self.verticalLayoutWidget)
        self.availableParentsComboBox.addItem("")
        self.availableParentsComboBox.addItem("")
        self.availableParentsComboBox.addItem("")
        self.availableParentsComboBox.setObjectName(u"availableParentsComboBox")
        self.availableParentsComboBox.setStyleSheet(u"color: rgb(255, 255, 255);")

        self.verticalLayout.addWidget(self.availableParentsComboBox)

        self.addParentItem = QPushButton(self.verticalLayoutWidget)
        self.addParentItem.setObjectName(u"addParentItem")

        self.verticalLayout.addWidget(self.addParentItem)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label.setText(QCoreApplication.translate("Form", u"Parents", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Adding parents will automatically add their binds to your profile", None))
        self.parentUp.setText(QCoreApplication.translate("Form", u"Up", None))
        self.parentDown.setText(QCoreApplication.translate("Form", u"Down", None))
        self.deleteParent.setText(QCoreApplication.translate("Form", u"Delete", None))
        self.availableParentsComboBox.setItemText(0, QCoreApplication.translate("Form", u"Profile1", None))
        self.availableParentsComboBox.setItemText(1, QCoreApplication.translate("Form", u"Profile2", None))
        self.availableParentsComboBox.setItemText(2, QCoreApplication.translate("Form", u"Profile3", None))

        self.addParentItem.setText(QCoreApplication.translate("Form", u"Add Parent", None))
    # retranslateUi

