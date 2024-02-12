# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'plugin_settings_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QCommandLinkButton,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(700, 596)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMaximumSize(QSize(700, 16777215))
        self.verticalLayoutWidget = QWidget(Form)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(10, 10, 681, 121))
        self.verticalLayout_3 = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.plugin_name_label = QLabel(self.verticalLayoutWidget)
        self.plugin_name_label.setObjectName("plugin_name_label")
        font = QFont()
        font.setPointSize(12)
        self.plugin_name_label.setFont(font)

        self.horizontalLayout.addWidget(self.plugin_name_label)

        self.plugin_version_label = QLabel(self.verticalLayoutWidget)
        self.plugin_version_label.setObjectName("plugin_version_label")

        self.horizontalLayout.addWidget(self.plugin_version_label)

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.line = QFrame(self.verticalLayoutWidget)
        self.line.setObjectName("line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_3.addWidget(self.line)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pluginEnabled = QCheckBox(self.verticalLayoutWidget)
        self.pluginEnabled.setObjectName("pluginEnabled")
        sizePolicy1 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.pluginEnabled.sizePolicy().hasHeightForWidth()
        )
        self.pluginEnabled.setSizePolicy(sizePolicy1)
        font1 = QFont()
        font1.setPointSize(14)
        self.pluginEnabled.setFont(font1)

        self.horizontalLayout_2.addWidget(self.pluginEnabled)

        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Preferred, QSizePolicy.Minimum
        )

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.configureLink = QCommandLinkButton(self.verticalLayoutWidget)
        self.configureLink.setObjectName("configureLink")
        sizePolicy2 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(
            self.configureLink.sizePolicy().hasHeightForWidth()
        )
        self.configureLink.setSizePolicy(sizePolicy2)
        self.configureLink.setMaximumSize(QSize(400, 16777215))

        self.horizontalLayout_2.addWidget(self.configureLink)

        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_3 = QLabel(self.verticalLayoutWidget)
        self.label_3.setObjectName("label_3")

        self.horizontalLayout_3.addWidget(self.label_3)

        self.verticalLayout_3.addLayout(self.horizontalLayout_3)

        self.frame = QFrame(Form)
        self.frame.setObjectName("frame")
        self.frame.setGeometry(QRect(9, 102, 116, 33))
        self.frame.setAutoFillBackground(False)
        self.frame.setFrameShape(QFrame.Box)
        self.frame.setFrameShadow(QFrame.Plain)
        self.frame.setLineWidth(0)
        self.frame.setMidLineWidth(1)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName("verticalLayout_2")

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.plugin_name_label.setText(
            QCoreApplication.translate("Form", "Plugin_Name", None)
        )
        self.plugin_version_label.setText(
            QCoreApplication.translate("Form", "TextLabel", None)
        )
        self.pluginEnabled.setText(
            QCoreApplication.translate("Form", "Enable Plugin", None)
        )
        self.configureLink.setText(
            QCoreApplication.translate("Form", "Configure plugin", None)
        )
        self.configureLink.setDescription(
            QCoreApplication.translate("Form", "Select your file/folder", None)
        )
        self.label_3.setText(
            QCoreApplication.translate("Form", "No options available", None)
        )

    # retranslateUi
