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

    def load(self):
        configfile = Path.home().joinpath('.qtifm')
        if configfile.exists():
            strfile = str(configfile)
            try:
                with open(strfile) as json_data_file:
                    self.__parsedata(json.load(json_data_file))

            except Exception:
                sys.stderr.write('Could not read config file: \'' + strfile + '\'\n')
                traceback.print_exc(file=sys.stderr)

    def __parsedata(self, data):
        mainwin = data.get('mainwindow', None)
        if mainwin is not None:
            self.mainwindow_witdh = mainwin.get('witdh', self.mainwindow_witdh)
            self.mainwindow_height = mainwin.get('height', self.mainwindow_height)
            self.mainwindow_x = mainwin.get('x', self.mainwindow_x)
            self.mainwindow_y = mainwin.get('y', self.mainwindow_y)

    def save(self):
        mainwin = {
            'witdh': self.mainwindow_witdh,
            'height': self.mainwindow_height,
            'x': self.mainwindow_x,
            'y': self.mainwindow_y,
        }

        data = {
            'mainwindow': mainwin,
        }

        configfile = Path.home().joinpath('.qtifm')
        strfile = str(configfile)
        with open(strfile, 'w') as outfile:
            json.dump(data, outfile, indent=4)
