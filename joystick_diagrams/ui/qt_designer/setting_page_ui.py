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
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(1100, 803)
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
        self.verticalLayout_2.setContentsMargins(0, 10, 0, 0)
        self.heading_label = QLabel(self.verticalLayoutWidget)
        self.heading_label.setObjectName("heading_label")

        self.verticalLayout_2.addWidget(self.heading_label)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pluginTreeHelpLabel = QLabel(self.verticalLayoutWidget)
        self.pluginTreeHelpLabel.setObjectName("pluginTreeHelpLabel")
        self.pluginTreeHelpLabel.setEnabled(True)

        self.horizontalLayout_2.addWidget(self.pluginTreeHelpLabel)

        self.installPlugin = QPushButton(self.verticalLayoutWidget)
        self.installPlugin.setObjectName("installPlugin")
        self.installPlugin.setEnabled(False)
        sizePolicy1 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.installPlugin.sizePolicy().hasHeightForWidth()
        )
        self.installPlugin.setSizePolicy(sizePolicy1)
        self.installPlugin.setMinimumSize(QSize(250, 0))
        self.installPlugin.setMaximumSize(QSize(250, 16777215))
        self.installPlugin.setFlat(False)

        self.horizontalLayout_2.addWidget(self.installPlugin)

        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.pluginContainer = QHBoxLayout()
        self.pluginContainer.setObjectName("pluginContainer")
        self.pluginContainer.setContentsMargins(5, -1, 5, -1)
        self.pluginTreeWidget = QTreeWidget(self.verticalLayoutWidget)
        self.pluginTreeWidget.headerItem().setText(4, "")
        QTreeWidgetItem(self.pluginTreeWidget)
        self.pluginTreeWidget.setObjectName("pluginTreeWidget")
        sizePolicy.setHeightForWidth(
            self.pluginTreeWidget.sizePolicy().hasHeightForWidth()
        )
        self.pluginTreeWidget.setSizePolicy(sizePolicy)
        self.pluginTreeWidget.setMinimumSize(QSize(0, 200))
        self.pluginTreeWidget.setMaximumSize(QSize(16777215, 500))
        font1 = QFont()
        font1.setPointSize(14)
        self.pluginTreeWidget.setFont(font1)
        self.pluginTreeWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pluginTreeWidget.setProperty("showDropIndicator", False)
        self.pluginTreeWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pluginTreeWidget.setIndentation(0)
        self.pluginTreeWidget.setRootIsDecorated(True)
        self.pluginTreeWidget.setItemsExpandable(False)
        self.pluginTreeWidget.header().setVisible(True)

        self.pluginContainer.addWidget(self.pluginTreeWidget)

        self.treeWidgetSidePanel = QVBoxLayout()
        self.treeWidgetSidePanel.setObjectName("treeWidgetSidePanel")

        self.pluginContainer.addLayout(self.treeWidgetSidePanel)

        self.verticalLayout_2.addLayout(self.pluginContainer)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.runPluginsButton = QPushButton(self.verticalLayoutWidget)
        self.runPluginsButton.setObjectName("runPluginsButton")

        self.horizontalLayout.addWidget(self.runPluginsButton)

        self.horizontalSpacer_2 = QSpacerItem(
            40, 20, QSizePolicy.Preferred, QSizePolicy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.verticalSpacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.verticalLayout_2.addItem(self.verticalSpacer)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.heading_label.setText(
            QCoreApplication.translate(
                "Form",
                '<html><head/><body><p><span style=" font-size:14pt; font-weight:600;">Plugin Setup</span></p></body></html>',
                None,
            )
        )
        self.pluginTreeHelpLabel.setText(
            QCoreApplication.translate("Form", "TextLabel", None)
        )
        self.installPlugin.setText(
            QCoreApplication.translate("Form", "Install Plugin", None)
        )
        ___qtreewidgetitem = self.pluginTreeWidget.headerItem()
        ___qtreewidgetitem.setText(
            3, QCoreApplication.translate("Form", "Errors", None)
        )
        ___qtreewidgetitem.setText(
            2, QCoreApplication.translate("Form", "Plugin Status", None)
        )
        ___qtreewidgetitem.setText(
            1, QCoreApplication.translate("Form", "Plugin Version", None)
        )
        ___qtreewidgetitem.setText(
            0, QCoreApplication.translate("Form", "Plugin Name", None)
        )

        __sortingEnabled = self.pluginTreeWidget.isSortingEnabled()
        self.pluginTreeWidget.setSortingEnabled(False)
        ___qtreewidgetitem1 = self.pluginTreeWidget.topLevelItem(0)
        ___qtreewidgetitem1.setText(3, QCoreApplication.translate("Form", "-", None))
        ___qtreewidgetitem1.setText(
            2, QCoreApplication.translate("Form", "Disabled", None)
        )
        ___qtreewidgetitem1.setText(1, QCoreApplication.translate("Form", "1.2", None))
        ___qtreewidgetitem1.setText(
            0, QCoreApplication.translate("Form", "DCS World", None)
        )
        self.pluginTreeWidget.setSortingEnabled(__sortingEnabled)

        self.runPluginsButton.setText(
            QCoreApplication.translate("Form", "Run (0) Plugins", None)
        )

    # retranslateUi
