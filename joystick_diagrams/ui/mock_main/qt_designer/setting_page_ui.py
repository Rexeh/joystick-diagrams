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
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
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
            Form.setObjectName(u"Form")
        Form.resize(1053, 651)
        self.activeScreenWidget = QWidget(Form)
        self.activeScreenWidget.setObjectName(u"activeScreenWidget")
        self.activeScreenWidget.setGeometry(QRect(0, 0, 1041, 631))
        self.verticalLayout_2 = QVBoxLayout(self.activeScreenWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(self.activeScreenWidget)
        self.label.setObjectName(u"label")

        self.verticalLayout_2.addWidget(self.label)

        self.label_2 = QLabel(self.activeScreenWidget)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout_2.addWidget(self.label_2)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.parserPluginList = QListWidget(self.activeScreenWidget)
        icon = QIcon()
        icon.addFile(u"../joystick_diagrams/ui/main_window/images/3rd_party/dcs.ico", QSize(), QIcon.Normal, QIcon.Off)
        brush = QBrush(QColor(0, 0, 0, 255))
        brush.setStyle(Qt.NoBrush)
        font = QFont()
        font.setFamilies([u"Cascadia Code SemiBold"])
        font.setPointSize(12)
        font.setBold(True)
        __qlistwidgetitem = QListWidgetItem(self.parserPluginList)
        __qlistwidgetitem.setFont(font)
        __qlistwidgetitem.setBackground(brush)
        __qlistwidgetitem.setIcon(icon)
        icon1 = QIcon()
        icon1.addFile(u"../joystick_diagrams/ui/main_window/images/3rd_party/jg.ico", QSize(), QIcon.Normal, QIcon.Off)
        __qlistwidgetitem1 = QListWidgetItem(self.parserPluginList)
        __qlistwidgetitem1.setFont(font)
        __qlistwidgetitem1.setIcon(icon1)
        icon2 = QIcon()
        icon2.addFile(u"../joystick_diagrams/ui/main_window/images/3rd_party/sc.png", QSize(), QIcon.Normal, QIcon.Off)
        font1 = QFont()
        font1.setFamilies([u"Cascadia Code SemiBold"])
        font1.setPointSize(11)
        font1.setBold(True)
        __qlistwidgetitem2 = QListWidgetItem(self.parserPluginList)
        __qlistwidgetitem2.setFont(font1)
        __qlistwidgetitem2.setIcon(icon2)
        self.parserPluginList.setObjectName(u"parserPluginList")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.parserPluginList.sizePolicy().hasHeightForWidth())
        self.parserPluginList.setSizePolicy(sizePolicy)
        self.parserPluginList.setMaximumSize(QSize(1087, 16777215))

        self.horizontalLayout_2.addWidget(self.parserPluginList)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setSpacing(10)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.pluginOptionsWidget = QWidget(self.activeScreenWidget)
        self.pluginOptionsWidget.setObjectName(u"pluginOptionsWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.pluginOptionsWidget.sizePolicy().hasHeightForWidth())
        self.pluginOptionsWidget.setSizePolicy(sizePolicy1)
        self.pluginOptionsWidget.setMinimumSize(QSize(800, 600))
        self.pluginOptionsWidget.setAutoFillBackground(False)
        self.verticalLayoutWidget_4 = QWidget(self.pluginOptionsWidget)
        self.verticalLayoutWidget_4.setObjectName(u"verticalLayoutWidget_4")
        self.verticalLayoutWidget_4.setGeometry(QRect(0, 0, 821, 571))
        self.verticalLayout_4 = QVBoxLayout(self.verticalLayoutWidget_4)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.line_2 = QFrame(self.verticalLayoutWidget_4)
        self.line_2.setObjectName(u"line_2")
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.line_2.sizePolicy().hasHeightForWidth())
        self.line_2.setSizePolicy(sizePolicy2)
        self.line_2.setFrameShape(QFrame.HLine)
        self.line_2.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_4.addWidget(self.line_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pluginName = QLabel(self.verticalLayoutWidget_4)
        self.pluginName.setObjectName(u"pluginName")
        sizePolicy3 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.pluginName.sizePolicy().hasHeightForWidth())
        self.pluginName.setSizePolicy(sizePolicy3)
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.pluginName.setFont(font2)
        self.pluginName.setTextFormat(Qt.RichText)
        self.pluginName.setScaledContents(False)
        self.pluginName.setAlignment(Qt.AlignRight|Qt.AlignTop|Qt.AlignTrailing)
        self.pluginName.setWordWrap(False)

        self.horizontalLayout.addWidget(self.pluginName)

        self.pluginVersionInfo = QLabel(self.verticalLayoutWidget_4)
        self.pluginVersionInfo.setObjectName(u"pluginVersionInfo")
        sizePolicy3.setHeightForWidth(self.pluginVersionInfo.sizePolicy().hasHeightForWidth())
        self.pluginVersionInfo.setSizePolicy(sizePolicy3)
        self.pluginVersionInfo.setFont(font2)
        self.pluginVersionInfo.setTextFormat(Qt.RichText)
        self.pluginVersionInfo.setScaledContents(False)
        self.pluginVersionInfo.setAlignment(Qt.AlignRight|Qt.AlignTop|Qt.AlignTrailing)
        self.pluginVersionInfo.setWordWrap(False)

        self.horizontalLayout.addWidget(self.pluginVersionInfo)


        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.verticalLayout_4.addItem(self.verticalSpacer_2)

        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setSizeConstraint(QLayout.SetMaximumSize)
        self.formLayout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.pluginPath = QLabel(self.verticalLayoutWidget_4)
        self.pluginPath.setObjectName(u"pluginPath")
        sizePolicy4 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.pluginPath.sizePolicy().hasHeightForWidth())
        self.pluginPath.setSizePolicy(sizePolicy4)

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.pluginPath)

        self.pluginPathButton = QPushButton(self.verticalLayoutWidget_4)
        self.pluginPathButton.setObjectName(u"pluginPathButton")
        sizePolicy5 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.pluginPathButton.sizePolicy().hasHeightForWidth())
        self.pluginPathButton.setSizePolicy(sizePolicy5)
        self.pluginPathButton.setFlat(False)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.pluginPathButton)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")

        self.formLayout.setLayout(0, QFormLayout.LabelRole, self.verticalLayout_5)


        self.verticalLayout_4.addLayout(self.formLayout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)


        self.verticalLayout_3.addWidget(self.pluginOptionsWidget)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.pushButton_2 = QPushButton(self.activeScreenWidget)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.horizontalLayout_4.addWidget(self.pushButton_2)

        self.pushButton = QPushButton(self.activeScreenWidget)
        self.pushButton.setObjectName(u"pushButton")
        sizePolicy4.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy4)

        self.horizontalLayout_4.addWidget(self.pushButton)


        self.verticalLayout_3.addLayout(self.horizontalLayout_4)


        self.horizontalLayout_2.addLayout(self.verticalLayout_3)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.addParserPlugin = QPushButton(self.activeScreenWidget)
        self.addParserPlugin.setObjectName(u"addParserPlugin")
        sizePolicy5.setHeightForWidth(self.addParserPlugin.sizePolicy().hasHeightForWidth())
        self.addParserPlugin.setSizePolicy(sizePolicy5)

        self.horizontalLayout_3.addWidget(self.addParserPlugin)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label.setText(QCoreApplication.translate("Form", u'<html><head/><body><p><span style=" font-size:14pt; font-weight:600;">Configure</span></p></body></html>', None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Setup your things... in order to customise stuff", None))

        __sortingEnabled = self.parserPluginList.isSortingEnabled()
        self.parserPluginList.setSortingEnabled(False)
        ___qlistwidgetitem = self.parserPluginList.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("Form", u"DCS World", None))
        ___qlistwidgetitem1 = self.parserPluginList.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("Form", u"Joystick Gremlin", None))
        ___qlistwidgetitem2 = self.parserPluginList.item(2)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("Form", u"Star Citizen", None))
        self.parserPluginList.setSortingEnabled(__sortingEnabled)

        self.pluginName.setText(QCoreApplication.translate("Form", u"PLUGIN NAME", None))
        self.pluginVersionInfo.setText(QCoreApplication.translate("Form", u"PLUGIN VERSION", None))
        self.pluginPath.setText(QCoreApplication.translate("Form", u"Path to <file/folder>", None))
        self.pluginPathButton.setText(QCoreApplication.translate("Form", u"Select File/Folder", None))
        self.pushButton_2.setText(QCoreApplication.translate("Form", u"PushButton", None))
        self.pushButton.setText(QCoreApplication.translate("Form", u"PushButton", None))
        self.addParserPlugin.setText(QCoreApplication.translate("Form", u"Add Plugin", None))
    # retranslateUi

