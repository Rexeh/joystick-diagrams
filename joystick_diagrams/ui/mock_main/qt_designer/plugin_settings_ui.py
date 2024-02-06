# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'plugin_settings_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
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
        Form.resize(750, 596)
        Form.setMaximumSize(QSize(750, 600))
        self.verticalLayoutWidget = QWidget(Form)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(9, 9, 731, 87))
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

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pluginEnabled = QCheckBox(self.verticalLayoutWidget)
        self.pluginEnabled.setObjectName("pluginEnabled")
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pluginEnabled.sizePolicy().hasHeightForWidth())
        self.pluginEnabled.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setPointSize(14)
        self.pluginEnabled.setFont(font1)

        self.horizontalLayout_2.addWidget(self.pluginEnabled)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Preferred, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.configureLink = QCommandLinkButton(self.verticalLayoutWidget)
        self.configureLink.setObjectName("configureLink")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.configureLink.sizePolicy().hasHeightForWidth())
        self.configureLink.setSizePolicy(sizePolicy1)
        self.configureLink.setStyleSheet("color: rgb(255, 255, 255);\n" "selection-color: rgb(255, 255, 255);")

        self.horizontalLayout_2.addWidget(self.configureLink)

        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

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
        self.label_3 = QLabel(self.frame)
        self.label_3.setObjectName("label_3")

        self.verticalLayout_2.addWidget(self.label_3)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.plugin_name_label.setText(QCoreApplication.translate("Form", "Plugin_Name", None))
        self.plugin_version_label.setText(QCoreApplication.translate("Form", "TextLabel", None))
        self.pluginEnabled.setText(QCoreApplication.translate("Form", "Enable Plugin", None))
        self.configureLink.setText(QCoreApplication.translate("Form", "Configure plugin", None))
        self.configureLink.setDescription(QCoreApplication.translate("Form", "Select your file/folder", None))
        self.label_3.setText(QCoreApplication.translate("Form", "No options available", None))

    # retranslateUi
