# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'export_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
    QLayout, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(500, 150)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(500, 150))
        Form.setMaximumSize(QSize(500, 150))
        Form.setBaseSize(QSize(500, 150))
        self.verticalLayoutWidget = QWidget(Form)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(9, 9, 481, 111))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.verticalLayoutWidget)
        self.label.setObjectName(u"label")
        self.label.setMaximumSize(QSize(1100, 23))

        self.verticalLayout.addWidget(self.label)

        self.export_location_container = QHBoxLayout()
        self.export_location_container.setObjectName(u"export_location_container")
        self.export_location_container.setSizeConstraint(QLayout.SetMaximumSize)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setSizeConstraint(QLayout.SetMaximumSize)
        self.export_location_label_2 = QLabel(self.verticalLayoutWidget)
        self.export_location_label_2.setObjectName(u"export_location_label_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.export_location_label_2.sizePolicy().hasHeightForWidth())
        self.export_location_label_2.setSizePolicy(sizePolicy1)
        font = QFont()
        font.setBold(True)
        self.export_location_label_2.setFont(font)

        self.verticalLayout_2.addWidget(self.export_location_label_2)

        self.export_location_directory = QLabel(self.verticalLayoutWidget)
        self.export_location_directory.setObjectName(u"export_location_directory")
        self.export_location_directory.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.export_location_directory)


        self.export_location_container.addLayout(self.verticalLayout_2)

        self.setExportLocationButton = QPushButton(self.verticalLayoutWidget)
        self.setExportLocationButton.setObjectName(u"setExportLocationButton")

        self.export_location_container.addWidget(self.setExportLocationButton)


        self.verticalLayout.addLayout(self.export_location_container)

        self.export_format_container = QHBoxLayout()
        self.export_format_container.setObjectName(u"export_format_container")
        self.export_format_container.setSizeConstraint(QLayout.SetMaximumSize)
        self.export_format_label = QLabel(self.verticalLayoutWidget)
        self.export_format_label.setObjectName(u"export_format_label")
        self.export_format_label.setFont(font)

        self.export_format_container.addWidget(self.export_format_label)

        self.export_format = QComboBox(self.verticalLayoutWidget)
        self.export_format.addItem("")
        self.export_format.setObjectName(u"export_format")

        self.export_format_container.addWidget(self.export_format)


        self.verticalLayout.addLayout(self.export_format_container)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label.setText(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:600;\">Export Settings</span></p></body></html>", None))
        self.export_location_label_2.setText(QCoreApplication.translate("Form", u"Export Location", None))
        self.export_location_directory.setText(QCoreApplication.translate("Form", u"TextLabel", None))
        self.setExportLocationButton.setText(QCoreApplication.translate("Form", u"Set Location", None))
        self.export_format_label.setText(QCoreApplication.translate("Form", u"Export Format", None))
        self.export_format.setItemText(0, QCoreApplication.translate("Form", u"SVG", None))

    # retranslateUi
