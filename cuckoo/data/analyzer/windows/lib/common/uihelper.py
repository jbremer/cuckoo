# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission

import ctypes
import ctypes.wintypes
import logging
import os
import random
import subprocess
import time

from lib.common.defines import (
    USER32, KERNEL32, WM_CLOSE, WM_GETTEXT, WM_GETTEXTLENGTH, BM_CLICK,
    WM_LBUTTONDOWN, WM_LBUTTONUP, SW_RESTORE, SW_MAXIMIZE, SW_MINIMIZE,
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, VirtualKeys, POINT, RECT,
    MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, MOUSEEVENTF_WHEEL,
    EnumWindowsProc
)
from lib.common.rand import chance

log = logging.getLogger(__name__)

class Window(object):
    """Wrapper around Windows window handles (hwnd)"""

    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.classname = None
        self.title = None
        self.buttons = {}
        self.children = []
        self.children_classes = {}

    def get_classname(self, hwnd=None):
        lookup_hwnd = hwnd if hwnd else self.hwnd
        if not hwnd and self.classname:
            return self.classname

        namebuff = ctypes.create_unicode_buffer(1025)
        USER32.GetClassNameW(lookup_hwnd, namebuff, 1024)
        self.classname = namebuff.value

        return self.classname

    def get_windowtitle(self, hwnd=None):
        lookup_hwnd = hwnd if hwnd else self.hwnd
        if not hwnd and self.title:
            return self.title

        txt_len = USER32.GetWindowTextLengthW(lookup_hwnd) + 1
        titlebuff = ctypes.create_unicode_buffer(txt_len)
        USER32.GetWindowTextW(lookup_hwnd, titlebuff, txt_len)
        self.title = titlebuff.value.lower()

        return self.title

    def get_buttontitle(self, hwnd=None):
        lookup_hwnd = hwnd if hwnd else self.hwnd
        txt_len = USER32.SendMessageW(lookup_hwnd, WM_GETTEXTLENGTH, 0, 0) + 1
        titlebuff = ctypes.create_unicode_buffer(txt_len)
        USER32.SendMessageW(lookup_hwnd, WM_GETTEXT, txt_len, titlebuff)

        return titlebuff.value.replace("&", "").lower()

    def click_button(self, name):
        hwnd = None
        for btn in name.split(","):
            hwnd = self.buttons.get(btn)
            if hwnd:
                name = btn
                break

        if not hwnd:
            log.warning(
                "Button '%s' not present in window '%s'",
                name, self.get_windowtitle()
            )
            return

        log.info(
            "Clicking button '%s' in window '%s'",
            name, self.get_windowtitle()
        )
        KERNEL32.Sleep(1100)
        USER32.SetForegroundWindow(hwnd)
        USER32.PostMessageW(hwnd, BM_CLICK, 0, 0)
        KERNEL32.Sleep(1000)

    def close_window(self):
        log.info(
            "Closing window class: '%s', name: '%s'",
            self.get_classname(), self.get_windowtitle()
        )
        USER32.SendNotifyMessageW(self.hwnd, WM_CLOSE, 0, 0)
        KERNEL32.Sleep(1000)

    def is_visible(self):
        return USER32.IsWindowVisible(self.hwnd)

    def send_mouseclick(self):
        USER32.SendMessageW(self.hwnd, WM_LBUTTONDOWN, 0, 0)
        USER32.SendMessageW(self.hwnd, WM_LBUTTONUP, 0, 0)
        KERNEL32.Sleep(100)

    def get_window_rect(self):
        rect = RECT()
        USER32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        return rect

    def get_center_coords(self):
        rect = self.get_window_rect()
        x = (rect.left + rect.right) / 2
        y = (rect.top + rect.bottom) / 2
        return x, y

    def set_foreground(self):
        USER32.SetForegroundWindow(self.hwnd)

    def set_focus(self):
        USER32.SetFocus(self.hwnd)

    def set_restored(self):
        USER32.ShowWindow(self.hwnd, SW_RESTORE)

    def set_maximized(self):
        USER32.ShowWindow(self.hwnd, SW_MAXIMIZE)

    def set_minimized(self):
        USER32.ShowWindow(self.hwnd, SW_MINIMIZE)

    def is_minimized(self):
        return USER32.IsIconic(self.hwnd)

class Autotyper(object):
    """Used to generate random text and press keys"""
    vowels = ["a", "e", "i", "o", "u"]
    consonants = [
        "b", "c", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "q",
        "r", "s", "t", "v", "w", "x", "y", "z"
    ]

    def __init__(self, window, changefocus=True):
        random.shuffle(self.vowels)
        random.shuffle(self.consonants)
        self.window = window
        self.changefocus = changefocus

    def press_key(self, key, shift=False):
        """Press and release the given key. Shift is pressed if shift True"""
        if shift:
            USER32.keybd_event(VirtualKeys.VK_SHIFT, 0, 0, 0)

        USER32.keybd_event(key, 0, 0, 0)
        USER32.keybd_event(key, 0, 2, 0)

        if shift:
            USER32.keybd_event(VirtualKeys.VK_SHIFT, 0, 2, 0)
        KERNEL32.Sleep(random.randint(50, 250))

    def type_text(self, text):
        """Only supported characters are a-z 0-9,. and space.
        Returns the amount of typed keys"""
        count = 0
        for char in text:
            key_code = VirtualKeys.key_mappings.get(char.lower())
            if key_code:
                self.press_key(key_code, shift=char.isupper())
                count += 1
        return count

    def type_word(self, length, capitalize=False):
        """Generate a sequence of characters that resembles a word. Returns
        the typed word."""
        num_vowels = length / 3 or 1
        first_char = True
        word = ""

        if not USER32.IsWindow(self.window.hwnd):
            log.warning("Cannot type to window, window does not exist anymore")
            return word

        if self.changefocus:
            if self.window.is_minimized():
                self.window.set_restored()

            self.window.set_foreground()
            self.window.set_focus()

        for char in range(length):
            capitalize = capitalize and first_char
            leftover = length - char

            # The chance that word starts with a vowel is about 50%
            if first_char:
                if chance(50):
                    letter = random.choice(self.vowels)
                    num_vowels -= 1
                else:
                    letter = random.choice(self.consonants)
                first_char = False

            else:
                if leftover == num_vowels or chance(25):
                    letter = random.choice(self.vowels)
                    num_vowels -= 1
                else:
                    letter = random.choice(self.consonants)

            key_code = VirtualKeys.key_mappings.get(letter)
            if key_code:
                word += letter
                self.press_key(key_code, shift=capitalize)

        return word

    def type_sentence(self):
        firstword = True
        for c in range(random.randint(5, 10)):
            if not firstword:
                self.press_key(VirtualKeys.VK_SPACE)
            word_length = random.randint(2, 14)
            self.type_word(word_length, capitalize=firstword)

            # Simulate error in typing
            if not firstword:
                if chance(8):
                    self.backspace_chars(word_length + 1)

            # Simulate thinking while typing
            if chance(8):
                KERNEL32.Sleep(random.randint(1, 3))
            firstword = False
        self.press_key(VirtualKeys.VK_OEM_PERIOD)
        self.press_key(VirtualKeys.VK_SPACE)

    def type_paragraph(self):
        for c in range(random.randint(3, 9)):
            self.type_sentence()
        self.press_key(VirtualKeys.VK_RETURN)

    def backspace_chars(self, count):
        """Hits the backspace keys for the amount of specified times
        at the current cursor position"""
        for c in range(count):
            self.press_key(VirtualKeys.VK_BACK)

class Software(object):
    """Can be used by Action classes to create a process and control
    its window"""

    def __init__(self, name, exepath, parameters=[]):
        self.name = name
        self.exepath = exepath
        self.parameters = parameters
        self.process = None
        self.hwnd = None
        self.startupwait = 3

    def isrunning(self):
        return self.process.poll() is None

    def start(self):
        if not os.path.isfile(self.exepath):
            log.error("Executable '%s' not found", self.exepath)
            return False

        cmd = [self.exepath]
        cmd.extend(self.parameters)
        self.process = subprocess.Popen(cmd)
        time.sleep(self.startupwait)

        if self.process.pid:
            self.hwnd = HwndHelper.search_hwnd(self.process.pid)
        return True

    def wait_exit(self):
        while self.isrunning():
            time.sleep(1)

class Mouse(object):
    def __init__(self):
        self.speed = 0.03
        self.jumpsize = 0.05

    def move_to(self, x, y):
        curpos = self.get_pos()
        percent = self.jumpsize

        while percent <= 1 + self.jumpsize:
            newx = (x - curpos.x) * percent + curpos.x
            newy = (y - curpos.y) * percent + curpos.y
            percent += self.jumpsize
            USER32.SetCursorPos(int(newx), int(newy))
            if chance(33):
                time.sleep(self.speed)

    def get_pos(self):
        curpos = POINT()
        USER32.GetCursorPos(ctypes.byref(curpos))
        return curpos

    def leftclick(self):
        USER32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        KERNEL32.Sleep(50)
        USER32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def rightclick(self):
        USER32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        KERNEL32.Sleep(50)
        USER32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def scroll(self, pixelamount):
        USER32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, pixelamount, 0)
        KERNEL32.Sleep(50)

class HwndHelper(object):
    """Set of tools to help finding and using hwnds"""
    tmp_hwnd = {}
    tmp_window = None

    @staticmethod
    def _gethwnd(hwnd, pid):
        if USER32.IsWindowVisible(hwnd):
            window_pid = ctypes.wintypes.DWORD()
            USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value == pid.contents.value:
                HwndHelper.tmp_hwnd[pid.contents.value] = hwnd
        return True

    @staticmethod
    def _cb_enum_child_windows(hwnd, lParam):
        child_element = Window(hwnd)
        classname = child_element.get_classname()

        if classname == "Button":
            name = child_element.get_buttontitle()
            HwndHelper.tmp_window.buttons[name] = hwnd
        HwndHelper.tmp_window.children.append(hwnd)

        child_classes = HwndHelper.tmp_window.children_classes
        if classname in child_classes:
            child_classes[classname].append(hwnd)
        else:
            child_classes[classname] = [hwnd]

        return True

    @staticmethod
    def search_hwnd(pid):
        """Find a window handle (HWND) for a given pid"""
        ret = None
        USER32.EnumWindows(EnumWindowsProc(
            HwndHelper._gethwnd), ctypes.byref(ctypes.c_int(pid))
        )
        if HwndHelper.tmp_hwnd.get(pid):
            ret = HwndHelper.tmp_hwnd[pid]
            del HwndHelper.tmp_hwnd[pid]

        return ret

    @staticmethod
    def find_children(window):
        """Find all children hwnds for the given window object. Updates
        the given object"""
        HwndHelper.tmp_window = window
        USER32.EnumChildWindows(
            window.hwnd, EnumWindowsProc(HwndHelper._cb_enum_child_windows), 0
        )
        HwndHelper.tmp_window = None
