#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# The gui
#

import constants as const
from config import Config

import gettext
import os
import subprocess
import sys
import traceback

from pathlib import Path
from PyQt5.QtGui import (QColor, QIcon, QPalette, QPixmap, QSyntaxHighlighter, QTextCursor, QTextCharFormat,
                         QTextOption, QImage, QTextDocument)
from PyQt5.QtCore import pyqtSlot, Qt,  QRegExp, pyqtSignal
from PyQt5.QtWidgets import (QAction, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                             QMainWindow, QPlainTextEdit, QPushButton, QSizePolicy,
                             QSplitter, QVBoxLayout, QWidget, QDialogButtonBox, QGridLayout, QLineEdit,
                             QMessageBox, QScrollArea, QTextEdit, QTabWidget, QSpinBox, QLayout)

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

    def __init__(self, dark_theme, parent=None):
        super(Highlighter, self).__init__(parent)

        keyword_format = QTextCharFormat()
        if dark_theme:
            keyword_format.setForeground(Qt.green)
        else:
            keyword_format.setForeground(Qt.darkGreen)
        keyword_patterns = ['\\btitle\\b', '\\bmap\\b', '\\brequire\\b']
        self.highlightingRules = [(QRegExp(pattern), keyword_format)
                                  for pattern in keyword_patterns]

        quotation_format = QTextCharFormat()
        if dark_theme:
            quotation_format.setForeground(QColor(180, 200, 255))
        else:
            quotation_format.setForeground(QColor(Qt.darkBlue))
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
    map_changed_signal = pyqtSignal(Path)
    map_cleared_signal = pyqtSignal()

    def __init__(self, mainwin, dark_theme, *args):
        QTextEdit.__init__(self, *args)

        self.main_window = mainwin
        self.config = mainwin.config
        self.setStyleSheet('font-family: "Monospace";')
        self.highlighter = Highlighter(dark_theme, self.document())
        self.setWordWrapMode(QTextOption.NoWrap)
        self.setTabStopWidth(int(self.tabStopWidth() / 2))

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

    def reset_highlighter(self, dark_theme):
        self.highlighter = Highlighter(dark_theme, self.document())

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
            self.editor_modified_label.setText(_('Modified  /'))

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
                with open(path, 'r', encoding='utf-8') as file:
                    self.editor_init = True
                    self.insertPlainText(file.read())
                    self.setFocus()
                    cursor = self.textCursor()
                    cursor.setPosition(0)
                    self.setTextCursor(cursor)
                    self.current_file = path

                self.map_changed_signal.emit(self.current_file)  # don't do this within the "with" statement

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
                'The file "') + str(path) + _('" doesn\'t exist!'),
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
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(self.toPlainText())
                    self.editor_init = True
                    self.text_changed()
                    if update:
                        self.update_state(self.current_file)

                self.map_changed_signal.emit(self.current_file)  # don't do this within the "with" statement
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
        self.map_cleared_signal.emit()


class ImageViewer(QScrollArea):

    def __init__(self, changed_signal, *args):
        QScrollArea.__init__(self, *args)

        self.changed_signal = changed_signal
        self.scale_factor = 1.0

        self.image_label = QLabel()
        self.image_label.setBackgroundRole(QPalette.Base)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setScaledContents(True)

        self.setBackgroundRole(QPalette.Dark)
        self.setWidget(self.image_label)

    def wheelEvent(self, event):

        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() < 0:
                self.scale_image(-0.1)
            else:
                self.scale_image(+0.1)
            self.changed_signal.emit()
        else:
            QScrollArea.wheelEvent(self, event)

    def load_image(self, filename):
        image = QImage(str(filename))
        if image.isNull():
            return

        self.image_label.setPixmap(QPixmap.fromImage(image))
        self.scale_factor = 1.0
        self.image_label.adjustSize()

    def normal_size(self):
        self.image_label.adjustSize()
        self.scale_factor = 1.0

    def scale_image(self, factor, absolute=False):
        test_factor = self.scale_factor + factor
        if absolute:
            test_factor = factor
        if test_factor > 3.0 or test_factor < 0.2:
            return

        self.scale_factor += factor
        if absolute:
            self.scale_factor = factor

        self.image_label.resize(self.scale_factor * self.image_label.pixmap().size())

        self.adjust_scroll_bar(self.horizontalScrollBar(), factor)
        self.adjust_scroll_bar(self.verticalScrollBar(), factor)

    def scale_image_allowed(self, factor):
        test_factor = self.scale_factor + factor
        if test_factor > 3.0 or test_factor < 0.2:
            return False
        return True

    @staticmethod
    def adjust_scroll_bar(scroll_bar, factor):
        scroll_bar.setValue(int(factor * scroll_bar.value() + ((factor - 1) * scroll_bar.pageStep() / 2)))


class MapView(QTabWidget):
    map_view_changed_signal = pyqtSignal()

    def __init__(self, mainwin, config, *args):
        QTabWidget.__init__(self, *args)

        self.setStyleSheet("QTabWidget::pane { margin: 0; }")
        self.main_window = mainwin
        self.config = config
        self.valid = False
        self.last_file = None

        self.zoom_factor_label = QLabel()
        self.zoom_factor_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))

        self.clear_maps()
        self.currentChanged.connect(self.tab_changed)

    @pyqtSlot()
    def tab_changed(self):
        self.map_view_changed_signal.emit()

    @pyqtSlot()
    def clear_maps(self):
        self.clear()
        self.valid = False
        self.display_message(self, _('Save the file to create the map images.'))
        self.map_view_changed_signal.emit()

    @pyqtSlot(Path)
    def create_maps(self, file):

        selected_index = -1
        old_viewers = []
        if self.valid and self.last_file == file:
            selected_index = self.currentIndex()
            for i in range(0, self.count()):
                old_viewers.append(self.widget(i))

        self.clear()
        self.valid = False

        base = file.parent

        # check syntax
        status, output = subprocess.getstatusoutput(self.config.map_ifm_command + ' "' + str(file) + '"')
        if status != 0:
            self.display_message(_('The syntax of the map file isn\'t correct!'), error=output)
            return

        # check maps
        self.valid = True
        sections = []

        if self.config.map_ifm_create_image_per_map:
            status, output = subprocess.getstatusoutput(self.config.map_ifm_command + ' --show=maps "' + str(file) + '"')
            if status != 0:
                self.display_message(_('The syntax of the map file isn\'t correct!'), error=output)
                return

            if output is not None and len(output) > 0:
                lines = output.split('\n')
                length = len(lines)
                if length > 1:
                    header = False
                    for i in range(0, length):
                        if header:
                            line = lines[i].split('\t')
                            if len(line) == 5:
                                sections.append([line[0], line[4]])
                        else:
                            header = lines[i].startswith('No.')

        if len(sections) > 0:
            for i in range(0, len(sections)):
                scale_factor = None
                if i < len(old_viewers):
                    scale_factor = old_viewers[i].scale_factor
                section = sections[i]
                self.create_map_section(file, base, section[0], section[1], scale_factor)
        else:
            self.create_map_section(file, base, None, _('Map'), None)

        if 0 <= selected_index < self.count():
            self.setCurrentIndex(selected_index)

        self.last_file = file
        self.map_view_changed_signal.emit()

    def create_map_section(self, file, base, section, name, scale_factor):
        # create fig files
        style = ''
        if self.config.map_ifm_helvetica_as_default:
            style = ' -S helvetica'

        if section is not None:
            fig = base.joinpath(file.stem + '_qtifm_' + section + '.fig')
        else:
            fig = base.joinpath(file.stem + '_qtifm.fig')

        if section is not None:
            cmd = self.config.map_ifm_command + style + ' -m=' + section + ' -f fig -o "' + str(fig) + '" "' + \
                  str(file) + '"'
        else:
            cmd = self.config.map_ifm_command + style + ' -m -f fig -o "' + str(fig) + '" "' + str(file) + '"'
        status, output = subprocess.getstatusoutput(cmd)
        if status != 0:
            self.valid = False
            self.display_message(_('An error occurred while running IFM to create the fig files!'), error=output)
            return

        # create png files
        magnification = 2.0
        if self.config.map_fig2dev_magnification_factor is not None \
                and 0 < self.config.map_fig2dev_magnification_factor < 10:
            magnification = float(self.config.map_fig2dev_magnification_factor + 1) / 2
            pass

        if section is not None:
            png = base.joinpath(file.stem + '_qtifm' + section + '.png')
        else:
            png = base.joinpath(file.stem + '_qtifm.png')

        status, output = subprocess.getstatusoutput(
            self.config.map_fig2dev_command + ' -L png -m ' + str(magnification) + '  -S 4 -b 5 "' + str(
                fig) + '" "' + str(png) + '"')
        if status != 0:
            self.valid = False
            self.display_message(_('An error occurred while running FIG2DEV to create the images!'), error=output)
            return

        # display images
        viewer = ImageViewer(self.map_view_changed_signal)
        viewer.load_image(png)
        self.addTab(viewer, name)

        if scale_factor is not None:
            viewer.scale_image(scale_factor, absolute=True)

    def update_zoom_factor_status(self):
        if self.valid:
            viewer = self.currentWidget()
            if viewer is not None:
                self.zoom_factor_label.setText(_('Zoom: ') + '{:.0%}'.format(viewer.scale_factor))
                return
        self.zoom_factor_label.setText(_('Zoom: -'))

    @pyqtSlot()
    def normal_size(self):
        if self.valid:
            viewer = self.currentWidget()
            if viewer is not None:
                viewer.normal_size()
                self.update_zoom_factor_status()
                self.map_view_changed_signal.emit()

    @pyqtSlot()
    def zoom_in(self):
        if self.valid:
            viewer = self.currentWidget()
            if viewer is not None:
                viewer.scale_image(+0.1)
                self.map_view_changed_signal.emit()

    @pyqtSlot()
    def zoom_out(self):
        if self.valid:
            viewer = self.currentWidget()
            if viewer is not None:
                viewer.scale_image(-0.1)
                self.map_view_changed_signal.emit()

    def zoom_in_allowed(self):
        if self.valid:
            viewer = self.currentWidget()
            if viewer is not None:
                return viewer.scale_image_allowed(+0.1)
        return False

    def zoom_out_allowed(self):
        if self.valid:
            viewer = self.currentWidget()
            if viewer is not None:
                return viewer.scale_image_allowed(-0.1)
        return False

    def display_message(self, message, error=None):

        if error is not None:
            sys.stderr.write(error)

        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        layout.addStretch(1)
        label1 = QLabel(message)
        label1.setAlignment(Qt.AlignCenter)
        layout.addWidget(label1)
        if error is not None:
            label2 = QLabel('<html><code>' + error + '</code></html>')
            label2.setAlignment(Qt.AlignCenter)
            layout.addWidget(label2)
        layout.addStretch(1)
        self.addTab(widget, _('Map'))


class DirectoryFieldButton(QPushButton):

    def __init__(self, icon, parent, ledit, dirsonly):
        QPushButton.__init__(self, icon, '', parent)
        self.line_edit = ledit
        self.directories_only = dirsonly
        self.clicked.connect(self.select_dir)

    @pyqtSlot()
    def select_dir(self):

        if self.directories_only:
            filename = QFileDialog.getExistingDirectory(self, _('Choose directory'), self.line_edit.text(),
                                                        QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog)
        else:
            filename, _ = QFileDialog.getOpenFileName(self, _('Choose file'), self.line_edit.text(),
                                                      options=QFileDialog.DontUseNativeDialog)
        if filename:
            file = Path(filename)
            if self.directories_only:
                if file.is_dir():
                    self.line_edit.setText(filename)
                    self.line_edit.setFocus()
            else:
                if file.is_file():
                    self.line_edit.setText(filename)
                    self.line_edit.setFocus()


class SettingsDialog(QDialog):

    def __init__(self, *args):
        QDialog.__init__(self, *args)
        self.setWindowTitle(_('Settings'))

        self.ifm_command_edit = self.__lineedit()
        self.fig2dev_command_edit = self.__lineedit()

        self.magnifcation_factor_edit = self.__spinbox()
        self.magnifcation_factor_edit.setRange(1, 9)
        self.magnifcation_factor_edit.setValue(1)

        self.image_per_map_check = QCheckBox(_('Create an image for each map section'))
        self.helvetica_check = QCheckBox(_('Use Helvetica as default font'))
        self.dark_theme_check = QCheckBox(_('Syntax highlighting for dark themes'))

        dlglyt = QVBoxLayout()
        dlglyt.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(dlglyt)

        grid = QGridLayout()
        dlglyt.addLayout(grid)
        grid.setSpacing(10)

        grid.addWidget(self.__label(_('ifm command:')), 0, 0)
        grid.addWidget(self.ifm_command_edit, 0, 1)
        grid.addWidget(self.__dirbutton(self.ifm_command_edit, False), 0, 2)

        grid.addWidget(self.__label(_('fig2dev command:')), 1, 0)
        grid.addWidget(self.fig2dev_command_edit, 1, 1)
        grid.addWidget(self.__dirbutton(self.fig2dev_command_edit, False), 1, 2)

        grid.addWidget(self.__label(_('Magnification factor:')), 2, 0)
        grid.addWidget(self.magnifcation_factor_edit, 2, 1, 1, 2)

        grid.addWidget(self.image_per_map_check, 3, 1, 1, 2)
        grid.addWidget(self.helvetica_check, 4, 1, 1, 2)
        grid.addWidget(self.dark_theme_check, 5, 1, 1, 2)

        dlglyt.addSpacing(10)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        dlglyt.addWidget(button_box)

    @staticmethod
    def __label(name):
        label = QLabel(name)
        label.setAlignment(Qt.AlignRight)
        return label

    @staticmethod
    def __lineedit():
        edit = QLineEdit()
        edit.setFixedWidth(400)
        return edit

    @staticmethod
    def __spinbox():
        edit = QSpinBox()
        edit.setFixedWidth(400)
        return edit

    def __dirbutton(self, ledit, dirsonly):
        button = DirectoryFieldButton(QIcon.fromTheme('folder-open'), self, ledit, dirsonly)
        return button


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
        self.settings_action = QAction(_('Settings'))

        self.find_next_action = QAction(QIcon.fromTheme('down'), _('Find Next'))
        self.find_next_action.setShortcut('F3')
        self.find_previous_action = QAction(QIcon.fromTheme('up'), _('Find Previous'))
        self.find_previous_action.setShortcut('Ctrl+F3')

        self.normal_size_action = QAction(QIcon.fromTheme('zoom-original'), _('Normal Size'))
        self.normal_size_action.setShortcut('Ctrl+0')
        self.zoom_in_action = QAction(QIcon.fromTheme('zoom-in'), _('Zoom In'))
        self.zoom_in_action.setShortcut('Ctrl++')
        self.zoom_out_action = QAction(QIcon.fromTheme('zoom-out'), _('Zoom Out'))
        self.zoom_out_action.setShortcut('Ctrl+-')

        # Menu Bar
        file_menu = self.menuBar().addMenu(_('File'))
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        self.recent_files_menu = file_menu.addMenu(_('Open recent'))
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.saveas_action)
        file_menu.addSeparator()
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        help_menu = self.menuBar().addMenu(_('Help'))
        help_menu.addAction(self.about_action)

        # Widgets
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(5)
        self.editor = Editor(self, self.config.editor_dark_theme)
        self.map_view = MapView(self, self.config)
        self.find_edit = QLineEdit()
        self.find_edit.setFixedWidth(200)

        # Tool bar
        tool_bar = self.addToolBar('Edit')
        tool_bar.setFloatable(False)
        tool_bar.setMovable(False)
        tool_bar.addAction(self.new_action)
        tool_bar.addAction(self.open_action)
        tool_bar.addAction(self.save_action)
        tool_bar.addAction(self.saveas_action)
        tool_bar.addSeparator()
        tool_bar.addWidget(QLabel(_('Find:') + ' '))
        tool_bar.addWidget(self.find_edit)
        tool_bar.addAction(self.find_next_action)
        tool_bar.addAction(self.find_previous_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.normal_size_action)
        tool_bar.addAction(self.zoom_in_action)
        tool_bar.addAction(self.zoom_out_action)

        # Connects
        self.new_action.triggered.connect(self.editor.new_file)
        self.open_action.triggered.connect(self.editor.open_file)
        self.save_action.triggered.connect(self.editor.save_file)
        self.saveas_action.triggered.connect(self.editor.save_file_as)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.clear_recent_files_action.triggered.connect(self.editor.clear_recent_files)
        self.settings_action.triggered.connect(self.show_settings)
        self.exit_action.triggered.connect(self.close)
        self.normal_size_action.triggered.connect(self.map_view.normal_size)
        self.zoom_in_action.triggered.connect(self.map_view.zoom_in)
        self.zoom_out_action.triggered.connect(self.map_view.zoom_out)
        self.find_next_action.triggered.connect(self.find_next)
        self.find_previous_action.triggered.connect(self.find_previous)

        self.editor.map_changed_signal.connect(self.map_view.create_maps)
        self.editor.map_cleared_signal.connect(self.map_view.clear_maps)

        self.map_view.map_view_changed_signal.connect(self.enable_map_actions)

        self.find_edit.textChanged.connect(self.find_edit_text_changed)
        self.find_edit.returnPressed.connect(self.find_next)

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
        self.statusBar().addWidget(self.map_view.zoom_factor_label)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.map_view)

        if len(self.config.mainwindow_splitter_sizes) > 0:
            self.splitter.setSizes(self.config.mainwindow_splitter_sizes)

        if self.config.editor_last_file is not None:
            self.editor.open_path(self.config.editor_last_file, check_modified=False)

        self.find_next_action.setEnabled(False)
        self.find_previous_action.setEnabled(False)

    @pyqtSlot()
    def enable_map_actions(self):
        self.zoom_in_action.setEnabled(self.map_view.zoom_in_allowed())
        self.zoom_out_action.setEnabled(self.map_view.zoom_out_allowed())
        self.normal_size_action.setEnabled(self.map_view.valid)
        self.map_view.update_zoom_factor_status()

    @pyqtSlot()
    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    @pyqtSlot()
    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.ifm_command_edit.setText(self.config.map_ifm_command)
        dialog.fig2dev_command_edit.setText(self.config.map_fig2dev_command)
        dialog.magnifcation_factor_edit.setValue(self.config.map_fig2dev_magnification_factor)
        dialog.dark_theme_check.setChecked(self.config.editor_dark_theme)
        dialog.helvetica_check.setChecked(self.config.map_ifm_helvetica_as_default)
        dialog.image_per_map_check.setChecked(self.config.map_ifm_create_image_per_map)
        dark_theme = self.config.editor_dark_theme

        result = dialog.exec_()
        if result == QDialog.Accepted:
            self.config.map_ifm_command = dialog.ifm_command_edit.text().strip()
            self.config.map_fig2dev_command = dialog.fig2dev_command_edit.text().strip()
            self.config.map_fig2dev_magnification_factor = dialog.magnifcation_factor_edit.value()
            self.config.editor_dark_theme = dialog.dark_theme_check.isChecked()
            self.config.map_ifm_helvetica_as_default = dialog.helvetica_check.isChecked()
            self.config.map_ifm_create_image_per_map = dialog.image_per_map_check.isChecked()

            if self.config.editor_dark_theme != dark_theme:
                self.editor.reset_highlighter(self.config.editor_dark_theme)

    @pyqtSlot()
    def find_edit_text_changed(self):
        flag = len(self.find_edit.text()) > 0
        self.find_next_action.setEnabled(flag)
        self.find_previous_action.setEnabled(flag)

    @pyqtSlot()
    def find_next(self):
        text = self.find_edit.text()
        if len(text) > 0:
            self.editor.find(text)

    @pyqtSlot()
    def find_previous(self):
        text = self.find_edit.text()
        if len(text) > 0:
            self.editor.find(text, QTextDocument.FindBackward)

    def closeEvent(self, event):
        if self.editor.abort_if_modified(_('Exit')):
            event.ignore()
        else:
            event.accept()

        self.config.mainwindow_witdh = self.width()
        self.config.mainwindow_height = self.height()
        self.config.mainwindow_x = self.x()
        self.config.mainwindow_y = self.y()

        self.config.mainwindow_splitter_sizes = []
        for i in range(0, self.splitter.count()):
            self.config.mainwindow_splitter_sizes.append(self.splitter.sizes()[i])

        self.config.editor_last_file = self.editor.current_file

        self.config.save()
