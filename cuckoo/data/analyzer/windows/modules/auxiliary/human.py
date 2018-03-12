# Copyright (C) 2012-2013 Claudio Guarnieri.
# Copyright (C) 2014-2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import ctypes
import difflib
import json
import logging
import os
import random
import threading
import time

from lib.common.abstracts import Auxiliary, Action
from lib.common.defines import (
    USER32, KERNEL32, VirtualKeys, EnumWindowsProc
)
from lib.common.rand import chance
from lib.common.uihelper import Autotyper, Mouse, HwndHelper, Window, Software

log = logging.getLogger(__name__)

def handle_save_as(window):
    """Used to handle a 'Save as' Window. It inputs a directory,
     filename, and hits save"""
    log.info("Custom action: handling save as")

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
    multi_instance = True

    def init(self):
        self.software = Software(
            "iexplorer",
            "C:\\Program Files\\Internet Explorer\\iexplore.exe",
            [self.config.get("url")]
        )
        self.software.start()
        self.window = Window(self.software.hwnd)
        self.typer = Autotyper(self.window)
        self.mouse = Mouse()

    def calculate_runs(self, duration):
        self.runs = duration / 10

    def run(self):
        if not self.software.hwnd or not self.software.isrunning():
            return False

        self.window.set_maximized()
        self.window.set_foreground()
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

class PlayMacro(Action):
    """Plays a specific macro exe"""

    name = "playmacro"
    multi_instance = True

    def calculate_runs(self, duration):
        self.runs = 1

    def run(self):
        name = self.config.get("name")
        if not name.endswith(".exe"):
            name = "%s.exe" % name

        macro_path = os.path.join("files", name)
        if not os.path.isfile(macro_path):
            log.error("Macro '%s' does not exist", name)
            return

        macro = Software("macro", macro_path)
        macro.start()

        # If it is a macro with dialog, press the play button
        if macro.hwnd:
            window = Window(macro.hwnd)
            HwndHelper.find_children(window)
            if "play" in window.buttons:
                window.click_button("play")

        macro.wait_exit()

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
        BrowseWebsite, ClickMouse, PlayMacro
    ]

    def __init__(self, options, analyzer=None):
        threading.Thread.__init__(self)
        Auxiliary.__init__(self, options, analyzer)
        self.actions = []
        self.enabled_modules = {}
        self.scheduled_modules = {}
        self.always_run = []
        self.schedule = {}
        self.do_run = True

    def init(self):
        """Creates an instance for each available action. Adds it to
        the enabled list of actions if the action was not disabled by options
        """
        for module in self.modules:
            if not module.is_enabled(self.options):
                continue

            if module.alwaysrun:
                module = module()
                module.set_options(self.options)
                self.always_run.append(module)
            else:
                self.enabled_modules[module.name] = module

        # If modules to start were passed over options,
        # add these to the queue. If not, use the schedule file.
        if not self.queue_from_options():
            schedule = self.get_schedule()
            if schedule:
                if schedule.get("sequential"):
                    self.queue_from_sequence(schedule)
                else:
                    self.calculate_queue(schedule)

    def queue_from_sequence(self, schedule):
        """Create a queue exactly as specified in the passed
        schedule. Order actions by 'order' key"""
        sequence = schedule.get("sequential", [])
        sequence = sorted(sequence, key=lambda a: a.get("order", 999))

        for action in sequence:
            if action["module"] not in self.enabled_modules:
                continue

            instance = self._get_instance(action)

            instance.schedule_count += 1
            self.actions.append(
                (action.get("duration", 1) * 60, action.get("data"), instance)
            )

    def queue_from_options(self):
        """Use options to determine which Action modules should be
        added to the queue"""
        if "human.actions" not in self.options:
            return False

        for action in self.options.get("human.actions", "").split(","):
            action = action.strip()

            if action not in self.enabled_modules:
                continue

            # Turn the options for a specific action into a dict that will be
            # passed to the action when it is about to run
            action_key = "human.%s." % action
            data = {}
            for key, value in self.options.items():
                if key.startswith(action_key):
                    data[key.replace(action_key, "")] = self.options[key]

            instance = self.enabled_modules.get(action)()
            instance.set_options(self.options)
            instance.delay = int(data.get("delay", 0))
            self.actions.append(
                (int(data.get("duration", 2)) * 60, data, instance)
            )

        if self.actions:
            return True

    def calculate_queue(self, schedule):
        """Uses the human schedule file and the timeout value to create
        a queue of actions that will be performed during the analysis"""
        totaltime = int(self.options.get(
            "human.schedule.totaltime", self.analyzer.config.timeout
        ))
        productivity = schedule.get("productivity", 0.5)
        recreation = schedule.get("recreation", [])
        tasks = schedule.get("tasks", [])

        while totaltime > 1:
            # Use productivity setting to decide of what category the next
            # action will be
            if chance(productivity * 100):
                action = self._random_choice(tasks)
            else:
                action = self._random_choice(recreation)

            if not action or not action["module"] in self.enabled_modules:
                continue

            instance = self._get_instance(action)

            duration = random.randint(
                action.get("min", 1) * 60, action.get("max", 2) * 60
            )
            totaltime -= duration

            # Do not queue this action if it has reached the max schedule
            # amount
            limit = action.get("limit")
            if limit and instance.schedule_count >= limit:
                continue

            instance.schedule_count += 1
            self.actions.append((duration, action.get("data"), instance))

    def _random_choice(self, seq):
        n = random.random()
        for choice in seq:
            if n < choice.get("chance"):
                return choice
            else:
                n -= choice.get("chance", 0.1)

    def get_schedule(self):
        """Return the current loaded schedule, or load it and return it"""
        if self.schedule:
            return self.schedule

        schedule = self.options.get("human.schedule")
        if not schedule:
            return {}

        if not schedule.endswith(".json"):
            schedule = "%s.json" % schedule

        schedule_path = os.path.join("files", schedule)
        if not os.path.isfile(schedule_path):
            log.error("Human schedule file '%s' not found", schedule_path)
            return {}

        try:
            schedule = json.loads(open(schedule_path, "rb").read())
            self.schedule = schedule
        except ValueError as e:
            log.error("Error reading human schedule: %s", e)
            return {}

        return schedule

    def _init_module(self, action):
        """Initialize the module specific in the given action dict. Returns
        the initialed module object"""
        # No instance for this module yet, create it.
        module = self.enabled_modules[action["module"]]()
        module.set_options(self.options)

        # Delay is the time in seconds of the analysis after which the action
        # is allowed to start
        module.delay = action.get("delay", 0)

        # Wait is the time in seconds the module will wait to run when it is
        # being started (Happens every time it is called)
        module.wait = action.get("wait", 0)
        name = module.name

        # If this module is of a type that allows multiple instances,
        # create a unique key using the module name and data. This way
        # the instance with the same data can be looked up again.
        if module.multi_instance:
            name = "%s%s" % (module.name, json.dumps(action.get("data", {})))

            if module.name not in self.scheduled_modules:
                self.scheduled_modules[module.name] = {}

            self.scheduled_modules[module.name][name] = module
        else:
            self.scheduled_modules[name] = module

        return module

    def _get_instance(self, action):
        """Retrieve instance info dict containing instance of module
        @param action: dict from the human schedule for an action"""
        module_class = self.enabled_modules[action["module"]]
        lookup = module_class.name
        instance = self.scheduled_modules.get(lookup)

        if not instance:
            instance = self._init_module(action)

        # If it is a multi instance, check if it exists already by looking
        # up its instance using the module name and data for this action
        elif module_class.multi_instance:
            lookup = "%s%s" % (
                module_class.name, json.dumps(action.get("data", {}))
            )
            instance = instance.get(lookup)
            if not instance:
                instance = self._init_module(action)

        return instance

    def run_small_actions(self):
        """Runs all actions added to to the 'always run' queue"""
        for small_action in self.always_run:
            if not small_action.initialized:
                small_action.init()
                small_action.initialized = True
            small_action.run()

    def stop(self):
        self.do_run = False

    def get_action(self):
        ret = (None, None, None)
        for action in self.actions:
            if action[2].delay > self.analyzer.time_counter:
                log.info(
                    "Module '%s' has delay. Not playing it yet. Delay: %s",
                    action[2].name, action[2].delay
                )
            else:
                ret = self.actions.pop(self.actions.index(action))
                break
        return ret

    def run(self):
        """Perform all small actions and queued actions from the schedule
        or ones passed as an option"""
        duration = data = action = None

        if not int(self.options.get("human", 1)):
            self.stop()

        while self.do_run:
            self.run_small_actions()

            # If the actions queue is empty, all actions were performed
            if not self.actions:
                continue

            # Get a new action from the action queue
            if not action:
                duration, data, action = self.get_action()
                if not action:
                    continue
                log.debug("Running action: %s. Data: %s", action.name, data)

            # Pass the action the data from the 'data' field in the schedule
            if not action.initialized:
                action.set_config(data)
                action.init()
                action.initialized = True
            if not action.active:
                action.calculate_runs(duration)
                action.active = True
                if action.wait:
                    time.sleep(action.wait)
            if action.runs:
                action.run()
                action.runs -= 1
            else:
                action.action_end()
                action.active = False
                action = None
            time.sleep(1)
