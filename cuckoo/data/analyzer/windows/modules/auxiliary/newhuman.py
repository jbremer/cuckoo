import ctypes
import time
import random
import difflib
import subprocess
import os
import json

from ctypes import wintypes

USER32 = ctypes.windll.user32
KERNEL32 = ctypes.windll.kernel32
EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
)

WL_LBUTTONDOWN = 0x0201
WL_LBUTTONUP = 0x0202
WM_GETTEXTLENGTH = 0x000E
WM_GETTEXT = 0x000D
WM_CLOSE = 0x0010
WM_SETFOCUS = 0x0007
BM_CLICK = 0x000000F5
SW_RESTORE = 6
SW_MAXIMIZE = 3
SW_MINIMIZE = 6

KEY_0 = 0x30
KEY_1 = 0x31
KEY_2 = 0x32
KEY_3 = 0x33
KEY_4 = 0x34
KEY_5 = 0x35
KEY_6 = 0x36
KEY_7 = 0x37
KEY_8 = 0x38
KEY_9 = 0x39
KEY_A = 0x41
KEY_B = 0x42
KEY_C = 0x43
KEY_D = 0x44
KEY_E = 0x45
KEY_F = 0x46
KEY_G = 0x47
KEY_H = 0x48
KEY_I = 0x49
KEY_J = 0x4A
KEY_K = 0x4B
KEY_L = 0x4C
KEY_M = 0x4D
KEY_N = 0x4E
KEY_O = 0x4F
KEY_P = 0x50
KEY_Q = 0x51
KEY_R = 0x52
KEY_S = 0x53
KEY_T = 0x54
KEY_U = 0x55
KEY_V = 0x56
KEY_W = 0x57
KEY_X = 0x58
KEY_Y = 0x59
KEY_Z = 0x5A
KEY_SPACE = 0x20
KEY_ENTER = 0x0D
KEY_PERIOD = 0xBE
KEY_BACKSPACE = 0x08
KEY_SHIFT = 0x10
KEY_COMMA = 0xBC
KEY_SLASHFORWARD = 0xBF
KEY_PLUS = 0x6B

hallo = 34
key_mappings = {
    "a": KEY_A,
    "b": KEY_B,
    "c": KEY_C,
    "d": KEY_D,
    "e": KEY_E,
    "f": KEY_F,
    "g": KEY_G,
    "h": KEY_H,
    "i": KEY_I,
    "j": KEY_J,
    "k": KEY_K,
    "l": KEY_L,
    "m": KEY_M,
    "n": KEY_N,
    "o": KEY_O,
    "p": KEY_P,
    "q": KEY_Q,
    "r": KEY_R,
    "s": KEY_S,
    "t": KEY_T,
    "u": KEY_U,
    "v": KEY_V,
    "w": KEY_W,
    "x": KEY_X,
    "y": KEY_Y,
    "z": KEY_Z,
    "0": KEY_0,
    "9": KEY_9,
    "8": KEY_8,
    "7": KEY_7,
    "6": KEY_6,
    "5": KEY_5,
    "4": KEY_4,
    "3": KEY_3,
    "2": KEY_2,
    "1": KEY_1,
    ".": KEY_PERIOD,
    ",": KEY_COMMA,
    " ": KEY_SPACE,
    "/": KEY_SLASHFORWARD,
    "+": KEY_PLUS
}


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_ulong),
        ("y", ctypes.c_ulong)
    ]

class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_ulong),
        ("top", ctypes.c_ulong),
        ("right", ctypes.c_ulong),
        ("bottom", ctypes.c_ulong),
    ]

class Action(object):
    name = ""

    def __init__(self):
        self.active = False
        self.runs = 0
        self.enabled = False
        self.duration = 0
        self.options = {}
        self.runcount = 0
        self.initialized = False
        self.software = None

    def set_options(self, options):
        self.options = options

    def init(self):
        pass

    def run(self):
        pass

    def action_end(self):
        pass

    def start(self, duration=None):
        raise NotImplementedError

def handle_save_as(window):
    """Used to handle a 'Save as' Window. It inputs a directory,
     filename, and hits save"""
    print("Custom action: handling save as")

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
            typer.press_key(KEY_ENTER)
            KERNEL32.Sleep(500)
            break

    for editcontrol in window.children_classes["Edit"]:
        child_w = Window(editcontrol)
        if not child_w.is_visible():
            continue

        typer = Autotyper(child_w)
        name = typer.type_word(12)
        print("Saved file for window '%s' under name '%s'" % (window.get_windowtitle(), name))
    KERNEL32.Sleep(500)
    window.click_button("opslaan")

class WindowHandler(Action):
    name = "Window handler"
    current = None
    ignore_list = []
    action_count = 0
    rules = {
        "opslaan als": {"action": "custom",
                    "value": handle_save_as},
        "naamloos ": {"action": "close"},
        "confirm save as": {"action": "button",
                            "value": "yes"},
        "activation wizard": {"action": "close"}
    }

    clickables = {
        1: ["save", "ok", "opslaan"],
    }

    def start(self):
        run = True
        while run:
            print("Scanning for clickable buttons")
            USER32.EnumWindows(
                EnumWindowsProc(WindowHandler.cb_enum_main_windows), 0
            )

            if WindowHandler.action_count < 1:
                WindowHandler.ignore_list = []
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
    def handle_clickables(window):
        buttons = window.buttons.keys()
        priorities = WindowHandler.clickables.keys()
        priorities.sort()
        click_button = None
        for prio in priorities:
            for wb in buttons:
                if wb in WindowHandler.clickables[prio]:
                    click_button = wb
                    break

        if click_button:
            window.click_button(click_button)
            return True

    @staticmethod
    def handle_rules(window):
        rule = {}
        hwnd_addr = ctypes.addressof(window.hwnd.contents)
        if hwnd_addr in WindowHandler.ignore_list:
            return

        print window.get_windowtitle()
        match = difflib.get_close_matches(
            window.get_windowtitle(), WindowHandler.rules.keys(), 1
        )
        print match
        if match:
            rule = WindowHandler.rules.get(match[0])

        action = rule.get("action")
        if action == "close":
            window.close_window()
            WindowHandler.action_count += 1
        elif action == "custom":
            handler = rule.get("value")
            handler(window)
            WindowHandler.action_count += 1
        elif action == "button":
            button = rule.get("value")
            window.click_button(button)
            WindowHandler.action_count += 1
        else:
            if WindowHandler.handle_clickables(window):
                WindowHandler.action_count += 1
        WindowHandler.ignore_list.append(hwnd_addr)


def chance(percentage):
    return random.randint(1, 100) < percentage

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
        hwnd = self.buttons.get(name)
        if not hwnd:
            print("Button '%s' not present in window '%s'" % (name, self.get_windowtitle()))
            return
        print("Clicking button '%s' in window '%s'" % (name, self.get_windowtitle()))
        USER32.SetForegroundWindow(hwnd)
        USER32.PostMessageW(hwnd, BM_CLICK, 0, 0)
        KERNEL32.Sleep(1000)

    def close_window(self):
        print("Closing window class: '%s', name: '%s'" % (
            self.get_classname(), self.get_windowtitle()
        ))
        USER32.SendNotifyMessageW(self.hwnd, WM_CLOSE, 0, 0)
        KERNEL32.Sleep(1000)

    def is_visible(self):
        return USER32.IsWindowVisible(self.hwnd)

    def send_mouseclick(self):
        USER32.SendMessageW(self.hwnd, WL_LBUTTONDOWN, 0, 0)
        USER32.SendMessageW(self.hwnd, WL_LBUTTONUP, 0, 0)
        KERNEL32.Sleep(100)

    def get_window_rect(self):
        rect = _RECT()
        USER32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        return rect

    def get_center_coords(self):
        rect = self.get_window_rect()
        print rect.left, rect.right, rect.top, rect.bottom
        x = (rect.left + rect.right) / 2
        y = (rect.top + rect.bottom) / 2
        return x, y

    def set_foreground(self):
        USER32.SetForegroundWindow(self.hwnd)

    def set_focus(self):
        USER32.SetFocus(self.hwnd)

    def set_restored(self):
        USER32.ShowWindow(self.hwnd, 9)

    def set_maximized(self):
        USER32.ShowWindow(self.hwnd, 3)

    def set_minimized(self):
        USER32.ShowWindow(self.hwnd, 6)

    def is_minimized(self):
        return USER32.IsIconic(self.hwnd)

class Autotyper(object):
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
            USER32.keybd_event(KEY_SHIFT, 0, 0, 0)

        USER32.keybd_event(key, 0, 0, 0)
        USER32.keybd_event(key, 0, 2, 0)

        if shift:
            USER32.keybd_event(KEY_SHIFT, 0, 2, 0)
        KERNEL32.Sleep(random.randint(50, 250))

    def type_text(self, text):
        """Only supported characters are a-z 0-9,. and space.
        Returns the amount of typed keys"""
        count = 0
        for char in text:
            key_code = key_mappings.get(char.lower())
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
            print("Cannot type to window, window does not exist anymore")
            return word

        if self.changefocus:
            if self.window.is_minimized():
                self.window.set_restored()

            print("Setting focus back")
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

            key_code = key_mappings.get(letter)
            if key_code:
                word += letter
                self.press_key(key_code, shift=capitalize)

        return word

    def write_random(self, for_seconds=None, paragraphs=None):
        """Generate text of multiple lines and paragraphs that resembles
        real text. Acts as if a human is typing."""
        if paragraphs:
            for c in range(paragraphs):
                self.type_paragraph()
            return

        start_time = time.time()
        if for_seconds:
            runtime = time.time() - start_time
            while runtime < for_seconds:
                start = time.time()
                self.type_paragraph()
                end = time.time()
                roundtime = end - start
                runtime = end - start_time
                # The amount of time a paragraph takes differs and can cause
                # this module to run longer than intended, therefore
                # we stop generating new paragraphs if the last generated one
                # took longer than the amount of time left.
                if for_seconds - runtime <= roundtime:
                    print "Remaining time less then what it took to generate" \
                          " last paragraph."
                    break
            return

    def type_sentence(self):
        firstword = True
        for c in range(random.randint(5, 10)):
            if not firstword:
                self.press_key(KEY_SPACE)
            word_length = random.randint(2, 14)
            self.type_word(word_length, capitalize=firstword)

            # Simulate error in typing
            if not firstword:
                if chance(15):
                    self.backspace_chars(word_length + 1)

            # Simulate thinking while typing
            if chance(5):
                KERNEL32.Sleep(random.randint(1, 3))
            firstword = False
        self.press_key(KEY_PERIOD)
        self.press_key(KEY_SPACE)

    def type_paragraph(self):
        for c in range(random.randint(3, 9)):
            self.type_sentence()
        self.press_key(KEY_ENTER)

    def backspace_chars(self, count):
        """Hits the backspace keys for the amount of specified times
        at the current cursor position"""
        for c in range(count):
            self.press_key(KEY_BACKSPACE)

class Software(object):
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
        cmd = [self.exepath]
        cmd.extend(self.parameters)
        self.process = subprocess.Popen(cmd)
        time.sleep(self.startupwait)
        if self.process.pid:
            self.search_hwnd()

class Mouse(object):
    def __init__(self):
        self.speed = 0.03
        self.jumpsize = 0.05

    def move_to(self, x, y):
        curpos = POINT()
        percent = self.jumpsize
        USER32.GetCursorPos(ctypes.byref(curpos))

        while percent <= 1 + self.jumpsize:
            newx = (x - curpos.x) * percent + curpos.x
            newy = (y - curpos.y) * percent + curpos.y
            percent += self.jumpsize
            USER32.SetCursorPos(int(newx), int(newy))
            if chance(33):
                time.sleep(self.speed)

    def leftclick(self):
        USER32.mouse_event(0x0002, 0, 0, 0, 0)
        KERNEL32.Sleep(50)
        USER32.mouse_event(0x0004, 0, 0, 0, 0)

    def rightclick(self):
        USER32.mouse_event(0x0008, 0, 0, 0, 0)
        KERNEL32.Sleep(50)
        USER32.mouse_event(0x0010, 0, 0, 0, 0)

    def scroll(self, pixelamount):
        USER32.mouse_event(0x0800, 0, 0, pixelamount, 0)
        KERNEL32.Sleep(50)

class WordProcessor(Action):

    name = "wordprocessor"

    software_params = {
        "word": {
            "params": ["/w"],
            "exepath": "C:\\Program Files\\Microsoft Office 15\\root\\office15\\WINWORD.exe"
        },
        "wordpad": {
            "exepath": "C:\\Program Files\\Windows NT\\Accessories\\wordpad.exe"
        }
    }

    def init(self):
        self.exepath = self.options.get("exepath")
        self.params = self.options.get("params", [])

        if not self.exepath:
            self.processor = self.options.get("name")
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
        self.software.start()
        if not self.software.isrunning():
            return False

        self.window = Window(self.software.hwnd)
        self.typer = Autotyper(self.window)
        self.sentences = random.randint(3, 9)
        return True

    def start(self, duration):
        """
        @param: duration: total runtime of this module in seconds
        """
        # Runs is duration / 5 because autotyping a sentence takes about 5
        # seconds.
        self.runs = duration / 5

    def run(self):
        if self.runs < 1:
            return

        if not self.software.hwnd or not self.software.isrunning():
            return False
        if self.sentences < 1:
            self.typer.press_key(KEY_ENTER)
            self.typer.press_key(KEY_ENTER)
            self.sentences = random.randint(3, 9)

        self.window.set_maximized()
        self.typer.type_sentence()
        self.sentences -= 1

    def action_end(self):
        if self.software.hwnd and self.software.isrunning():
            if not self.window.is_minimized():
                self.window.set_minimized()


class UseCalculator(Action):

    name = "usecalculator"

    def init(self):
        self.software = Software(
            "calculator", "C:\\Windows\\System32\\calc.exe"
        )
        self.software.start()
        self.window = Window(self.software.hwnd)
        self.typer = Autotyper(self.window)

    def start(self, duration=None):
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
            time.sleep(2)
            self.typer.press_key(KEY_PLUS)
            time.sleep(1)
        self.typer.press_key(KEY_ENTER)

    def action_end(self):
        time.sleep(3)
        self.window.set_minimized()


class MoveMouse(Action):

    def start(self):
        orig_x = USER32.GetSystemMetrics(0)
        orig_y = USER32.GetSystemMetrics(1)

        tenpx = orig_x * 0.02
        tenpy = orig_y * 0.02

        # newx = random.randint(tenpx, orig_x - tenpx)
        # newy = random.randint(tenpy, orig_y - tenpy)
        Mouse().move_to(orig_x, orig_y)

class Human(object):

    def __init__(self):
        self.actions = []
        self.possible = {
            UseCalculator.name: UseCalculator(),
            WordProcessor.name: WordProcessor(),
            "website": "website",
            "donothing": "donothing"
        }
        self.always_run = [WindowHandler(), MoveMouse()]
        self.options = {}

    def random_choice(self, seq):
        n = random.random()
        for choice in seq:
            if n < choice.get("chance"):
                return choice
            else:
                n -= choice.get("chance", 0.1)

    def calculate_schedule(self):
        totaltime = 480
        schedule = json.loads(open("schedule.json", "rb").read())
        productivity = schedule.get("productivity", 0.5)
        recreation = schedule.get("recreation", [])
        tasks = schedule.get("tasks", [])

        while totaltime > 1:
            print productivity * 10
            if chance(productivity * 100):
                task = self.random_choice(tasks)
                print 1
            else:
                print 2
                task = self.random_choice(recreation)

            if not task or not task["module"] in self.possible:
                print 3
                continue

            duration = random.randint(task.get("min", 1), task.get("max", 2))
            data = task.get("data")
            action = self.possible.get(task["module"])
            self.actions.append((duration, data, action))
            totaltime -= duration

    def run_small_actions(self):
        for small_action in self.always_run:
            small_action.start()

    def create_schedule(self, name):
        stuff = ["usecalculator", "wordprocessor", "usecalculator"]
        for action in stuff:
            scheduled = (
                random.randint(1, 20), random.randint(5, 30), self.possible.get(action)
            )
            self.actions.append(scheduled)

        self.actions.sort(key=lambda schedule: schedule[0])

    def run(self):
        current = None
        order = duration = action = None
        run = True

        while run:

            self.run_small_actions()
            if not self.actions:
                schedule_name = self.options.get("human.schedule")
                if schedule_name:
                    self.create_schedule(schedule_name)

                print self.actions
                time.sleep(1)
                continue

            if not action:

                current = self.actions.pop(0)
                order, duration, action = current
                print self.actions

            if not action.initialized:
                action.init()
                action.initialized = True
            if not action.active:
                action.start(duration)
                action.active = True
            if action.runs:
                print action.runs
                action.run()
                action.runs -= 1
            else:
                action.action_end()
                action.active = False
                action = None
            if not self.actions:
                run = False
            time.sleep(1)

if __name__ == "__main__":

    #time.sleep(4)
    h = Human()
    h.calculate_schedule()
    print h.actions
    test = {}

    for entry in h.actions:
        duration, data, name = entry
        if name in test:
            test[name] += duration
        else:
            test[name] = duration
    print test
    #h.options = {"human.schedule": 1}
    # h.run()
    # time.sleep(4)
    # w = WindowHandler()
    # w.start()

    # s = Software(1, "C:\\Windows\\System32\\calc.exe")
    # s.startupwait = 2
    # s.start()
    #
    # w = Window(s.hwnd)
    # # i = True
    # # f = True
    # #
    # x, y = w.get_center_coords()
    # print x, y
    # m = Mouse()
    # m.move_to(x, y)
    # w.close_window()

    # m.scrollup()
    # USER32.SetCursorPos(5, 100)

    # uw = WordProcessor()
    # uw.set_options({"name": "word"})
    # uw.init()
    # while True:
    #     w.start()
    #     time.sleep(2)
    # time.sleep(2)
    # w = WordProcessor()
    # w.init()
    # w.start(10)
    # time.sleep(3)
    #
    # for x in range(20):
    #     print "bla"
    #     w.run()
    #     time.sleep(3)

