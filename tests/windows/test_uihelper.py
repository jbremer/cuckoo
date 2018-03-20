# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import ctypes
import pytest
import subprocess
import time
import mock

from lib.common.uihelper import HwndHelper, Window, Software, Autotyper, Mouse

user32 = ctypes.windll.user32

class TestWithProcesses(object):
    def setup(self):
        self.procs = []

    def create_hwnd(self, args="C:\\Windows\\System32\\calc.exe"):
        p = self.create_process(args)
        hwnd = None
        while hwnd is None:
            hwnd = HwndHelper.search_hwnd(p.pid)
            time.sleep(0.01)
        return hwnd

    def teardown(self):
        for p in self.procs:
            try:
                p.kill()
            except Exception as e:
                pass

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
        assert HwndHelper.tmp_hwnd == {}

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
        assert HwndHelper.tmp_window is None

class TestWindow(TestWithProcesses):

    @pytest.mark.timeout(60)
    def test_getwindowtitle(self):
        hwnd = self.create_hwnd()
        w = Window(hwnd)
        assert w.get_windowtitle() == "calculator"

    @pytest.mark.timeout(60)
    def test_get_classname(self):
        hwnd = self.create_hwnd()
        w = Window(hwnd)
        assert w.get_classname() == "CalcFrame"

    @pytest.mark.timeout(60)
    def test_close_window(self):
        hwnd = self.create_hwnd()
        proc = self.procs[0]
        w = Window(hwnd)
        assert proc.poll() is None
        w.close_window()
        assert proc.poll() is not None

    @pytest.mark.timeout(60)
    def test_is_visibile(self):
        hwnd = self.create_hwnd()
        w = Window(hwnd)
        w.set_minimized()
        assert w.is_visible()

    @pytest.mark.timeout(60)
    def test_set_minimized(self):
        hwnd = self.create_hwnd()
        w = Window(hwnd)
        assert not user32.IsIconic(hwnd)
        w.set_minimized()
        assert user32.IsIconic(hwnd)

    @pytest.mark.timeout(60)
    def test_set_restored(self):
        hwnd = self.create_hwnd()
        w = Window(hwnd)
        user32.ShowWindow(hwnd, 6)
        assert user32.IsIconic(hwnd)
        w.set_restored()
        assert not user32.IsIconic(hwnd)

    @pytest.mark.timeout(60)
    def test_get_window_rect(self):
        hwnd = self.create_hwnd()
        w = Window(hwnd)
        r = w.get_window_rect()
        assert r.left > 0
        assert r.top > 0
        assert r.right > 0
        assert r.bottom > 0

class TestSoftware(TestWithProcesses):

    @pytest.mark.timeout(60)
    def test_isrunning(self):
        proc = self.create_process("C:\\Windows\\System32\\calc.exe")
        s = Software(
            "calculator",
            "C:\\Windows\\System32\\calc.exe"
        )
        s.process = proc
        assert s.isrunning()
        try:
            proc.kill()
            time.sleep(0.5)
        except OSError as e:
            pass
        assert not s.isrunning()

    @mock.patch("time.sleep")
    @pytest.mark.timeout(60)
    def test_wait_exit(self, ms):
        s = Software(
            "calculator",
            "C:\\Windows\\System32\\calc.exe"
        )
        s.process = mock.MagicMock()
        s.process.poll.side_effect = [None, None, 1]
        s.wait_exit()
        assert ms.call_count == 2

    @pytest.mark.timeout(60)
    def test_start(self):
        s = Software(
            "calculator",
            "C:\\Windows\\System32\\calc.exe"
        )
        s.startupwait = 1
        res = s.start()
        self.procs.append(s.process)
        assert s.hwnd is not None
        assert s.process.pid is not None
        assert Window(s.hwnd).get_windowtitle() == "calculator"

class TestAutotyper(object):

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_press_key(self, mu, mk):
        window = mock.MagicMock()
        a = Autotyper(window)
        a.press_key(0x5A)
        mu.keybd_event.assert_has_calls([
            mock.call(0x5A, 0, 0, 0), mock.call(0x5A, 0, 2, 0)
        ])

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_press_key_shift(self, mu, mk):
        window = mock.MagicMock()
        a = Autotyper(window)
        a.press_key(0x5A, shift=True)
        mu.keybd_event.assert_has_calls([
            mock.call(0x10, 0, 0, 0), mock.call(0x5A, 0, 0, 0),
            mock.call(0x5A, 0, 2, 0), mock.call(0x10, 0, 2, 0)
        ])

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_type_text(self, mu, mk):
        window = mock.MagicMock()
        keys = [0x48, 0x45, 0x4C, 0x4F, 0x20, 0x54, 0x53, 0x10]
        a = Autotyper(window)
        count = a.type_text("Hello test")
        for key in keys:
            mu.keybd_event.assert_any_call(key, 0, 0, 0)
            mu.keybd_event.assert_any_call(key, 0, 2, 0)
        assert count == 10

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_type_word(self, mu, mk):
        window = mock.MagicMock()
        a = Autotyper(window)
        a.press_key = mock.MagicMock()
        word = a.type_word(24, capitalize=True)

        assert len(word) == 24
        assert a.press_key.call_count == 24
        a.press_key.assert_any_call(mock.ANY, shift=True)
        window.set_focus.assert_called_once()

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_type_sentence(self, mu, mk):
        window = mock.MagicMock()
        a = Autotyper(window)
        a.type_word = mock.MagicMock()
        a.type_sentence()

        a.type_word.call_count >= 5
        mu.keybd_event.assert_any_call(0xBE, 0, 0, 0)
        mu.keybd_event.assert_any_call(0x20, 0, 0, 0)

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_type_paragraph(self, mu, mk):
        window = mock.MagicMock()
        a = Autotyper(window)
        a.type_sentence = mock.MagicMock()
        a.type_paragraph()

        a.type_sentence.call_count >= 3
        mu.keybd_event.assert_any_call(0x0D, 0, 0, 0)

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_backspace_chars(self, mu, mk):
        window = mock.MagicMock()
        a = Autotyper(window)
        a.type_sentence = mock.MagicMock()
        a.backspace_chars(19)

        assert mu.keybd_event.call_count == 38
        mu.keybd_event.assert_any_call(0x08, 0, 0, 0)

class TestMouse(object):

    def test_get_pos(self):
        m = Mouse()
        point = m.get_pos()
        assert point.x > 0
        assert point.y > 0

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_leftclick(self, mu, mk):
        m = Mouse()
        m.leftclick()
        mu.mouse_event.assert_has_calls([
            mock.call(0x00000002, 0, 0, 0, 0),
            mock.call(0x00000004, 0, 0, 0, 0)
        ])

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_rightclick(self, mu, mk):
        m = Mouse()
        m.rightclick()
        mu.mouse_event.assert_has_calls([
            mock.call(0x00000008, 0, 0, 0, 0),
            mock.call(0x00000010, 0, 0, 0, 0)
        ])

    @mock.patch("lib.common.uihelper.KERNEL32")
    @mock.patch("lib.common.uihelper.USER32")
    def test_scroll(self, mu, mk):
        m = Mouse()
        m.scroll(-40)
        mu.mouse_event.assert_called_once_with(0x00000800, 0, 0, -40, 0)

    def test_move_to(self):
        m = Mouse()
        pos1 = m.get_pos()
        x = int(user32.GetSystemMetrics(0) / 3)
        y = int(user32.GetSystemMetrics(1) / 3)
        m.move_to(x, y)
        pos2 = m.get_pos()

        assert pos1.x != pos2.x
        assert pos1.y != pos2.y
