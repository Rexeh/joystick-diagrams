# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'configure.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QSizePolicy,
    QTabWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(1100, 700)
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(1100, 700))
        Form.setMaximumSize(QSize(1100, 700))
        font = QFont()
        font.setFamilies(["Roboto"])
        Form.setFont(font)
        self.layoutWidget = QWidget(Form)
        self.layoutWidget.setObjectName("layoutWidget")
        self.layoutWidget.setGeometry(QRect(0, 0, 1081, 691))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(12, 8, 12, 8)
        self.heading_label = QLabel(self.layoutWidget)
        self.heading_label.setObjectName("heading_label")

        self.verticalLayout.addWidget(self.heading_label)

        self.tabWidget = QTabWidget(self.layoutWidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tabWidget.setMouseTracking(False)
        self.view_binds_tab = QWidget()
        self.view_binds_tab.setObjectName("view_binds_tab")
        self.viewBindsTabLayout = QVBoxLayout(self.view_binds_tab)
        self.viewBindsTabLayout.setObjectName("viewBindsTabLayout")
        self.viewBindsTabLayout.setContentsMargins(8, 8, 8, 8)
        self.viewBindsProfileList = QComboBox(self.view_binds_tab)
        self.viewBindsProfileList.setObjectName("viewBindsProfileList")
        self.viewBindsProfileList.setStyleSheet("color: rgb(255, 255, 255);")

        self.viewBindsTabLayout.addWidget(self.viewBindsProfileList)

        self.viewBindsTreeWidget = QTreeWidget(self.view_binds_tab)
        self.viewBindsTreeWidget.setObjectName("viewBindsTreeWidget")
        self.viewBindsTreeWidget.setProperty("showDropIndicator", False)
        self.viewBindsTreeWidget.setAlternatingRowColors(False)
        self.viewBindsTreeWidget.setRootIsDecorated(True)
        self.viewBindsTreeWidget.setUniformRowHeights(False)
        self.viewBindsTreeWidget.setSortingEnabled(True)
        self.viewBindsTreeWidget.setAnimated(True)
        self.viewBindsTreeWidget.setWordWrap(True)
        self.viewBindsTreeWidget.setHeaderHidden(True)
        self.viewBindsTreeWidget.header().setVisible(False)
        self.viewBindsTreeWidget.header().setCascadingSectionResizes(True)
        self.viewBindsTreeWidget.header().setHighlightSections(False)
        self.viewBindsTreeWidget.header().setProperty("showSortIndicator", True)
        self.viewBindsTreeWidget.header().setStretchLastSection(True)

        self.viewBindsTabLayout.addWidget(self.viewBindsTreeWidget)

        self.tabWidget.addTab(self.view_binds_tab, "")
        self.profile_setup_tab = QWidget()
        self.profile_setup_tab.setObjectName("profile_setup_tab")
        self.profileSetupTabLayout = QVBoxLayout(self.profile_setup_tab)
        self.profileSetupTabLayout.setObjectName("profileSetupTabLayout")
        self.profileSetupTabLayout.setContentsMargins(8, 8, 8, 8)
        self.label_3 = QLabel(self.profile_setup_tab)
        self.label_3.setObjectName("label_3")

        self.profileSetupTabLayout.addWidget(self.label_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.profileList = QListWidget(self.profile_setup_tab)
        self.profileList.setObjectName("profileList")
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

        self.profileSetupTabLayout.addLayout(self.horizontalLayout)

        self.tabWidget.addTab(self.profile_setup_tab, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(Form)

        self.tabWidget.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.heading_label.setText(
            QCoreApplication.translate("Form", "Customise & Review", None)
        )
        ___qtreewidgetitem = self.viewBindsTreeWidget.headerItem()
        ___qtreewidgetitem.setText(
            2, QCoreApplication.translate("Form", "Action", None)
        )
        ___qtreewidgetitem.setText(
            1, QCoreApplication.translate("Form", "Control", None)
        )
        ___qtreewidgetitem.setText(
            0, QCoreApplication.translate("Form", "Device", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.view_binds_tab),
            QCoreApplication.translate("Form", "View binds by Profile", None),
        )
        self.label_3.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p>Allows ability to <span style=" font-weight:600;">merge profiles together</span>, so a  single profile can inherit the binds of many others.</p></body></html>',
                None,
            )
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.profile_setup_tab),
            QCoreApplication.translate("Form", "Profile Setup", None),
        )

    # retranslateUi
