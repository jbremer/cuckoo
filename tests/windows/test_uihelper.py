# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import ctypes
import pytest
import subprocess
import time

from lib.common.uihelper import HwndHelper, Window

user32 = ctypes.windll.user32

class TestWithProcesses(object):
    def setup(self):
        self.procs = []

    def teardown(self):
        for p in self.procs:
            p.kill()

    def create_process(self, args):
        p = subprocess.Popen(args)
        if not p or p.pid is None:
            pytest.fail("Could not create '%s' process to start test" % args)
        self.procs.append(p)
        return p

class TestHwndHelper(TestWithProcesses):

    @pytest.mark.timeout(60)
    def test_search_hwnd(self):
        p = self.create_process("C:\\Windows\\System32\\notepad.exe")
        hwnd = None
        while hwnd is None:
            hwnd = HwndHelper.search_hwnd(p.pid)
            time.sleep(0.01)

        namebuff = ctypes.create_unicode_buffer(1025)
        user32.GetClassNameW(hwnd, namebuff, 1024)
        assert "notepad" in namebuff.value.lower()

    @pytest.mark.timeout(60)
    def test_find_children(self):
        p = self.create_process("C:\\Windows\\System32\\calc.exe")
        hwnd = None
        while hwnd is None:
            hwnd = HwndHelper.search_hwnd(p.pid)
            time.sleep(0.01)

        w = Window(hwnd)
        HwndHelper.find_children(w)
        for hwndclass in ["Button", "CalcFrame", "#32770"]:
            assert hwndclass in w.children_classes.keys()

class TestWindow(TestWithProcesses):

    def create_hwnd(self):
        p = self.create_process("C:\\Windows\\System32\\calc.exe")
        hwnd = None
        while hwnd is None:
            hwnd = HwndHelper.search_hwnd(p.pid)
            time.sleep(0.01)
        return hwnd

    @pytest.mark.timeout(60)
    def test_getwindowtitle(self):
        hwnd = self.create_hwnd()
        w = Window(hwnd)
        assert w.get_windowtitle() == "rekenmachine"

    def test_get_classname(self):
        hwnd = self.create_hwnd()
        w = Window(hwnd)
        assert w.get_classname() == "CalcFrame"
