# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'setup_page_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
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
        Form.setBaseSize(QSize(1024, 0))
        font = QFont()
        font.setFamilies(["Bauhaus 93"])
        Form.setFont(font)
        self.verticalLayoutWidget = QWidget(Form)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(0, 0, 1081, 791))
        self.verticalLayout_2 = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.verticalLayoutWidget)
        self.label.setObjectName("label")

        self.verticalLayout_2.addWidget(self.label)

        self.line = QFrame(self.verticalLayoutWidget)
        self.line.setObjectName("line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_2.addWidget(self.line)

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

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.parserPluginList = QListWidget(self.verticalLayoutWidget)
        self.parserPluginList.setObjectName("parserPluginList")
        sizePolicy2 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(
            self.parserPluginList.sizePolicy().hasHeightForWidth()
        )
        self.parserPluginList.setSizePolicy(sizePolicy2)
        self.parserPluginList.setMaximumSize(QSize(300, 16777215))

        self.horizontalLayout_2.addWidget(self.parserPluginList)

        self.pluginOptionWidget = QWidget(self.verticalLayoutWidget)
        self.pluginOptionWidget.setObjectName("pluginOptionWidget")
        sizePolicy3 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(
            self.pluginOptionWidget.sizePolicy().hasHeightForWidth()
        )
        self.pluginOptionWidget.setSizePolicy(sizePolicy3)
        self.pluginOptionWidget.setMaximumSize(QSize(800, 16777215))

        self.horizontalLayout_2.addWidget(self.pluginOptionWidget)

        self.verticalLayout_4.addLayout(self.horizontalLayout_2)

        self.runButton = QPushButton(self.verticalLayoutWidget)
        self.runButton.setObjectName("runButton")

        self.verticalLayout_4.addWidget(self.runButton)

        self.verticalLayout_3.addLayout(self.verticalLayout_4)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName("verticalLayout_5")

        self.verticalLayout_3.addLayout(self.verticalLayout_5)

        self.verticalLayout_2.addLayout(self.verticalLayout_3)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.label.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p><span style=" font-size:14pt; font-weight:600;">Plugin Setup</span></p></body></html>',
                None,
            )
        )
        self.pageTitle.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p><span style=" font-size:12pt; font-weight:600;">Plugin Setup</span></p></body></html>',
                None,
            )
        )
        self.runButton.setText(QCoreApplication.translate("Form", "PushButton", None))

    # retranslateUi
