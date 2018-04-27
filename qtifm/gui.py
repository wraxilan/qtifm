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
from PyQt5.QtGui import QColor, QIcon, QFont, QPixmap, QSyntaxHighlighter, QTextCursor, QTextCharFormat
from PyQt5.QtCore import pyqtSlot, Qt, QFile, QRegExp, QSize, QThread
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

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        dlglyt.addWidget(button_box)

        self.resize(600, 400)


class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(Highlighter, self).__init__(parent)

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.yellow)
        keyword_patterns = ["\\btitle\\b", "\\bmap\\b", "\\brequire\\b"]
        self.highlightingRules = [(QRegExp(pattern), keyword_format)
                                  for pattern in keyword_patterns]

        quotation_format = QTextCharFormat()
        quotation_format.setForeground(QColor(180, 200, 255))
        self.highlightingRules.append((QRegExp("\".*\""), quotation_format))

        single_line_comment_format = QTextCharFormat()
        single_line_comment_format.setForeground(Qt.darkGray)
        self.highlightingRules.append((QRegExp("#[^\n]*"),
                                       single_line_comment_format))

    def highlightBlock(self, text):
        for pattern, highlight_format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, highlight_format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)


class Editor(QTextEdit):

    def __init__(self, mainwin, *args):
        QTextEdit.__init__(self, *args)

        self.main_window = mainwin
        self.config = mainwin.config
        self.setStyleSheet('font-family: "Monospace";')
        self.highlighter = Highlighter(self.document())

        self.current_file = None
        self.current_file_name = ''
        self.saveable = False

        # cursor position handling
        self.cursor_position_label = QLabel()
        self.cursor_position_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
        self.cursorPositionChanged.connect(self.cursor_position_changed)
        self.cursor_position_changed()

        # content modified handling
        self.editor_init = True
        self.editor_modified = False
        self.editor_modified_label = QLabel()
        self.editor_modified_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
        self.textChanged.connect(self.text_changed)

        self.update_state()

    @pyqtSlot()
    def cursor_position_changed(self):
        cursor = self.textCursor()
        self.cursor_position_label.setText(
            _('Line:') + ' ' + str(cursor.blockNumber() + 1) + ', ' + _('Column:') + ' ' + str(
                cursor.columnNumber() + 1))

    @pyqtSlot()
    def text_changed(self):
        if self.editor_init:
            self.editor_init = False
            self.editor_modified = False
            self.editor_modified_label.setText('')
        elif not self.editor_modified:
            self.editor_modified = True
            self.editor_modified_label.setText(_('Modified'))

    def abort_if_modified(self, title):
        if self.editor_modified:
            choice = QMessageBox.question(self.main_window, title,
                                          _('There are unsaved changes. Continue anyway?'),
                                          QMessageBox.Yes | QMessageBox.No)
            return choice != QMessageBox.Yes
        return False

    @pyqtSlot()
    def open_file(self):
        if self.abort_if_modified(_('Open')):
            return

        filename, ignore = QFileDialog.getOpenFileName(self.main_window, _('Open'), '',
                                                       options=QFileDialog.DontUseNativeDialog,
                                                       filter='IFM files (*.ifm);;All files (*)')
        if filename:
            self.open_path(Path(filename), check_modified=False)

    @pyqtSlot()
    def open_path(self, path, check_modified=True):

        if check_modified and self.abort_if_modified(_('Open')):
            return

        if path is not None and path.exists():
            self.editor_init = True
            self.clear()
            self.current_file = None
            try:
                with open(path, 'r', encoding="utf-8") as file:
                    self.editor_init = True
                    self.insertPlainText(file.read())
                    self.setFocus()
                    cursor = self.textCursor()
                    cursor.setPosition(0)
                    self.setTextCursor(cursor)
                    self.current_file = path

            except OSError:
                sys.stderr.write('Could not open IFM file: \'' + str(path) + '\'\n')
                traceback.print_exc(file=sys.stderr)
                QMessageBox.critical(self, _('Open'), _(
                    'An error occured while opening the selected IFM file!\n'
                    'Maybe it isn\'t an IFM file. See console output for details.'),
                                     QMessageBox.Ok)
            self.update_state(self.current_file)
        elif path is not None:
            QMessageBox.critical(self, _('Open'), _(
                'The file "' + str(path) + '" doesn\'t exist!'),
                                 QMessageBox.Ok)

    def update_state(self, path=None):
        self.saveable = False
        self.current_file_name = ''
        if self.current_file is not None:
            self.saveable = True
            try:
                self.current_file_name = '~/' + str(self.current_file.relative_to(Path.home()).as_posix()) + ' - '
            except ValueError:
                self.current_file_name = str(self.current_file.as_posix()) + ' - '

        if path is not None:
            if self.config.editor_recent_files.count(path) > 0:
                self.config.editor_recent_files.remove(path)
            self.config.editor_recent_files.insert(0, path)
            if len(self.config.editor_recent_files) > const.RECENT_FILES_COUNT:
                del self.config.editor_recent_files[-1]

        self.main_window.recent_files_menu.clear()
        if len(self.config.editor_recent_files) > 0:
            self.main_window.recent_files_menu.setEnabled(True)
            for path in self.config.editor_recent_files:
                action = self.main_window.recent_files_menu.addAction(path.name)
                action.triggered.connect(lambda l, p=path: self.open_path(p))
            self.main_window.recent_files_menu.addSeparator()
            self.main_window.recent_files_menu.addAction(self.main_window.clear_recent_files_action)
        else:
            self.main_window.recent_files_menu.setEnabled(False)

        appstr = _('qtIFM')
        self.main_window.setWindowTitle(self.current_file_name + appstr)
        self.main_window.save_action.setEnabled(self.saveable)

    @pyqtSlot()
    def clear_recent_files(self):
        self.config.editor_recent_files.clear()
        self.update_state()

    @pyqtSlot()
    def save_file(self, update=False):
        if self.current_file is not None:
            try:
                with open(self.current_file, 'w', encoding="utf-8") as file:
                    file.write(self.toPlainText())
                    self.editor_init = True
                    self.text_changed()
                    if update:
                        self.update_state(self.current_file)
            except OSError:
                sys.stderr.write('Could not save IFM file: \'' + str(self.current_file) + '\'\n')
                traceback.print_exc(file=sys.stderr)
                QMessageBox.critical(self, _('Save'), _(
                    'An error occured while writing the IFM file!\n'
                    'See console output for details.'), QMessageBox.Ok)

    @pyqtSlot()
    def save_file_as(self):
        filename, ignore = QFileDialog.getSaveFileName(self.main_window, _('Save as'), '',
                                                       options=QFileDialog.DontUseNativeDialog,
                                                       filter='IFM files (*.ifm);;All files (*)')
        if filename:
            self.current_file = Path(filename)
            self.save_file(update=True)

    @pyqtSlot()
    def new_file(self):
        if self.abort_if_modified(_('New')):
            return

        self.editor_init = True
        self.clear()
        self.current_file = None
        self.update_state()


class MainWindow(QMainWindow):

    def __init__(self, *args):
        QMainWindow.__init__(self, *args)
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
        self.editor = Editor(self)

        # Connects
        # self.dir_button.clicked.connect(self.select_dir)
        self.new_action.triggered.connect(self.editor.new_file)
        self.open_action.triggered.connect(self.editor.open_file)
        self.save_action.triggered.connect(self.editor.save_file)
        self.saveas_action.triggered.connect(self.editor.save_file_as)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.clear_recent_files_action.triggered.connect(self.editor.clear_recent_files)
        self.exit_action.triggered.connect(self.close)
        # self.show_hidden_check.stateChanged.connect(self.update_dir)
        # self.file_list.itemDoubleClicked.connect(self.show_file)

        # Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)  # left, top, right, bottom
        central_widget.setLayout(central_layout)
        central_layout.addWidget(self.splitter)
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addWidget(self.editor.cursor_position_label, 1)
        self.statusBar().addWidget(self.editor.editor_modified_label)

        self.splitter.addWidget(self.editor)

    @pyqtSlot()
    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        if self.editor.abort_if_modified(_('Exit')):
            event.ignore()
        else:
            event.accept()

        self.config.mainwindow_witdh = self.width()
        self.config.mainwindow_height = self.height()
        self.config.mainwindow_x = self.x()
        self.config.mainwindow_y = self.y()
        self.config.save()
