# Copyright (C) 2012-2013 Claudio Guarnieri.
# Copyright (C) 2014-2017 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import ctypes
import difflib
import json
import logging
import os
import random
import subprocess
import threading
import time

from ctypes import wintypes

from lib.common.abstracts import Auxiliary, Action
from lib.common.defines import (
    USER32, KERNEL32, WM_CLOSE, WM_GETTEXT, WM_GETTEXTLENGTH, BM_CLICK,
    WM_LBUTTONDOWN, WM_LBUTTONUP, SW_RESTORE, SW_MAXIMIZE, SW_MINIMIZE,
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, VirtualKeys, POINT, _RECT,
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
        rect = _RECT()
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

    tmp_hwnd = None

    def __init__(self, name, exepath, parameters=[]):
        self.name = name
        self.exepath = exepath
        self.parameters = parameters
        self.process = None
        self.hwnd = None
        self.startupwait = 3

    @staticmethod
    def gethwnd(hwnd, pid):
        if USER32.IsWindowVisible(hwnd):
            window_pid = wintypes.DWORD()
            USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value == pid.contents.value:
                Software.tmp_hwnd = hwnd
        return True

    def search_hwnd(self):
        USER32.EnumWindows(EnumWindowsProc(
            Software.gethwnd), ctypes.byref(ctypes.c_int(self.process.pid))
        )
        if Software.tmp_hwnd:
            self.hwnd = Software.tmp_hwnd
            Software.tmp_hwnd = None

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
            self.search_hwnd()
        return True

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

def handle_save_as(window):
    """Used to handle a 'Save as' Window. It inputs a directory,
     filename, and hits save"""
    log.info("Custom action: handling save as")

    for toolbarw32 in window.children_classes["ToolbarWindow32"]:
        child_w = Window(toolbarw32)
        if not child_w.is_visible():
            continue

        if child_w.get_windowtitle().startswith("address"):
            child_w.set_focus()
            child_w.send_mouseclick()
            typer = Autotyper(child_w, changefocus=False)
            typer.type_text("desktop")
            KERNEL32.Sleep(200)
            typer.press_key(VirtualKeys.VK_RETURN)
            KERNEL32.Sleep(500)
            break

    for editcontrol in window.children_classes["Edit"]:
        child_w = Window(editcontrol)
        if not child_w.is_visible():
            continue

        typer = Autotyper(child_w)
        name = typer.type_word(12)
        log.info(
            "Saving file for window '%s' under name '%s'",
            window.get_windowtitle(), name
        )
    KERNEL32.Sleep(500)
    window.click_button("save,opslaan")

class WindowHandler(Action):
    """Enumerates all visible windows and for each creates a Window
    object holding all child HWNDs. These Window objects are passed
    to a rule handler. Create rules to handle a Window object. If
    no rule exists, the default button clicker handler will be called"""

    name = "click_buttons"
    current = None
    ignore_hwnds = []
    action_count = 0
    alwaysrun = True

    # Numbers are the IDs for a rule. A rule is triggered by finding a window
    # with a specific title. Possible actions are: custom, close, and button
    rules = {
        1: {
            "action": "custom",
            "value": handle_save_as,
            "triggers": [
                "opslaan als",
                "save as"
            ]
        },
        2: {
            "action": "close",
            "triggers": [
                "activation wizard",
                "adobe product improvement program"
            ]
        },
        3: {
            "action": "button",
            "value": "yes",
            "triggers": [
                "confirm save as"
            ]
        }
    }

    # Buttons that have this words in them will be clicked
    # the numbers are a priority. If a window with more than one buttons
    # is found, it will pick the highest priority button to click.
    clickables = {
        1: [
            "yes", "oui",
            "ok",
            "i accept",
            "next", "suivant",
            "new", "nouveau",
            "install", "installer",
            "file", "fichier",
            "i agree", "accepte",
            "enable", "activer", "accord", "valider",
            "don't send", "ne pas envoyer",
            "don't save",
            "continue", "continuer",
            "personal", "personnel",
            "scan", "scanner",
            "unzip", "dezip",
            "open", "ouvrir",
            "close the program",
            "execute", "executer",
            "launch", "lancer",
            "save", "sauvegarder",
            "download", "load", "charger",
            "end", "fin", "terminer"
            "later",
            "finish",
            "end",
            "allow access",
            "remind me later",
        ],
        2: ["run", "marrer", "cuter"]
    }

    # If a buttons contains an entry in this list, it is not clicked.
    never_click = [
        "don't run",
        "i do not accept"
    ]

    def run(self):
        run = True
        while run:
            USER32.EnumWindows(
                EnumWindowsProc(WindowHandler.cb_enum_main_windows), 0
            )

            if WindowHandler.action_count < 1:
                WindowHandler.ignore_hwnds = []
                run = False

            WindowHandler.action_count = 0

    @staticmethod
    def cb_enum_main_windows(hwnd, lParam):
        current_window = Window(hwnd)
        if current_window.is_visible():
            WindowHandler.current = current_window
            USER32.EnumChildWindows(
                hwnd, EnumWindowsProc(WindowHandler.cb_enum_child_windows), 0
            )
            WindowHandler.handle_rules(WindowHandler.current)

        return True

    @staticmethod
    def cb_enum_child_windows(hwnd, lParam):
        child_element = Window(hwnd)
        classname = child_element.get_classname()

        if classname == "Button":
            name = child_element.get_buttontitle()
            WindowHandler.current.buttons[name] = hwnd
        WindowHandler.current.children.append(hwnd)

        child_classes = WindowHandler.current.children_classes
        if classname in child_classes:
            child_classes[classname].append(hwnd)
        else:
            child_classes[classname] = [hwnd]

        return True

    @staticmethod
    def best_match(needle, haystack):
        match = None
        for btn in haystack:
            if btn in needle:
                if not match:
                    match = btn
                if match and len(match) < len(btn):
                    match = btn
        return match

    @staticmethod
    def handle_clickables(window):
        buttons = window.buttons.keys()
        priorities = WindowHandler.clickables.keys()
        priorities.sort()
        click_button = None
        for prio in priorities:
            for wb in buttons:
                ignore_btn = False
                for ignore in WindowHandler.never_click:
                    if ignore in wb:
                        ignore_btn = True
                if ignore_btn:
                    break

                match = WindowHandler.best_match(
                    wb, WindowHandler.clickables[prio]
                )

                if match:
                    click_button = wb
                    break

        if click_button:
            btn_hwnd = window.buttons.get(click_button)
            if USER32.IsWindowVisible(btn_hwnd):
                window.click_button(click_button)
                return True

    @staticmethod
    def handle_rules(window):
        """Searches for a matching rule for the given window, uses
        the handle_clickables method as default if no rule exists"""

        # Only search for rules if no actions for this hwnd were performed
        # in a previous run.
        hwnd_addr = ctypes.addressof(window.hwnd.contents)
        if hwnd_addr in WindowHandler.ignore_hwnds:
            return

        triggers = {}
        matched_rule = {}
        window_title = window.get_windowtitle()

        # Search all rules for triggers
        for ruleid, rule in WindowHandler.rules.iteritems():
            match = difflib.get_close_matches(
                window_title, rule.get("triggers", []), 1
            )
            if match:
                matched_rule = ruleid
                triggers[match[0]] = ruleid

        # If multiple rules with the same trigger exist, find the closest
        # matching trigger.
        if len(triggers.keys()) > 1:
            match = difflib.get_close_matches(
                window_title, triggers.keys(), 1
            )
            matched_rule = triggers.get(match[0])

        if matched_rule:
            log.debug(
                "Window title '%s' matched rule %s",
                window_title, matched_rule
            )
            matched_rule = WindowHandler.rules.get(matched_rule)

        action = matched_rule.get("action")
        if action == "close":
            window.close_window()
            WindowHandler.action_count += 1
        elif action == "custom":
            handler = matched_rule.get("value")
            handler(window)
            WindowHandler.action_count += 1
        elif action == "button":
            button = matched_rule.get("value")
            window.click_button(button)
            WindowHandler.action_count += 1
        elif WindowHandler.handle_clickables(window):
                WindowHandler.action_count += 1

        # If an action is performed for a HWND, it is ignored next run.
        # This is done so that multiple actions can be done in a row, without
        # constantly triggering the same rule for the same window.
        # EG: Close->Save->Save as->Enter
        WindowHandler.ignore_hwnds.append(hwnd_addr)
        KERNEL32.Sleep(100)

class ClickMouse(Action):
    """Clicks the mouse at the current position. Only clicks if the
    window at the cursor position is not of any of the ignored classes.
    This is an attempt at preventing it from clicking most unwanted clickable
    items.
    """

    name = "click_mouse"
    alwaysrun = True
    ignore_classes = [
        "Button", "Edit", "NetUIHWND", "ToolbarWindow32", "SysTreeView32",
        "#32768", "#32770", "Start", "MSTaskListWClass", "DirectUIHWND",
        "SysTabControl32", "ComboBox", "ScrollBar", "msctls_trackbar32",
        "ComboLBox", "TrayClockWClass", "ConsoleWindowClass"
    ]

    def init(self):
        self.mouse = Mouse()

    def run(self):
        curpos = self.mouse.get_pos()
        hwnd = USER32.WindowFromPoint(curpos)

        if hwnd and Window(hwnd).get_classname() in self.ignore_classes:
            return

        if hwnd:
            chwnd = USER32.ChildWindowFromPoint(hwnd, curpos)
            if chwnd:
                if Window(chwnd).get_classname() in self.ignore_classes:
                    return

        self.mouse.leftclick()

class WordProcessor(Action):
    """Opens a word processor (Wordpad by default), and when the action
    is running, maximizes the window and writing sentences to form paragraphs
    of fake text."""

    name = "wordprocessor"

    software_params = {
        "wordpad": {
            "exepath": "C:\\Program Files\\Windows NT\\Accessories\\wordpad.exe"
        }
    }

    def init(self):
        self.exepath = self.options.get("wordprocessor.exepath")
        self.params = self.options.get("wordprocessor.params", [])

        if not self.exepath:
            self.processor = self.options.get("wordprocessor.name")
            choice = self.software_params.get(self.processor)
            if not choice:
                choice = self.software_params.get("wordpad")
                self.processor = "wordpad"
                self.params = choice.get("params", [])
                self.exepath = choice.get("exepath")
            else:
                if not self.params:
                    self.params = choice.get("params", [])
                self.exepath = choice.get("exepath")
        else:
            self.processor = "custom"

        self.software = Software(self.processor, self.exepath, self.params)
        self.software.startupwait = 4
        if not self.software.start():
            return
        if not self.software.isrunning():
            return False

        self.window = Window(self.software.hwnd)
        self.typer = Autotyper(self.window)
        self.sentences = random.randint(3, 9)
        return True

    def calculate_runs(self, duration):
        """
        @param: duration: total runtime of this module in seconds
        """
        # Runs is duration / 5 because autotyping a sentence takes about 5
        # seconds.
        self.runs = duration / 5

    def run(self):
        if not self.software.hwnd or not self.software.isrunning():
            return False

        self.window.set_maximized()
        self.window.set_focus()
        self.typer.press_key(VirtualKeys.VK_END)

        if self.sentences < 1:
            self.typer.press_key(VirtualKeys.VK_RETURN)
            self.sentences = random.randint(3, 9)

        self.typer.type_sentence()
        self.sentences -= 1

    def action_end(self):
        if self.software.hwnd and self.software.isrunning():
            if not self.window.is_minimized():
                self.window.set_minimized()

class UseCalculator(Action):
    """Opens the calculator and uses it to add some numbers"""

    name = "usecalculator"

    def init(self):
        self.software = Software(
            "calculator", "C:\\Windows\\System32\\calc.exe"
        )
        if not self.software.start():
            return
        self.window = Window(self.software.hwnd)
        self.typer = Autotyper(self.window)

    def calculate_runs(self, duration):
        self.runs = 1

    def run(self):
        if not self.software.hwnd or not self.software.isrunning():
            return False

        amount = random.randint(2, 7)
        for x in range(amount):
            self.window.set_restored()
            self.window.set_foreground()
            self.window.set_focus()
            number = str(random.randint(110, 35500))
            self.typer.type_text(number)
            KERNEL32.Sleep(500)
            self.typer.press_key(VirtualKeys.VK_ADD)
            KERNEL32.Sleep(1000)
        self.typer.press_key(VirtualKeys.VK_RETURN)

    def action_end(self):
        time.sleep(3)
        self.window.set_minimized()

class BrowseWebsite(Action):
    """Opens the configured (data field) website in the schedule.json in
    Internet Explorer and scrolls a through the opened page. Scrolls back up
    when the action ends."""

    name = "browsewebsite"

    def init(self):
        self.software = Software(
            "iexplorer",
            "C:\\Program Files\\Internet Explorer\\iexplore.exe",
            [self.config]
        )
        self.software.start()
        self.window = Window(self.software.hwnd)
        self.typer = Autotyper(self.window)
        self.mouse = Mouse()

    def calculate_runs(self, duration):
        self.runs = 10

    def run(self):
        if not self.software.hwnd or not self.software.isrunning():
            return False

        self.window.set_maximized()
        self.window.set_focus()

        time.sleep(5)
        self.mouse.scroll(-30)
        time.sleep(2)

    def action_end(self):
        if USER32.IsIconic(self.software.hwnd):
            self.window.set_maximized()
            self.window.set_focus()

        for x in range(5):
            self.typer.press_key(VirtualKeys.VK_PRIOR)
        self.window.set_minimized()

class DoNothing(Action):
    """Does.. nothing. Waits"""

    name = "donothing"

    def calculate_runs(self, duration):
        self.runs = duration / 5

    def run(self):
        time.sleep(5)

class MoveMouse(Action):
    """Moves the mouse over the screen in random lines. The mouse is only
    moved in the screen resolution - 'reduceby' percent. This is to
    prevent it from landing on office ribbons, start button etc."""

    name = "move_mouse"
    alwaysrun = True
    reduceby = 0.15

    def init(self):
        self.x = USER32.GetSystemMetrics(0)
        self.y = USER32.GetSystemMetrics(1)
        self.mouse = Mouse()

    def run(self):
        startx = int(self.x * self.reduceby)
        endx = int(self.x - startx)
        starty = int(self.y * self.reduceby)
        endy = int(self.y - starty)
        newx = random.randint(startx, endx)
        newy = random.randint(starty, endy)

        self.mouse.move_to(newx, newy)

class Human(threading.Thread, Auxiliary):
    """The human module simulates human behavior and automates the clicking
    of buttons etc that need to be clicked.

    2 types of actions are performed: small and big. Small actions have
    their alwaysrun attribute set to True and are always executed, unless
    disabled.

    Big actions are only executed if they are configured in a named schedule
    in the humanschedule.json file. This named schedule can be selected.

    Big actions can be used to simulate behavior like using a word processor,
    typing text, visiting websites etc. In general to simulate behavior on
    longer analyses.

    To configure what buttons, windows etc need to be handled, see the
    WindowHandler class.
    """

    modules = [
        UseCalculator, WordProcessor, DoNothing, WindowHandler, MoveMouse,
        BrowseWebsite, ClickMouse
    ]

    def __init__(self, options, analyzer=None):
        threading.Thread.__init__(self)
        Auxiliary.__init__(self, options, analyzer)
        self.actions = []
        self.enabled_modules = {}
        self.always_run = []
        self.do_run = True

    def init(self):
        """Creates an instance for each available action. Adds it to
        the enabled list of actions of the action was not disabled by options
        """
        for entry in self.modules:
            module = entry()
            module.set_options(self.options)
            if not module.is_enabled():
                continue

            if module.alwaysrun:
                self.always_run.append(module)
            else:
                self.enabled_modules[module.name] = module

    def _random_choice(self, seq):
        n = random.random()
        for choice in seq:
            if n < choice.get("chance"):
                return choice
            else:
                n -= choice.get("chance", 0.1)

    def calculate_schedule(self, name):
        """Retrieves the given schedule name from the humanschedule.json file.
        It then uses the settings in this schedule to create a set of 'big'
        actions to fill the total time specified in totaltime.

        EG: Do nothing for X mins-> Use word for 10 min -> browse site X for
        x min etc.
        """
        totaltime = 28800
        schedule_path = os.path.join("files", "humanschedule.json")

        if not os.path.isfile(schedule_path):
            log.error("Human schedule file '%s' not found", schedule_path)
            return

        schedule = json.loads(open(schedule_path, "rb").read())
        schedule = schedule.get(name)
        if not schedule:
            log.error("Human schedule '%s' does not exist.", name)
            return

        productivity = schedule.get("productivity", 0.5)
        recreation = schedule.get("recreation", [])
        tasks = schedule.get("tasks", [])

        while totaltime > 1:
            if chance(productivity * 100):
                task = self._random_choice(tasks)
            else:
                task = self._random_choice(recreation)

            if not task or not task["module"] in self.enabled_modules:
                continue

            duration = random.randint(
                task.get("min", 1) * 60, task.get("max", 2) * 60
            )
            data = task.get("data")
            action = self.enabled_modules.get(task["module"])
            self.actions.append((duration, data, action))
            totaltime -= duration

    def run_small_actions(self):
        for small_action in self.always_run:
            if not small_action.initialized:
                small_action.init()
                small_action.initialized = True
            small_action.run()

    def stop(self):
        self.do_run = False

    def run(self):
        duration = data = action = None

        if not int(self.options.get("human", 1)):
            self.stop()

        while self.do_run:
            self.run_small_actions()
            if not self.actions:
                schedule_name = self.options.get("human.schedule")
                if schedule_name:
                    self.calculate_schedule(schedule_name)
                time.sleep(1)
                continue

            if not action:
                duration, data, action = self.actions.pop(0)
            if not action.initialized:
                action.set_config(data)
                action.init()
                action.initialized = True
            if not action.active:
                action.calculate_runs(duration)
                action.active = True
            if action.runs:
                action.run()
                action.runs -= 1
            else:
                action.action_end()
                action.active = False
                action = None
            time.sleep(1)
