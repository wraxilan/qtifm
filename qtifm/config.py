#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# The config handling
#

import json
import platform
import subprocess
import sys
import tempfile
import traceback

from pathlib import Path


class Config:

    def __init__(self):
        self.mainwindow_witdh = 800
        self.mainwindow_height = 600
        self.mainwindow_x = 0
        self.mainwindow_y = 0
        self.mainwindow_splitter_sizes = []

        self.editor_recent_files = []
        self.editor_last_file = None
        self.editor_dark_theme = False

        self.map_ifm_command = 'ifm'
        self.map_fig2dev_command = 'fig2dev'

    def load(self):
        configfile = Path.home().joinpath('.qtifm')
        if configfile.exists():
            strfile = str(configfile)
            try:
                with open(strfile) as json_data_file:
                    self.__parsedata(json.load(json_data_file))

            except OSError:
                sys.stderr.write('Could not read config file: \'' + strfile + '\'\n')
                traceback.print_exc(file=sys.stderr)

    def __parsedata(self, data):
        mainwin = data.get('mainwindow', None)
        if mainwin is not None:
            self.mainwindow_witdh = mainwin.get('witdh', self.mainwindow_witdh)
            self.mainwindow_height = mainwin.get('height', self.mainwindow_height)
            self.mainwindow_x = mainwin.get('x', self.mainwindow_x)
            self.mainwindow_y = mainwin.get('y', self.mainwindow_y)
            self.mainwindow_splitter_sizes = mainwin.get('splitter-sizes', self.mainwindow_splitter_sizes)

        editor = data.get('editor', None)
        if editor is not None:
            str_files = editor.get('recent-files', [])
            for file in str_files:
                path = Path(file)
                if path.is_file():
                    self.editor_recent_files.append(path)
            str_file = editor.get('last-file', None)

            if str_file is not None:
                file = Path(str_file)
                if file.is_file():
                    self.editor_last_file = file

            self.editor_dark_theme = editor.get('dark-theme', self.editor_dark_theme)

        map_prop = data.get('map', None)
        if map_prop is not None:
            self.map_ifm_command = map_prop.get('ifm-command', self.map_ifm_command)
            self.map_fig2dev_command = map_prop.get('fig2dev-command', self.map_fig2dev_command)

    def save(self):
        mainwin = {
            'witdh': self.mainwindow_witdh,
            'height': self.mainwindow_height,
            'x': self.mainwindow_x,
            'y': self.mainwindow_y,
            'splitter-sizes': self.mainwindow_splitter_sizes,
        }

        str_files = []
        for f in self.editor_recent_files:
            str_files.append(str(f))
        lastfile = ''
        if self.editor_last_file is not None:
            lastfile = str(self.editor_last_file)

        editor = {
            'recent-files': str_files,
            'last-file': lastfile,
            'dark-theme': self.editor_dark_theme
        }

        map_prop = {
            'ifm-command': self.map_ifm_command,
            'fig2dev-command': self.map_fig2dev_command,
        }

        data = {
            'mainwindow': mainwin,
            'editor': editor,
            'map': map_prop,
        }

        configfile = Path.home().joinpath('.qtifm')
        strfile = str(configfile)
        with open(strfile, 'w') as outfile:
            json.dump(data, outfile, indent=4)
