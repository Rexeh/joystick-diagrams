# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'configure.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QListView,
    QListWidget, QListWidgetItem, QSizePolicy, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1100, 700)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(1100, 700))
        Form.setMaximumSize(QSize(1100, 700))
        self.layoutWidget = QWidget(Form)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(0, 0, 1081, 691))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 10, 0, 0)
        self.heading_label = QLabel(self.layoutWidget)
        self.heading_label.setObjectName(u"heading_label")

        self.verticalLayout.addWidget(self.heading_label)

        self.line = QFrame(self.layoutWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.tabWidget = QTabWidget(self.layoutWidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setMouseTracking(False)
        self.view_binds_tab = QWidget()
        self.view_binds_tab.setObjectName(u"view_binds_tab")
        self.verticalLayoutWidget_2 = QWidget(self.view_binds_tab)
        self.verticalLayoutWidget_2.setObjectName(u"verticalLayoutWidget_2")
        self.verticalLayoutWidget_2.setGeometry(QRect(10, 10, 1001, 521))
        self.verticalLayout_3 = QVBoxLayout(self.verticalLayoutWidget_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.viewBindsProfileList = QComboBox(self.verticalLayoutWidget_2)
        self.viewBindsProfileList.addItem("")
        self.viewBindsProfileList.addItem("")
        self.viewBindsProfileList.setObjectName(u"viewBindsProfileList")
        self.viewBindsProfileList.setStyleSheet(u"color: rgb(255, 255, 255);")

        self.verticalLayout_3.addWidget(self.viewBindsProfileList)

        self.viewBindsTreeWidget = QTreeWidget(self.verticalLayoutWidget_2)
        QTreeWidgetItem(self.viewBindsTreeWidget)
        __qtreewidgetitem = QTreeWidgetItem(self.viewBindsTreeWidget)
        __qtreewidgetitem.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEditable|Qt.ItemIsDragEnabled|Qt.ItemIsUserCheckable|Qt.ItemIsEnabled);
        __qtreewidgetitem1 = QTreeWidgetItem(__qtreewidgetitem)
        __qtreewidgetitem1.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEditable|Qt.ItemIsDragEnabled|Qt.ItemIsUserCheckable|Qt.ItemIsEnabled);
        QTreeWidgetItem(__qtreewidgetitem)
        __qtreewidgetitem2 = QTreeWidgetItem(self.viewBindsTreeWidget)
        QTreeWidgetItem(__qtreewidgetitem2)
        self.viewBindsTreeWidget.setObjectName(u"viewBindsTreeWidget")
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

        self.verticalLayout_3.addWidget(self.viewBindsTreeWidget)

        self.tabWidget.addTab(self.view_binds_tab, "")
        self.profile_setup_tab = QWidget()
        self.profile_setup_tab.setObjectName(u"profile_setup_tab")
        self.verticalLayoutWidget = QWidget(self.profile_setup_tab)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(10, 10, 1091, 521))
        self.verticalLayout_4 = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.verticalLayoutWidget)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_4.addWidget(self.label_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.profileList = QListWidget(self.verticalLayoutWidget)
        QListWidgetItem(self.profileList)
        QListWidgetItem(self.profileList)
        QListWidgetItem(self.profileList)
        QListWidgetItem(self.profileList)
        QListWidgetItem(self.profileList)
        self.profileList.setObjectName(u"profileList")
        font = QFont()
        font.setFamilies([u"Sans Serif Collection"])
        self.profileList.setFont(font)
        self.profileList.setDragEnabled(True)
        self.profileList.setDragDropOverwriteMode(True)
        self.profileList.setDragDropMode(QAbstractItemView.DragOnly)
        self.profileList.setViewMode(QListView.ListMode)
        self.profileList.setSelectionRectVisible(False)

        self.horizontalLayout.addWidget(self.profileList)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")

        self.horizontalLayout.addLayout(self.verticalLayout_6)


        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.tabWidget.addTab(self.profile_setup_tab, "")

        self.verticalLayout.addWidget(self.tabWidget)


        self.retranslateUi(Form)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.heading_label.setText(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:600;\">Customise &amp; Review</span></p></body></html>", None))
        self.viewBindsProfileList.setItemText(0, QCoreApplication.translate("Form", u"FA-18", None))
        self.viewBindsProfileList.setItemText(1, QCoreApplication.translate("Form", u"A10-C", None))

        ___qtreewidgetitem = self.viewBindsTreeWidget.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("Form", u"Action", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("Form", u"Control", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("Form", u"Device", None));

        __sortingEnabled = self.viewBindsTreeWidget.isSortingEnabled()
        self.viewBindsTreeWidget.setSortingEnabled(False)
        ___qtreewidgetitem1 = self.viewBindsTreeWidget.topLevelItem(0)
        ___qtreewidgetitem1.setText(2, QCoreApplication.translate("Form", u"Go Fast", None));
        ___qtreewidgetitem1.setText(1, QCoreApplication.translate("Form", u"AXIS X", None));
        ___qtreewidgetitem1.setText(0, QCoreApplication.translate("Form", u"Throttle 1", None));
        ___qtreewidgetitem2 = self.viewBindsTreeWidget.topLevelItem(1)
        ___qtreewidgetitem2.setText(2, QCoreApplication.translate("Form", u"Fire Guns", None));
        ___qtreewidgetitem2.setText(1, QCoreApplication.translate("Form", u"BUTTON 1", None));
        ___qtreewidgetitem2.setText(0, QCoreApplication.translate("Form", u"Joystick_1", None));
        ___qtreewidgetitem3 = ___qtreewidgetitem2.child(0)
        ___qtreewidgetitem3.setText(2, QCoreApplication.translate("Form", u"Drop Ordnance", None));
        ___qtreewidgetitem3.setText(1, QCoreApplication.translate("Form", u"+CTRL", None));
        ___qtreewidgetitem3.setText(0, QCoreApplication.translate("Form", u"Modifier", None));
        ___qtreewidgetitem4 = ___qtreewidgetitem2.child(1)
        ___qtreewidgetitem4.setText(2, QCoreApplication.translate("Form", u"Drop something else", None));
        ___qtreewidgetitem4.setText(1, QCoreApplication.translate("Form", u"+CTRL ALT", None));
        ___qtreewidgetitem4.setText(0, QCoreApplication.translate("Form", u"Modifier", None));
        ___qtreewidgetitem5 = self.viewBindsTreeWidget.topLevelItem(2)
        ___qtreewidgetitem5.setText(2, QCoreApplication.translate("Form", u"Fire the lasers", None));
        ___qtreewidgetitem5.setText(1, QCoreApplication.translate("Form", u"BUTTON 2", None));
        ___qtreewidgetitem5.setText(0, QCoreApplication.translate("Form", u"Joystick_1", None));
        ___qtreewidgetitem6 = ___qtreewidgetitem5.child(0)
        ___qtreewidgetitem6.setText(2, QCoreApplication.translate("Form", u"Reload", None));
        ___qtreewidgetitem6.setText(1, QCoreApplication.translate("Form", u"+ ALT", None));
        ___qtreewidgetitem6.setText(0, QCoreApplication.translate("Form", u"Modifier", None));
        self.viewBindsTreeWidget.setSortingEnabled(__sortingEnabled)

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.view_binds_tab), QCoreApplication.translate("Form", u"View binds by Profile", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"<html><head/><body><p>Allows ability to <span style=\" font-weight:600;\">merge profiles together</span>, so a  single profile can inherit the binds of many others.</p></body></html>", None))

        __sortingEnabled1 = self.profileList.isSortingEnabled()
        self.profileList.setSortingEnabled(False)
        ___qlistwidgetitem = self.profileList.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("Form", u"DCS World - A10C2", None));
        ___qlistwidgetitem1 = self.profileList.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("Form", u"DCS World - FA18", None));
        ___qlistwidgetitem2 = self.profileList.item(2)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("Form", u"Joystick Gremlin - Base", None));
        ___qlistwidgetitem3 = self.profileList.item(3)
        ___qlistwidgetitem3.setText(QCoreApplication.translate("Form", u"Joystick Gremlin - A10C", None));
        ___qlistwidgetitem4 = self.profileList.item(4)
        ___qlistwidgetitem4.setText(QCoreApplication.translate("Form", u"Joystick Gremlin - FA18", None));
        self.profileList.setSortingEnabled(__sortingEnabled1)

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.profile_setup_tab), QCoreApplication.translate("Form", u"Profile Setup", None))
    # retranslateUi
