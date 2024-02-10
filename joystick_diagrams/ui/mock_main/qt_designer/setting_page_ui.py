# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'setup_page_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(1024, 682)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(1024, 0))
        Form.setMaximumSize(QSize(1024, 16777215))
        Form.setBaseSize(QSize(1024, 0))
        self.verticalLayoutWidget = QWidget(Form)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(9, 9, 1012, 664))
        self.verticalLayout_2 = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pageTitle = QLabel(self.verticalLayoutWidget)
        self.pageTitle.setObjectName("pageTitle")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.pageTitle.sizePolicy().hasHeightForWidth())
        self.pageTitle.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.pageTitle)

        self.pageDescription = QLabel(self.verticalLayoutWidget)
        self.pageDescription.setObjectName("pageDescription")
        sizePolicy1.setHeightForWidth(
            self.pageDescription.sizePolicy().hasHeightForWidth()
        )
        self.pageDescription.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.pageDescription)

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.splitter = QSplitter(self.verticalLayoutWidget)
        self.splitter.setObjectName("splitter")
        sizePolicy2 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy2)
        self.splitter.setMaximumSize(QSize(16777215, 16777215))
        self.splitter.setOrientation(Qt.Horizontal)
        self.parserPluginList = QListWidget(self.splitter)
        brush = QBrush(QColor(0, 0, 0, 255))
        brush.setStyle(Qt.NoBrush)
        font = QFont()
        font.setFamilies(["Cascadia Code SemiBold"])
        font.setPointSize(12)
        font.setBold(True)
        __qlistwidgetitem = QListWidgetItem(self.parserPluginList)
        __qlistwidgetitem.setCheckState(Qt.Unchecked)
        __qlistwidgetitem.setFont(font)
        __qlistwidgetitem.setBackground(brush)
        __qlistwidgetitem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        icon = QIcon()
        icon.addFile(
            "../joystick_diagrams/ui/main_window/images/3rd_party/jg.ico",
            QSize(),
            QIcon.Normal,
            QIcon.Off,
        )
        __qlistwidgetitem1 = QListWidgetItem(self.parserPluginList)
        __qlistwidgetitem1.setFont(font)
        __qlistwidgetitem1.setIcon(icon)
        icon1 = QIcon()
        icon1.addFile(
            "../joystick_diagrams/ui/main_window/images/3rd_party/sc.png",
            QSize(),
            QIcon.Normal,
            QIcon.Off,
        )
        font1 = QFont()
        font1.setFamilies(["Cascadia Code SemiBold"])
        font1.setPointSize(11)
        font1.setBold(True)
        __qlistwidgetitem2 = QListWidgetItem(self.parserPluginList)
        __qlistwidgetitem2.setFont(font1)
        __qlistwidgetitem2.setIcon(icon1)
        self.parserPluginList.setObjectName("parserPluginList")
        sizePolicy3 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(
            self.parserPluginList.sizePolicy().hasHeightForWidth()
        )
        self.parserPluginList.setSizePolicy(sizePolicy3)
        self.parserPluginList.setMaximumSize(QSize(1087, 16777215))
        self.parserPluginList.setBaseSize(QSize(1, 0))
        self.splitter.addWidget(self.parserPluginList)
        self.pluginOptionsWidget = QWidget(self.splitter)
        self.pluginOptionsWidget.setObjectName("pluginOptionsWidget")
        sizePolicy.setHeightForWidth(
            self.pluginOptionsWidget.sizePolicy().hasHeightForWidth()
        )
        self.pluginOptionsWidget.setSizePolicy(sizePolicy)
        self.pluginOptionsWidget.setMinimumSize(QSize(600, 600))
        self.pluginOptionsWidget.setAutoFillBackground(False)
        self.horizontalLayout_6 = QHBoxLayout(self.pluginOptionsWidget)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.splitter.addWidget(self.pluginOptionsWidget)

        self.verticalLayout_4.addWidget(self.splitter)

        self.verticalLayout_3.addLayout(self.verticalLayout_4)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.splitter_2 = QSplitter(self.verticalLayoutWidget)
        self.splitter_2.setObjectName("splitter_2")
        sizePolicy1.setHeightForWidth(self.splitter_2.sizePolicy().hasHeightForWidth())
        self.splitter_2.setSizePolicy(sizePolicy1)
        self.splitter_2.setMinimumSize(QSize(1006, 23))
        self.splitter_2.setMaximumSize(QSize(16777215, 16777215))
        self.splitter_2.setOrientation(Qt.Horizontal)
        self.addParserPlugin = QPushButton(self.splitter_2)
        self.addParserPlugin.setObjectName("addParserPlugin")
        sizePolicy4 = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(
            self.addParserPlugin.sizePolicy().hasHeightForWidth()
        )
        self.addParserPlugin.setSizePolicy(sizePolicy4)
        self.splitter_2.addWidget(self.addParserPlugin)
        self.pushButton = QPushButton(self.splitter_2)
        self.pushButton.setObjectName("pushButton")
        self.splitter_2.addWidget(self.pushButton)

        self.verticalLayout_5.addWidget(self.splitter_2)

        self.verticalLayout_3.addLayout(self.verticalLayout_5)

        self.verticalLayout_2.addLayout(self.verticalLayout_3)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.pageTitle.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p><span style=" font-size:12pt; font-weight:600;">Plugin Setup</span></p></body></html>',
                None,
            )
        )
        self.pageDescription.setText(
            QCoreApplication.translate(
                "Form", "Setup your things... in order to customise stuff", None
            )
        )

        __sortingEnabled = self.parserPluginList.isSortingEnabled()
        self.parserPluginList.setSortingEnabled(False)
        ___qlistwidgetitem = self.parserPluginList.item(0)
        ___qlistwidgetitem.setText(
            QCoreApplication.translate("Form", "DCS World", None)
        )
        ___qlistwidgetitem1 = self.parserPluginList.item(1)
        ___qlistwidgetitem1.setText(
            QCoreApplication.translate("Form", "Joystick Gremlin", None)
        )
        ___qlistwidgetitem2 = self.parserPluginList.item(2)
        ___qlistwidgetitem2.setText(
            QCoreApplication.translate("Form", "Star Citizen PTOATO", None)
        )
        self.parserPluginList.setSortingEnabled(__sortingEnabled)

        self.addParserPlugin.setText(
            QCoreApplication.translate("Form", "Add Plugin", None)
        )
        self.pushButton.setText(
            QCoreApplication.translate("Form", "Remove Plugin", None)
        )

    # retranslateUi
