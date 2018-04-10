#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# The gui
#

import constants as const
from config import Config

import gettext
import os
import sys
import traceback

from pathlib import Path
from zipfile import is_zipfile
from PyQt5.QtGui import QIcon, QPixmap, QTextCursor
from PyQt5.QtCore import pyqtSlot, Qt, QSize, QThread
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QMainWindow, QPlainTextEdit, QPushButton, QSizePolicy,
                             QSplitter, QVBoxLayout, QWidget, QFrame, QDialogButtonBox, QGridLayout, QLineEdit,
                             QMessageBox, QTextEdit, QTableWidgetItem, QListView, QLayout)

images_path = Path(__file__).parent.joinpath('images')
resources_path = Path(__file__).parent.joinpath('resources')

localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locales')
translate = gettext.translation('gui', localedir, fallback=True)
_ = translate.gettext


class AboutDialog(QDialog):

    def __init__(self, *args):
        QDialog.__init__(self, *args)
        self.setWindowTitle(_('About qtIFM'))

        dlglyt = QVBoxLayout()
        self.setLayout(dlglyt)

        info = QWidget()
        infolyt = QHBoxLayout()
        info.setLayout(infolyt)
        dlglyt.addWidget(info)

        pixmap = QPixmap(str(images_path.joinpath('qtifm48.png')))
        lbl = QLabel(self)
        lbl.setPixmap(pixmap)
        infolyt.addWidget(lbl)

        text = QWidget()
        textlyt = QVBoxLayout()
        text.setLayout(textlyt)
        infolyt.addWidget(text)
        appstr = _('qtIFM')
        l1 = QLabel(appstr + ' ' + const.VERSION)
        l1.setStyleSheet('font: bold')
        l2 = QLabel(_('Copyright © Jens Kieselbach'))
        textlyt.addWidget(l1)
        textlyt.addWidget(l2)
        infolyt.addStretch()

        textedit = QPlainTextEdit(self)

        try:
            file = open(resources_path.joinpath('LICENSE'), 'r', encoding="utf-8")
            textedit.insertPlainText(file.read())
        except Exception as e:
            textedit.insertPlainText(str(e))

        textedit.moveCursor(QTextCursor.Start)
        textedit.setTextInteractionFlags(Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse)
        textedit.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        textedit.setStyleSheet('font: 9pt "Monospace"')
        dlglyt.addWidget(textedit)

        # button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        dlglyt.addWidget(button_box)

        self.resize(600, 400)


class MainWindow(QMainWindow):

    def __init__(self, *args):
        QMainWindow.__init__(self, *args)
        appstr = _('qtIFM')
        self.setWindowTitle(appstr + ' ' + const.VERSION)
        self.setWindowIcon(QIcon(str(images_path.joinpath('qtifm512.png'))))

        # load config
        self.config = Config()
        self.config.load()

        self.move(self.config.mainwindow_x, self.config.mainwindow_y)
        self.resize(self.config.mainwindow_witdh, self.config.mainwindow_height)

        # Actions
        self.exit_action = QAction(_('Exit'), self)
        self.exit_action.setMenuRole(QAction.QuitRole)
        self.exit_action.setShortcut('Ctrl+Q')
        self.about_action = QAction(_('About'), self)
        self.about_action.setMenuRole(QAction.AboutRole)

        self.new_action = QAction(QIcon.fromTheme('document-new'), _('New'))
        self.new_action.setShortcut('Ctrl+N')
        self.open_action = QAction(QIcon.fromTheme('document-open'), _('Open...'))
        self.open_action.setShortcut('Ctrl+O')
        self.save_action = QAction(QIcon.fromTheme('document-save'), _('Save'))
        self.save_action.setShortcut('Ctrl+S')
        self.saveas_action = QAction(QIcon.fromTheme('document-save-as'), _('Save As...'))
        self.saveas_action.setShortcut('Shift+Ctrl+S')

        # Menu Bar
        file_menu = self.menuBar().addMenu(_('File'))
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.saveas_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        help_menu = self.menuBar().addMenu(_('Help'))
        help_menu.addAction(self.about_action)

        # Tool bar
        tool_bar = self.addToolBar('Edit')
        tool_bar.setFloatable(False)
        tool_bar.setMovable(False)
        tool_bar.addAction(self.new_action)
        tool_bar.addAction(self.open_action)
        tool_bar.addAction(self.save_action)
        tool_bar.addAction(self.saveas_action)

        # self.statusBar().setStyleSheet('margin-bottom: 2px;')
        self.statusBar().showMessage('Ready')

        # Widgets
        self.splitter = QSplitter(Qt.Horizontal)
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet('font-family: "Monospace";')

        # self.rp9_viewer = Rp9Viewer(self.config)
        # self.file_list = QListWidget()
        # self.file_list.setSelectionMode(QAbstractItemView.SingleSelection)
        # self.dir_button = QPushButton(QIcon.fromTheme('folder-open'), '', self)
        # self.show_hidden_check = QCheckBox(_('Show hidden files'), self)

        # Connects
        # self.dir_button.clicked.connect(self.select_dir)
        self.about_action.triggered.connect(self.show_about_dialog)
        # self.settings_action.triggered.connect(self.show_settings_dialog)
        self.exit_action.triggered.connect(self.close)
        # self.show_hidden_check.stateChanged.connect(self.update_dir)
        # self.file_list.itemDoubleClicked.connect(self.show_file)

        self.text_edit.cursorPositionChanged.connect(self.cursor_position_changed)

        # Layout
        self.setCentralWidget(self.splitter)

        left_widget = QWidget()
        # left_widget.setStyleSheet('margin: 0px;')
        self.splitter.addWidget(left_widget)
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        left_layout.addWidget(self.text_edit)
        # left_layout.addWidget(self.file_list)
        # left_layout.addWidget(self.show_hidden_check)

        # self.splitter.addWidget(self.rp9_viewer)

    @pyqtSlot()
    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    @pyqtSlot()
    def cursor_position_changed(self):
        cursor = self.text_edit.textCursor()
        self.statusBar().showMessage(
            'Line: ' + str(cursor.blockNumber() + 1) + ', Column: ' + str(cursor.columnNumber() + 1))

    def closeEvent(self, event):
        self.config.mainwindow_witdh = self.width()
        self.config.mainwindow_height = self.height()
        self.config.mainwindow_x = self.x()
        self.config.mainwindow_y = self.y()
        self.config.save()

        super(MainWindow, self).closeEvent(event)
