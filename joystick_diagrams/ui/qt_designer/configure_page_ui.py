# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'configure.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
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
        self.layoutWidget = QWidget(Form)
        self.layoutWidget.setObjectName("layoutWidget")
        self.layoutWidget.setGeometry(QRect(0, 0, 1081, 791))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName("label")

        self.verticalLayout.addWidget(self.label)

        self.line = QFrame(self.layoutWidget)
        self.line.setObjectName("line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.tabWidget = QTabWidget(self.layoutWidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayoutWidget = QWidget(self.tab_2)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(10, 10, 1091, 521))
        self.verticalLayout_4 = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.verticalLayoutWidget)
        self.label_3.setObjectName("label_3")

        self.verticalLayout_4.addWidget(self.label_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.profileList = QListWidget(self.verticalLayoutWidget)
        QListWidgetItem(self.profileList)
        QListWidgetItem(self.profileList)
        QListWidgetItem(self.profileList)
        QListWidgetItem(self.profileList)
        QListWidgetItem(self.profileList)
        self.profileList.setObjectName("profileList")
        font = QFont()
        font.setFamilies(["Sans Serif Collection"])
        self.profileList.setFont(font)
        self.profileList.setDragEnabled(True)
        self.profileList.setDragDropOverwriteMode(True)
        self.profileList.setDragDropMode(QAbstractItemView.DragOnly)
        self.profileList.setViewMode(QListView.ListMode)
        self.profileList.setSelectionRectVisible(False)

        self.horizontalLayout.addWidget(self.profileList)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName("verticalLayout_6")

        self.horizontalLayout.addLayout(self.verticalLayout_6)

        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName("tab_3")
        self.verticalLayoutWidget_2 = QWidget(self.tab_3)
        self.verticalLayoutWidget_2.setObjectName("verticalLayoutWidget_2")
        self.verticalLayoutWidget_2.setGeometry(QRect(10, 10, 1001, 521))
        self.verticalLayout_3 = QVBoxLayout(self.verticalLayoutWidget_2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.comboBox = QComboBox(self.verticalLayoutWidget_2)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName("comboBox")
        self.comboBox.setStyleSheet("color: rgb(255, 255, 255);")

        self.verticalLayout_3.addWidget(self.comboBox)

        self.treeWidget = QTreeWidget(self.verticalLayoutWidget_2)
        QTreeWidgetItem(self.treeWidget)
        __qtreewidgetitem = QTreeWidgetItem(self.treeWidget)
        __qtreewidgetitem.setFlags(
            Qt.ItemIsSelectable
            | Qt.ItemIsEditable
            | Qt.ItemIsDragEnabled
            | Qt.ItemIsUserCheckable
            | Qt.ItemIsEnabled
        )
        __qtreewidgetitem1 = QTreeWidgetItem(__qtreewidgetitem)
        __qtreewidgetitem1.setFlags(
            Qt.ItemIsSelectable
            | Qt.ItemIsEditable
            | Qt.ItemIsDragEnabled
            | Qt.ItemIsUserCheckable
            | Qt.ItemIsEnabled
        )
        QTreeWidgetItem(__qtreewidgetitem)
        __qtreewidgetitem2 = QTreeWidgetItem(self.treeWidget)
        QTreeWidgetItem(__qtreewidgetitem2)
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.setProperty("showDropIndicator", False)
        self.treeWidget.setAlternatingRowColors(False)
        self.treeWidget.setRootIsDecorated(True)
        self.treeWidget.setUniformRowHeights(False)
        self.treeWidget.setSortingEnabled(True)
        self.treeWidget.setAnimated(True)
        self.treeWidget.setWordWrap(True)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.header().setVisible(False)
        self.treeWidget.header().setCascadingSectionResizes(True)
        self.treeWidget.header().setHighlightSections(False)
        self.treeWidget.header().setProperty("showSortIndicator", True)
        self.treeWidget.header().setStretchLastSection(True)

        self.verticalLayout_3.addWidget(self.treeWidget)

        self.tabWidget.addTab(self.tab_3, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(Form)

        self.tabWidget.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.label.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p><span style=" font-size:14pt; font-weight:600;">Configure &amp; Review</span></p></body></html>',
                None,
            )
        )
        self.label_3.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p>Allows ability to <span style=" font-weight:600;">merge profiles together</span>, so a  single profile can inherit the binds of many others.</p></body></html>',
                None,
            )
        )

        __sortingEnabled = self.profileList.isSortingEnabled()
        self.profileList.setSortingEnabled(False)
        ___qlistwidgetitem = self.profileList.item(0)
        ___qlistwidgetitem.setText(
            QCoreApplication.translate("Form", "DCS World - A10C2", None)
        )
        ___qlistwidgetitem1 = self.profileList.item(1)
        ___qlistwidgetitem1.setText(
            QCoreApplication.translate("Form", "DCS World - FA18", None)
        )
        ___qlistwidgetitem2 = self.profileList.item(2)
        ___qlistwidgetitem2.setText(
            QCoreApplication.translate("Form", "Joystick Gremlin - Base", None)
        )
        ___qlistwidgetitem3 = self.profileList.item(3)
        ___qlistwidgetitem3.setText(
            QCoreApplication.translate("Form", "Joystick Gremlin - A10C", None)
        )
        ___qlistwidgetitem4 = self.profileList.item(4)
        ___qlistwidgetitem4.setText(
            QCoreApplication.translate("Form", "Joystick Gremlin - FA18", None)
        )
        self.profileList.setSortingEnabled(__sortingEnabled)

        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_2),
            QCoreApplication.translate("Form", "Profile Setup", None),
        )
        self.comboBox.setItemText(0, QCoreApplication.translate("Form", "FA-18", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("Form", "A10-C", None))

        ___qtreewidgetitem = self.treeWidget.headerItem()
        ___qtreewidgetitem.setText(
            2, QCoreApplication.translate("Form", "Action", None)
        )
        ___qtreewidgetitem.setText(
            1, QCoreApplication.translate("Form", "Control", None)
        )
        ___qtreewidgetitem.setText(
            0, QCoreApplication.translate("Form", "Device", None)
        )

        __sortingEnabled1 = self.treeWidget.isSortingEnabled()
        self.treeWidget.setSortingEnabled(False)
        ___qtreewidgetitem1 = self.treeWidget.topLevelItem(0)
        ___qtreewidgetitem1.setText(
            2, QCoreApplication.translate("Form", "Go Fast", None)
        )
        ___qtreewidgetitem1.setText(
            1, QCoreApplication.translate("Form", "AXIS X", None)
        )
        ___qtreewidgetitem1.setText(
            0, QCoreApplication.translate("Form", "Throttle 1", None)
        )
        ___qtreewidgetitem2 = self.treeWidget.topLevelItem(1)
        ___qtreewidgetitem2.setText(
            2, QCoreApplication.translate("Form", "Fire Guns", None)
        )
        ___qtreewidgetitem2.setText(
            1, QCoreApplication.translate("Form", "BUTTON 1", None)
        )
        ___qtreewidgetitem2.setText(
            0, QCoreApplication.translate("Form", "Joystick_1", None)
        )
        ___qtreewidgetitem3 = ___qtreewidgetitem2.child(0)
        ___qtreewidgetitem3.setText(
            2, QCoreApplication.translate("Form", "Drop Ordnance", None)
        )
        ___qtreewidgetitem3.setText(
            1, QCoreApplication.translate("Form", "+CTRL", None)
        )
        ___qtreewidgetitem3.setText(
            0, QCoreApplication.translate("Form", "Modifier", None)
        )
        ___qtreewidgetitem4 = ___qtreewidgetitem2.child(1)
        ___qtreewidgetitem4.setText(
            2, QCoreApplication.translate("Form", "Drop something else", None)
        )
        ___qtreewidgetitem4.setText(
            1, QCoreApplication.translate("Form", "+CTRL ALT", None)
        )
        ___qtreewidgetitem4.setText(
            0, QCoreApplication.translate("Form", "Modifier", None)
        )
        ___qtreewidgetitem5 = self.treeWidget.topLevelItem(2)
        ___qtreewidgetitem5.setText(
            2, QCoreApplication.translate("Form", "Fire the lasers", None)
        )
        ___qtreewidgetitem5.setText(
            1, QCoreApplication.translate("Form", "BUTTON 2", None)
        )
        ___qtreewidgetitem5.setText(
            0, QCoreApplication.translate("Form", "Joystick_1", None)
        )
        ___qtreewidgetitem6 = ___qtreewidgetitem5.child(0)
        ___qtreewidgetitem6.setText(
            2, QCoreApplication.translate("Form", "Reload", None)
        )
        ___qtreewidgetitem6.setText(
            1, QCoreApplication.translate("Form", "+ ALT", None)
        )
        ___qtreewidgetitem6.setText(
            0, QCoreApplication.translate("Form", "Modifier", None)
        )
        self.treeWidget.setSortingEnabled(__sortingEnabled1)

        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_3),
            QCoreApplication.translate("Form", "View binds by Profile", None),
        )

    # retranslateUi