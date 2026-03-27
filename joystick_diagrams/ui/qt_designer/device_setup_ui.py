# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'device_setup.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QSize
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(1116, 430)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(0, 200))
        self._centralWidget = QWidget(Form)
        self._centralWidget.setObjectName("_centralWidget")
        self.verticalLayout = QVBoxLayout(self._centralWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 10)
        self.treeWidget = QTreeWidget(self._centralWidget)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, "1")
        self.treeWidget.setHeaderItem(__qtreewidgetitem)
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.setMinimumSize(QSize(0, 150))
        self.treeWidget.setMaximumSize(QSize(16777215, 16777215))
        self.treeWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.treeWidget.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self.treeWidget.setWordWrap(True)

        self.verticalLayout.addWidget(self.treeWidget)

        Form.setCentralWidget(self._centralWidget)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))

    # retranslateUi
