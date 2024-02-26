# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QGridLayout,
    QHBoxLayout, QLayout, QMainWindow, QMenuBar,
    QPushButton, QSizePolicy, QSplitter, QStatusBar,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1100, 900)
        MainWindow.setMinimumSize(QSize(1100, 900))
        font = QFont()
        font.setFamilies([u"Century Gothic"])
        font.setBold(True)
        MainWindow.setFont(font)
        self.actionSubmenu_2 = QAction(MainWindow)
        self.actionSubmenu_2.setObjectName(u"actionSubmenu_2")
        self.actionSubmenu_2.setCheckable(True)
        self.actionSubmenu_3 = QAction(MainWindow)
        self.actionSubmenu_3.setObjectName(u"actionSubmenu_3")
        self.actionSUBSUB = QAction(MainWindow)
        self.actionSUBSUB.setObjectName(u"actionSUBSUB")
        self.actionSUBSUB_2 = QAction(MainWindow)
        self.actionSUBSUB_2.setObjectName(u"actionSUBSUB_2")
        self.actionSUBSUB_3 = QAction(MainWindow)
        self.actionSUBSUB_3.setObjectName(u"actionSUBSUB_3")
        self.actiondissabled = QAction(MainWindow)
        self.actiondissabled.setObjectName(u"actiondissabled")
        self.actiondissabled.setEnabled(False)
        self.actionSubmenu = QAction(MainWindow)
        self.actionSubmenu.setObjectName(u"actionSubmenu")
        self.actionSubmenu.setCheckable(True)
        self.actionSubmenu.setChecked(True)
        self.actionSubmenu_4 = QAction(MainWindow)
        self.actionSubmenu_4.setObjectName(u"actionSubmenu_4")
        self.actionSubmenu_4.setCheckable(True)
        self.actionSubmenu_5 = QAction(MainWindow)
        self.actionSubmenu_5.setObjectName(u"actionSubmenu_5")
        self.actionSubmenu_5.setCheckable(True)
        self.actionSubmenu_5.setEnabled(False)
        self.actionToolbar = QAction(MainWindow)
        self.actionToolbar.setObjectName(u"actionToolbar")
        self.actionSelected = QAction(MainWindow)
        self.actionSelected.setObjectName(u"actionSelected")
        self.actionSelected.setCheckable(True)
        self.actionSelected.setChecked(True)
        self.actionaction = QAction(MainWindow)
        self.actionaction.setObjectName(u"actionaction")
        self.actionaction2 = QAction(MainWindow)
        self.actionaction2.setObjectName(u"actionaction2")
        self.actionaction3 = QAction(MainWindow)
        self.actionaction3.setObjectName(u"actionaction3")
        self.action111 = QAction(MainWindow)
        self.action111.setObjectName(u"action111")
        self.action111.setCheckable(True)
        self.action222 = QAction(MainWindow)
        self.action222.setObjectName(u"action222")
        self.action222.setCheckable(True)
        self.action333 = QAction(MainWindow)
        self.action333.setObjectName(u"action333")
        self.action333.setCheckable(True)
        self.actionsubmenu = QAction(MainWindow)
        self.actionsubmenu.setObjectName(u"actionsubmenu")
        icon = QIcon()
        iconThemeName = u"document-new"
        if QIcon.hasThemeIcon(iconThemeName):
            icon = QIcon.fromTheme(iconThemeName)
        else:
            icon.addFile(u"../../../PythonCode/qt-material/examples/full_features", QSize(), QIcon.Normal, QIcon.Off)

        self.actionsubmenu.setIcon(icon)
        self.actionsubmenu_2 = QAction(MainWindow)
        self.actionsubmenu_2.setObjectName(u"actionsubmenu_2")
        icon1 = QIcon()
        iconThemeName = u"folder"
        if QIcon.hasThemeIcon(iconThemeName):
            icon1 = QIcon.fromTheme(iconThemeName)
        else:
            icon1.addFile(u"../../../PythonCode/qt-material/examples/full_features", QSize(), QIcon.Normal, QIcon.Off)

        self.actionsubmenu_2.setIcon(icon1)
        self.actionsubmenu_3 = QAction(MainWindow)
        self.actionsubmenu_3.setObjectName(u"actionsubmenu_3")
        icon2 = QIcon()
        iconThemeName = u"document-save-as"
        if QIcon.hasThemeIcon(iconThemeName):
            icon2 = QIcon.fromTheme(iconThemeName)
        else:
            icon2.addFile(u"../../../PythonCode/qt-material/examples/full_features", QSize(), QIcon.Normal, QIcon.Off)

        self.actionsubmenu_3.setIcon(icon2)
        self.actionsubmenu_4 = QAction(MainWindow)
        self.actionsubmenu_4.setObjectName(u"actionsubmenu_4")
        icon3 = QIcon()
        iconThemeName = u"document-save"
        if QIcon.hasThemeIcon(iconThemeName):
            icon3 = QIcon.fromTheme(iconThemeName)
        else:
            icon3.addFile(u"../../../PythonCode/qt-material/examples/full_features", QSize(), QIcon.Normal, QIcon.Off)

        self.actionsubmenu_4.setIcon(icon3)
        self.actionSave_all = QAction(MainWindow)
        self.actionSave_all.setObjectName(u"actionSave_all")
        self.actionClose = QAction(MainWindow)
        self.actionClose.setObjectName(u"actionClose")
        icon4 = QIcon()
        iconThemeName = u"window-close"
        if QIcon.hasThemeIcon(iconThemeName):
            icon4 = QIcon.fromTheme(iconThemeName)
        else:
            icon4.addFile(u"../../../PythonCode/qt-material/examples/full_features", QSize(), QIcon.Normal, QIcon.Off)

        self.actionClose.setIcon(icon4)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.splitter_2 = QSplitter(self.centralwidget)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setGeometry(QRect(0, 0, 0, 0))
        self.splitter_2.setOrientation(Qt.Vertical)
        self.gridLayout_17 = QGridLayout(self.centralwidget)
        self.gridLayout_17.setObjectName(u"gridLayout_17")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.topnav_additional_layout = QHBoxLayout()
        self.topnav_additional_layout.setObjectName(u"topnav_additional_layout")
        self.topnav_additional_layout.setContentsMargins(-1, -1, -1, 20)

        self.verticalLayout.addLayout(self.topnav_additional_layout)

        self.topnav_layout = QHBoxLayout()
        self.topnav_layout.setObjectName(u"topnav_layout")
        self.topnav_layout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.topnav_layout.setContentsMargins(-1, 25, -1, 50)
        self.setupSectionButton = QPushButton(self.centralwidget)
        self.buttonGroup_2 = QButtonGroup(MainWindow)
        self.buttonGroup_2.setObjectName(u"buttonGroup_2")
        self.buttonGroup_2.addButton(self.setupSectionButton)
        self.setupSectionButton.setObjectName(u"setupSectionButton")
        self.setupSectionButton.setAutoExclusive(True)

        self.topnav_layout.addWidget(self.setupSectionButton)

        self.customiseSectionButton = QPushButton(self.centralwidget)
        self.buttonGroup_2.addButton(self.customiseSectionButton)
        self.customiseSectionButton.setObjectName(u"customiseSectionButton")
        self.customiseSectionButton.setAutoExclusive(True)

        self.topnav_layout.addWidget(self.customiseSectionButton)

        self.exportSectionButton = QPushButton(self.centralwidget)
        self.buttonGroup_2.addButton(self.exportSectionButton)
        self.exportSectionButton.setObjectName(u"exportSectionButton")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.exportSectionButton.sizePolicy().hasHeightForWidth())
        self.exportSectionButton.setSizePolicy(sizePolicy)
        self.exportSectionButton.setAutoExclusive(True)

        self.topnav_layout.addWidget(self.exportSectionButton)


        self.verticalLayout.addLayout(self.topnav_layout)

        self.main_content_layout = QHBoxLayout()
        self.main_content_layout.setObjectName(u"main_content_layout")

        self.verticalLayout.addLayout(self.main_content_layout)

        self.line = QFrame(self.centralwidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)


        self.gridLayout_17.addLayout(self.verticalLayout, 1, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        self.statusbar.setEnabled(True)
        MainWindow.setStatusBar(self.statusbar)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1100, 21))
        self.menubar.setContextMenuPolicy(Qt.NoContextMenu)
        self.menubar.setNativeMenuBar(True)
        MainWindow.setMenuBar(self.menubar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Qt Material", None))
        self.actionSubmenu_2.setText(QCoreApplication.translate("MainWindow", u"Submenu", None))
        self.actionSubmenu_3.setText(QCoreApplication.translate("MainWindow", u"Submenu", None))
        self.actionSUBSUB.setText(QCoreApplication.translate("MainWindow", u"SUBSUB", None))
        self.actionSUBSUB_2.setText(QCoreApplication.translate("MainWindow", u"SUBSUB", None))
        self.actionSUBSUB_3.setText(QCoreApplication.translate("MainWindow", u"SUBSUB", None))
        self.actiondissabled.setText(QCoreApplication.translate("MainWindow", u"dissabled", None))
        self.actionSubmenu.setText(QCoreApplication.translate("MainWindow", u"Submenu", None))
        self.actionSubmenu_4.setText(QCoreApplication.translate("MainWindow", u"Submenu", None))
        self.actionSubmenu_5.setText(QCoreApplication.translate("MainWindow", u"Submenu", None))
        self.actionToolbar.setText(QCoreApplication.translate("MainWindow", u"Qt Material Theme", None))
#if QT_CONFIG(tooltip)
        self.actionToolbar.setToolTip(QCoreApplication.translate("MainWindow", u"Qt Material Theme", None))
#endif // QT_CONFIG(tooltip)
        self.actionSelected.setText(QCoreApplication.translate("MainWindow", u"Selected", None))
        self.actionaction.setText(QCoreApplication.translate("MainWindow", u"action", None))
        self.actionaction2.setText(QCoreApplication.translate("MainWindow", u"action2", None))
        self.actionaction3.setText(QCoreApplication.translate("MainWindow", u"action3", None))
        self.action111.setText(QCoreApplication.translate("MainWindow", u"111", None))
        self.action222.setText(QCoreApplication.translate("MainWindow", u"222", None))
        self.action333.setText(QCoreApplication.translate("MainWindow", u"333", None))
        self.actionsubmenu.setText(QCoreApplication.translate("MainWindow", u"New...", None))
        self.actionsubmenu_2.setText(QCoreApplication.translate("MainWindow", u"Open...", None))
        self.actionsubmenu_3.setText(QCoreApplication.translate("MainWindow", u"Save as...", None))
        self.actionsubmenu_4.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.actionSave_all.setText(QCoreApplication.translate("MainWindow", u"Save all", None))
        self.actionClose.setText(QCoreApplication.translate("MainWindow", u"Close", None))
        self.setupSectionButton.setText(QCoreApplication.translate("MainWindow", u"Setup", None))
        self.customiseSectionButton.setText(QCoreApplication.translate("MainWindow", u"Customise", None))
        self.exportSectionButton.setText(QCoreApplication.translate("MainWindow", u"Export", None))
    # retranslateUi
