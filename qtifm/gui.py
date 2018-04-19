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
        self.setWindowIcon(QIcon(str(images_path.joinpath('qtifm512.png'))))

        # attrubutes
        self.current_file = None

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
        self.clear_recent_files_action = QAction(_('Clear Items'))

        # Menu Bar
        file_menu = self.menuBar().addMenu(_('File'))
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        self.recent_files_menu = file_menu.addMenu(_('Open recent'))
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

        # Widgets
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(5)

        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet('font-family: "Monospace";')

        self.cursor_position_label = QLabel()
        self.cursor_position_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))

        # Connects
        # self.dir_button.clicked.connect(self.select_dir)
        self.open_action.triggered.connect(self.open_file)
        self.about_action.triggered.connect(self.show_about_dialog)
        # self.settings_action.triggered.connect(self.show_settings_dialog)
        self.exit_action.triggered.connect(self.close)
        self.clear_recent_files_action.triggered.connect(self.clear_recent_files)
        # self.show_hidden_check.stateChanged.connect(self.update_dir)
        # self.file_list.itemDoubleClicked.connect(self.show_file)

        self.text_edit.cursorPositionChanged.connect(self.cursor_position_changed)

        # Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)  # left, top, right, bottom
        central_widget.setLayout(central_layout)
        central_layout.addWidget(self.splitter)
        self.statusBar().addWidget(self.cursor_position_label)

        # left_widget.setStyleSheet('margin: 0px;')
        self.splitter.addWidget(self.text_edit)

        self.update_title()
        self.cursor_position_changed()
        self.update_recent_files()

    @pyqtSlot()
    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    @pyqtSlot()
    def cursor_position_changed(self):
        cursor = self.text_edit.textCursor()
        self.cursor_position_label.setText(
            _('Line:') + ' ' + str(cursor.blockNumber() + 1) + ', ' + _('Column:') + ' ' + str(
                cursor.columnNumber() + 1))

    @pyqtSlot()
    def open_file(self):
        # file filter !
        filename, ignore = QFileDialog.getOpenFileName(self, _('Open'), '',
                                                       options=QFileDialog.DontUseNativeDialog,
                                                       filter='IFM files (*.ifm);;All files (*)')
        if filename:
            self.open_path(Path(filename))

    @pyqtSlot()
    def open_path(self, path):
        if path is not None and path.exists():
            self.text_edit.clear()
            self.current_file = None
            try:
                with open(path, 'r', encoding="utf-8") as file:
                    self.text_edit.insertPlainText(file.read())
                    self.text_edit.setFocus()
                    cursor = self.text_edit.textCursor()
                    cursor.setPosition(0)
                    self.text_edit.setTextCursor(cursor)
                    self.current_file = path
                    self.update_recent_files(path)
            except OSError:
                sys.stderr.write('Could not open IFM file: \'' + str(path) + '\'\n')
                traceback.print_exc(file=sys.stderr)
                QMessageBox.critical(self, _('Open'), _(
                    'An error occured while opening the selected IFM file!\n'
                    'Maybe it isn\'t an IFM file. See console output for details.'),
                                     QMessageBox.Ok)
            self.update_title()
        elif path is not None:
            QMessageBox.critical(self, _('Open'), _(
                'The file "' + str(path) + '" doesn\'t exist!'),
                                 QMessageBox.Ok)

    def update_title(self):
        filestr = ''
        if self.current_file is not None:
            try:
                filestr = '~/' + str(self.current_file.relative_to(Path.home()).as_posix()) + ' - '
            except ValueError:
                filestr = str(self.current_file.as_posix()) + ' - '
        appstr = _('qtIFM')
        self.setWindowTitle(filestr + appstr)

    def update_recent_files(self, path=None):
        if path is not None:
            if self.config.editor_recent_files.count(path) > 0:
                self.config.editor_recent_files.remove(path)
            self.config.editor_recent_files.insert(0, path)
            if len(self.config.editor_recent_files) > const.RECENT_FILES_COUNT:
                del self.config.editor_recent_files[-1]

        self.recent_files_menu.clear()
        if len(self.config.editor_recent_files) > 0:
            self.recent_files_menu.setEnabled(True)
            for path in self.config.editor_recent_files:
                action = self.recent_files_menu.addAction(path.name)
                action.triggered.connect(lambda l, p=path: self.open_path(p))
            self.recent_files_menu.addSeparator()
            self.recent_files_menu.addAction(self.clear_recent_files_action)
        else:
            self.recent_files_menu.setEnabled(False)

    @pyqtSlot()
    def clear_recent_files(self):
        self.config.editor_recent_files.clear()
        self.update_recent_files()

    def closeEvent(self, event):
        self.config.mainwindow_witdh = self.width()
        self.config.mainwindow_height = self.height()
        self.config.mainwindow_x = self.x()
        self.config.mainwindow_y = self.y()
        self.config.save()

        super(MainWindow, self).closeEvent(event)
