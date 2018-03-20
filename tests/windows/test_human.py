# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import copy
import json
import mock

from modules.auxiliary.human import (
    Human, BrowseWebsite, DoNothing, PlayMacro, UseCalculator, WordProcessor,
    ClickMouse, MoveMouse, WindowHandler
)
from lib.common.uihelper import Autotyper, Mouse, HwndHelper, Window

class TestHuman(object):

    def test_minimal_modules(self):
        minimal = [
            BrowseWebsite, DoNothing, PlayMacro, UseCalculator, WordProcessor,
            ClickMouse, MoveMouse, WindowHandler
        ]

        for m in minimal:
            assert m in Human.modules

    def test_init_no_options(self):
        h = Human({})
        h.init()
        assert h.actions == []
        assert len(h.always_run) == 3
        assert h.enabled_modules == {
            "browsewebsite": BrowseWebsite,
            "donothing": DoNothing,
            "playmacro": PlayMacro,
            "usecalculator": UseCalculator,
            "wordprocessor": WordProcessor
        }
        small_actions = [ClickMouse, MoveMouse, WindowHandler]
        for small_action in h.always_run:
            small_actions.remove(type(small_action))
        assert small_actions == []

    def test_init_disable_small(self):
        h = Human({
            "human.click_mouse": 0,
            "human.move_mouse": 0
        })
        h.init()
        assert len(h.enabled_modules) == 5
        assert len(h.always_run) == 1
        small_actions = [ClickMouse, MoveMouse, WindowHandler]
        for small_action in h.always_run:
            small_actions.remove(type(small_action))
        assert small_actions == [ClickMouse, MoveMouse]

    def test_init_disable_nonexisting(self):
        h = Human({"human.dogessuchwow": 0})
        h.init()
        assert len(h.enabled_modules) == 5
        assert len(h.always_run) == 3
        small_actions = [ClickMouse, MoveMouse, WindowHandler]
        for small_action in h.always_run:
            small_actions.remove(type(small_action))
        assert small_actions == []

    def test_init_disable_action(self):
        h = Human({"human.usecalculator": 0})
        h.init()
        assert len(h.enabled_modules) == 4
        assert len(h.always_run) == 3
        assert h.enabled_modules == {
            "browsewebsite": BrowseWebsite,
            "donothing": DoNothing,
            "playmacro": PlayMacro,
            "wordprocessor": WordProcessor
        }

    def test_init_queue_options(self):
        h = Human({
            "human.actions": "playmacro",
            "human.playmacro.name": "macro1",
            "human.playmacro.delay": 10
        })
        h.init()
        assert len(h.actions) == 1
        duration, data, instance = h.actions[0]
        assert data == {"name": "macro1", "delay": 10}
        assert isinstance(instance, PlayMacro)
        assert instance.delay == 10

    def test_init_queue_schedule(self):
        h = Human({"human.schedule": "humanschedule"})
        schedule = json.loads(
            open("tests/files/humanschedule.json", "rb").read()
        )
        h.get_schedule = mock.MagicMock(return_value=schedule)
        h.calculate_queue = mock.MagicMock()
        h.init()
        assert len(h.enabled_modules) == 5
        assert len(h.always_run) == 3
        h.get_schedule.assert_called_once()
        h.calculate_queue.assert_called_once_with(schedule)

    def test_init_queue_sequential(self):
        h = Human({"human.schedule": "humansequential"})
        schedule = json.loads(
            open("tests/files/humansequential.json", "rb").read()
        )
        h.get_schedule = mock.MagicMock(return_value=schedule)
        h.queue_from_sequence = mock.MagicMock()
        h.init()
        assert len(h.enabled_modules) == 5
        assert len(h.always_run) == 3
        h.get_schedule.assert_called_once()
        h.queue_from_sequence.assert_called_once_with(schedule)

    def test_queue_from_sequence(self):
        h = Human({"human.schedule": "humansequential"})
        h.enabled_modules = {
            "browsewebsite": BrowseWebsite,
            "donothing": DoNothing,
            "playmacro": PlayMacro,
            "usecalculator": UseCalculator,
            "wordprocessor": WordProcessor
        }
        schedule = json.loads(
            open("tests/files/humansequential.json", "rb").read()
        )
        h.queue_from_sequence(schedule)
        dur1, data1, inst1 = h.actions[0]
        dur2, data2, inst2 = h.actions[1]
        dur3, data3, inst3 = h.actions[2]
        assert len(h.actions) == 3
        assert data1 == {"name": "macro1"}
        assert isinstance(inst1, PlayMacro)
        assert inst1.wait == 5
        assert data2 == {"name": "macro2"}
        assert isinstance(inst1, PlayMacro)
        assert inst2.wait == 0
        assert data3 == {"name": "macro3"}
        assert isinstance(inst3, PlayMacro)
        assert inst3.wait == 0

    def test_calculate_queue(self):
        h = Human({
            "human.schedule": "humanschedule",
            "human.schedule.totaltime": 12000
        })
        h.analyzer = mock.MagicMock()
        h.enabled_modules = {
            "browsewebsite": BrowseWebsite,
            "donothing": DoNothing,
            "playmacro": PlayMacro,
            "usecalculator": UseCalculator,
            "wordprocessor": WordProcessor
        }
        schedule = json.loads(
            open("tests/files/humanschedule.json", "rb").read()
        )
        # It it a random chance calculation. Run multiple times to confirm
        # the percentage is still correct
        for x in range(20):
            recreation = 0
            tasks = 0
            macrotask = 0
            h.calculate_queue(schedule)
            assert len(h.actions) >= 40
            assert len(h.actions) <= 80
            for duration, data, instance in h.actions:
                if isinstance(instance, (UseCalculator, WordProcessor)):
                    tasks += 1
                elif isinstance(instance, (DoNothing, BrowseWebsite)):
                    recreation += 1
                elif isinstance(instance, PlayMacro):
                    macrotask += 1

            assert macrotask == 1
            assert tasks >= 2
            assert recreation > tasks
            h.actions = []
            h.scheduled_modules = {}

    def test_get_schedule_nonexisting(self):
        h = Human({"human.schedule": "dogesuchwow"})
        schedule = h.get_schedule()
        assert schedule == {}

    def test_get_instance(self):
        h = Human({})
        h.enabled_modules = {
            "browsewebsite": BrowseWebsite,
            "donothing": DoNothing,
            "playmacro": PlayMacro,
            "usecalculator": UseCalculator,
            "wordprocessor": WordProcessor
        }

        module = h._get_instance({
            "module": "donothing",
            "delay": 60,
            "wait": 5
        })

        module2 = h._get_instance({
            "module": "donothing",
            "delay": 60,
            "wait": 5
        })

        assert module is module2
        assert module.name == "donothing"
        assert isinstance(module, DoNothing)
        assert module.delay == 60
        assert module.wait == 5
        assert len(h.scheduled_modules) == 1

    def test_init_module_multi(self):
        h = Human({})
        h.enabled_modules = {
            "browsewebsite": BrowseWebsite,
            "donothing": DoNothing,
            "playmacro": PlayMacro,
            "usecalculator": UseCalculator,
            "wordprocessor": WordProcessor
        }

        module1 = h._get_instance({
            "module": "playmacro",
            "delay": 60,
            "wait": 5,
            "data": {"name": "macro1"}
        })
        module2 = h._get_instance({
            "module": "playmacro",
            "delay": 120,
            "wait": 10,
            "data": {"name": "macro2"}
        })

        assert module1 is not module2
        assert module1.name == "playmacro"
        assert isinstance(module1, PlayMacro)
        assert module1.delay == 60
        assert module1.wait == 5
        assert module2.name == "playmacro"
        assert isinstance(module2, PlayMacro)
        assert module2.delay == 120
        assert module2.wait == 10
        assert len(h.scheduled_modules) == 1
        assert len(h.scheduled_modules["playmacro"]) == 2

    def test_run_small_actions(self):
        h = Human({})
        h.init()
        small1 = mock.MagicMock()
        small2 = mock.MagicMock()
        small1.initialized = False
        h.always_run = [small1, small2]
        h.run_small_actions()

        small1.init.assert_called_once()
        small1.run.assert_called_once()
        small2.init.assert_not_called()
        small2.run.assert_called_once()

    def test_get_action(self):
        h = Human({})
        h.init()
        h.analyzer = mock.MagicMock()
        h.analyzer.time_counter = 10
        a = PlayMacro()
        b = PlayMacro()
        h.actions = [(60, {}, a), (80, {}, b)]
        delay, data, instance = h.get_action()
        assert instance is a
        delay, data, instance = h.get_action()
        assert instance is b

    def test_get_action_delayed(self):
        h = Human({})
        h.init()
        h.analyzer = mock.MagicMock()
        h.analyzer.time_counter = 10
        a = PlayMacro()
        a.delay = 120
        b = PlayMacro()
        h.actions = [(60, {}, a), (80, {}, b)]
        delay, data, instance = h.get_action()
        assert instance is b
        delay, data, instance = h.get_action()
        assert instance is None
        h.analyzer.time_counter = 121
        delay, data, instance = h.get_action()
        assert instance is a

    def test_stop(self):
        h = Human({})
        assert h.do_run
        h.stop()
        assert not h.do_run

    def test_run_no_actions(self):
        h = Human({})
        h.init()
        h.do_run = FakeBool(True, 1)
        h.run_small_actions = mock.MagicMock()
        h.run()

        h.run_small_actions.assert_called_once()

    @mock.patch("time.sleep")
    def test_run_actions(self, ts):
        h = Human({})
        h.init()
        h.do_run = FakeBool(True, 4)
        h.run_small_actions = mock.MagicMock()
        h.analyzer = mock.MagicMock()
        h.analyzer.time_counter = 10
        a = mock.MagicMock()
        a.initialized = False
        a.wait = 10
        a.active = False
        a.runs = 2
        h.actions = [(60, {"name": "macro1"}, a)]
        h.run()

        assert h.run_small_actions.call_count == 4
        a.set_config.assert_called_with({"name": "macro1"})
        a.init.assert_called_once()
        assert a.initialized
        a.calculate_runs.assert_called_once_with(60)
        assert a.run.call_count == 2
        assert a.runs == 0
        a.action_end.assert_called_once()
        assert not a.active
        ts.assert_any_call(10)
        assert ts.call_count == 4
        assert h.actions == []

class FakeBool(object):
    def __init__(self, bool, times):
        self.bool = bool
        self.times = times

    def __nonzero__(self):
        if self.times:
            self.times -= 1
            return self.bool
        return not self.bool

class TestPlayMacro(object):

    def test_calcruns(self):
        p = PlayMacro()
        p.calculate_runs(60)
        assert p.runs == 1

    @mock.patch("os.path.isfile")
    @mock.patch("modules.auxiliary.human.Software")
    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.HwndHelper")
    def test_run(self, mh, mw, ms, mi):
        software = mock.MagicMock()
        ms.return_value = software
        window = mock.MagicMock()
        window.buttons = ["play"]
        mw.return_value = window
        p = PlayMacro()
        p.set_config({"name": "macro1"})
        p.run()

        ms.assert_called_once_with("macro", "files\\macro1.exe")
        software.start.assert_called_once()
        mw.assert_called_once_with(software.hwnd)
        mh.find_children.assert_called_once_with(window)
        window.click_button.assert_called_once_with("play")

    def test_constants(self):
        assert PlayMacro.multi_instance
        assert PlayMacro.name == "playmacro"

class TestWordprocessor(object):

    def test_constants(self):
        assert not WordProcessor.multi_instance
        assert WordProcessor.name == "wordprocessor"


    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.Autotyper")
    @mock.patch("modules.auxiliary.human.Software")
    def test_init_default(self, ms, ma, mw):
        software = mock.MagicMock()
        ms.return_value = software
        window = mock.MagicMock()
        mw.return_value = window
        w = WordProcessor()
        w.set_options({})
        w.init()

        assert w.processor == "wordpad"
        ms.assert_called_once_with(
            "wordpad",
            "C:\\Program Files\\Windows NT\\Accessories\\wordpad.exe",
            []
        )
        software.start.assert_called_once()
        software.isrunning.assert_called_once()
        mw.assert_called_once_with(software.hwnd)
        ma.assert_called_once_with(window)
        assert w.sentences > 0

    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.Autotyper")
    @mock.patch("modules.auxiliary.human.Software")
    def test_init_custom(self, ms, ma, mw):
        software = mock.MagicMock()
        ms.return_value = software
        window = mock.MagicMock()
        mw.return_value = window
        w = WordProcessor()
        w.set_options({
            "wordprocessor.exepath": "C:\\custom.exe",
            "wordprocessor.params": "-P -A 'doges' -X"
        })
        w.init()

        assert w.processor == "custom"
        ms.assert_called_once_with(
            "custom",
            "C:\\custom.exe",
            "-P -A 'doges' -X"
        )
        software.start.assert_called_once()
        software.isrunning.assert_called_once()
        mw.assert_called_once_with(software.hwnd)
        ma.assert_called_once_with(window)
        assert w.sentences > 0

    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.Autotyper")
    @mock.patch("modules.auxiliary.human.Software")
    def test_init_fail(self, ms, ma, mw):
        software = mock.MagicMock()
        software.start.return_value = False
        ms.return_value = software
        w = WordProcessor()
        w.set_options({})
        w.init()

        software.start.assert_called_once()
        software.isrunning.assert_not_called()
        mw.assert_not_called()
        ma.assert_not_called()

    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.Autotyper")
    @mock.patch("modules.auxiliary.human.Software")
    def test_init_crash(self, ms, ma, mw):
        software = mock.MagicMock()
        software.isrunning.return_value = False
        ms.return_value = software
        w = WordProcessor()
        w.set_options({})
        res = w.init()

        software.start.assert_called_once()
        software.isrunning.assert_called_once()
        assert not res
        mw.assert_not_called()
        ma.assert_not_called()

    def test_calcruns(self):
        w = WordProcessor()
        w.calculate_runs(120)
        assert w.runs == 24

    def test_run(self):
        w = WordProcessor()
        w.software = mock.MagicMock()
        w.typer = mock.MagicMock()
        w.window = mock.MagicMock()
        w.sentences = 5

        w.run()
        w.window.set_maximized.assert_called_once()
        w.window.set_focus.assert_called_once()
        w.typer.press_key.assert_called_once_with(0x23)
        w.typer.type_sentence.assert_called_once()
        assert w.sentences == 4

    def test_run_lastsentence(self):
        w = WordProcessor()
        w.software = mock.MagicMock()
        w.typer = mock.MagicMock()
        w.window = mock.MagicMock()
        w.sentences = 0

        w.run()
        w.window.set_maximized.assert_called_once()
        w.window.set_focus.assert_called_once()
        w.typer.press_key.assert_any_call(0x0D)
        w.typer.press_key.assert_any_call(0x23)
        w.typer.type_sentence.assert_called_once()
        assert w.sentences > 0

    def test_action_end(self):
        w = WordProcessor()
        w.software = mock.MagicMock()
        w.window = mock.MagicMock()
        w.window.is_minimized.return_value = False
        w.action_end()

        w.window.set_minimized.assert_called_once()

    def test_action_end_dontminimize(self):
        w = WordProcessor()
        w.software = mock.MagicMock()
        w.window = mock.MagicMock()
        w.window.is_minimized.return_value = True
        w.action_end()

        w.window.set_minimized.assert_not_called()

class TestClickMouse(object):

    def test_constants(self):
        classlist = [
            "Button", "Edit", "NetUIHWND", "ToolbarWindow32", "SysTreeView32",
            "#32768", "#32770", "Start", "MSTaskListWClass", "DirectUIHWND",
            "SysTabControl32", "ComboBox", "ScrollBar", "msctls_trackbar32",
            "ComboLBox", "TrayClockWClass", "ConsoleWindowClass"
        ]
        assert ClickMouse.alwaysrun
        assert ClickMouse.name == "click_mouse"
        for hwndclass in classlist:
            assert hwndclass in ClickMouse.ignore_classes

    def test_init(self):
        c = ClickMouse()
        c.init()
        assert isinstance(c.mouse, Mouse)

    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.USER32")
    def test_run(self, mu, mw):
        window = mock.MagicMock()
        window.get_classname.return_value = "NonIgnoredClass"
        mw.return_value = window
        c = ClickMouse()
        c.mouse = mock.MagicMock()
        c.run()

        c.mouse.leftclick.assert_called_once()

    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.USER32")
    def test_run_ignore(self, mu, mw):
        window = mock.MagicMock()
        window.get_classname.return_value = "Button"
        mw.return_value = window
        c = ClickMouse()
        c.mouse = mock.MagicMock()
        c.run()

        c.mouse.leftclick.assert_not_called()

class TestMoveMouse(object):

    def test_constants(self):
        assert MoveMouse.alwaysrun
        assert MoveMouse.name == "move_mouse"
        assert MoveMouse.reduceby == 0.15

    def test_init(self):
        m = MoveMouse()
        m.init()

        assert isinstance(m.mouse, Mouse)
        assert m.x > 0
        assert m.y > 0

    def test_run(self):
        m = MoveMouse()
        m.mouse = mock.MagicMock()
        m.x = 1920
        m.y = 1080
        m.run()
        m.mouse.move_to.assert_called_once()
        used_x = m.mouse.move_to.call_args[0][0]
        used_y = m.mouse.move_to.call_args[0][1]
        assert used_x >= 288 and used_x <= 1632
        assert used_y >= 162 and used_y <= 918

class TestDoNothing(object):

    def test_constants(self):
        assert not DoNothing.multi_instance
        assert DoNothing.name == "donothing"

    def test_calcruns(self):
        d = DoNothing()
        d.calculate_runs(120)
        assert d.runs == 24
        d.calculate_runs(124)
        assert d.runs == 24

    @mock.patch("time.sleep")
    def test_run(self, ms):
        d = DoNothing()
        d.run()
        ms.assert_called_once_with(5)

class TestWindowHandler(object):

    def test_constants(self):
        assert WindowHandler.alwaysrun
        assert WindowHandler.name == "click_buttons"
        assert len(WindowHandler.rules) >= 3

    @mock.patch("modules.auxiliary.human.USER32")
    def test_run(self, mu):
        with mock.patch('__builtin__.True', FakeBool(True, 1)):
            w = WindowHandler()
            WindowHandler.ignore_hwnds = [mock.MagicMock()]
            w.run()
            mu.EnumWindows.assert_called_once()
            assert WindowHandler.ignore_hwnds == []
            assert WindowHandler.action_count == 0

    @mock.patch("modules.auxiliary.human.USER32")
    def test_run_actions_remaining(self, mu):
        with mock.patch('__builtin__.True', FakeBool(True, 1)):
            w = WindowHandler()
            hwnd = mock.MagicMock()
            WindowHandler.ignore_hwnds = [hwnd]
            WindowHandler.action_count = 1
            w.run()
            mu.EnumWindows.call_count == 3
            assert WindowHandler.ignore_hwnds == [hwnd]
            assert WindowHandler.action_count == 0

    def test_best_match(self):
        buttons = [
            "run", "start", "running", "open"
        ]
        assert WindowHandler.best_match("run program", buttons) == "run"
        assert WindowHandler.best_match("execute", buttons) is None
        assert WindowHandler.best_match(
            "open this document", buttons
        ) == "open"

    @mock.patch("modules.auxiliary.human.USER32")
    def test_handle_clickables(self, mu):
        w = mock.MagicMock()
        w.buttons = {
            "execute": mock.MagicMock(),
            "run": mock.MagicMock(),
            "open": mock.MagicMock()
        }
        WindowHandler.handle_clickables(w)
        w.click_button.assert_called_once_with("run")

    @mock.patch("modules.auxiliary.human.KERNEL32")
    @mock.patch("ctypes.addressof")
    def test_handle_rules_close(self, ma, mk):
        WindowHandler.action_count = 0
        w = mock.MagicMock()
        w.get_windowtitle.return_value = "activation wizard"
        WindowHandler.handle_rules(w)

        w.close_window.assert_called_once()
        assert WindowHandler.action_count == 1

    @mock.patch("modules.auxiliary.human.KERNEL32")
    @mock.patch("ctypes.addressof")
    def test_handle_rules_buttonpress(self, ma, mk):
        WindowHandler.action_count = 0
        w = mock.MagicMock()
        w.get_windowtitle.return_value = "confirm save as"
        WindowHandler.handle_rules(w)

        w.click_button.assert_called_once_with("yes")
        assert WindowHandler.action_count == 1

    @mock.patch("modules.auxiliary.human.handle_save_as")
    @mock.patch("modules.auxiliary.human.KERNEL32")
    @mock.patch("ctypes.addressof")
    def test_handle_rules_custom(self, ma, mk, mh):
        _orig_rules = copy.deepcopy(WindowHandler.rules)
        WindowHandler.rules[1]["value"] = mh
        WindowHandler.action_count = 0
        w = mock.MagicMock()
        w.get_windowtitle.return_value = "opslaan als"
        WindowHandler.handle_rules(w)
        WindowHandler.rules = _orig_rules

        mh.assert_called_once_with(w)
        assert WindowHandler.action_count == 1

    @mock.patch("modules.auxiliary.human.WindowHandler.handle_clickables")
    @mock.patch("modules.auxiliary.human.KERNEL32")
    @mock.patch("ctypes.addressof")
    def test_handle_rules_noaction(self, ma, mk, mh):
        WindowHandler.action_count = 0
        w = mock.MagicMock()
        w.get_windowtitle.return_value = "Doges, such wow, many test"
        WindowHandler.handle_rules(w)

        mh.assert_called_once_with(w)
        assert WindowHandler.action_count == 1

class TestUseCalculator(object):

    def test_constants(self):
        assert not UseCalculator.multi_instance
        assert UseCalculator.name == "usecalculator"

    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.Autotyper")
    @mock.patch("modules.auxiliary.human.Software")
    def test_init(self, ms, ma, mw):
        software = mock.MagicMock()
        ms.return_value = software
        window = mock.MagicMock()
        mw.return_value = window
        u = UseCalculator()
        u.init()

        ms.assert_called_once_with(
            "calculator", "C:\\Windows\\System32\\calc.exe"
        )
        software.start.assert_called_once()
        mw.assert_called_once_with(software.hwnd)
        ma.assert_called_once_with(window)

    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.Autotyper")
    @mock.patch("modules.auxiliary.human.Software")
    def test_init_fail(self, ms, ma, mw):
        software = mock.MagicMock()
        software.start.return_value = False
        ms.return_value = software
        window = mock.MagicMock()
        mw.return_value = window
        u = UseCalculator()
        u.init()

        ms.assert_called_once_with(
            "calculator", "C:\\Windows\\System32\\calc.exe"
        )
        software.start.assert_called_once()
        mw.assert_not_called()
        ma.assert_not_called()

    def test_calcruns(self):
        u = UseCalculator()
        u.calculate_runs(120)
        assert u.runs == 1

    @mock.patch("random.randint")
    @mock.patch("modules.auxiliary.human.KERNEL32")
    def test_run(self, mk, mr):
        mr.side_effect = [2, 10, 20]
        u = UseCalculator()
        u.software = mock.MagicMock()
        u.window = mock.MagicMock()
        u.typer = mock.MagicMock()
        u.run()

        assert u.window.set_restored.call_count == 2
        assert u.window.set_foreground.call_count == 2
        assert u.window.set_focus.call_count == 2
        u.typer.type_text.assert_has_calls([
            mock.call("10"), mock.call("20")
        ])
        u.typer.press_key.assert_has_calls([
            mock.call(0x6B), mock.call(0x6B), mock.call(0x0D)
        ])

    @mock.patch("random.randint")
    @mock.patch("modules.auxiliary.human.KERNEL32")
    def test_run_fail(self, mk, mr):
        u = UseCalculator()
        u.software = mock.MagicMock()
        u.software.hwnd = None
        u.typer = mock.MagicMock()
        res = u.run()

        assert not res
        u.typer.press_key.assert_not_called()

    @mock.patch("time.sleep")
    def test_action_end(self, ms):
        u = UseCalculator()
        u.window = mock.MagicMock()
        u.action_end()
        u.window.set_minimized.assert_called_once()
        ms.assert_called_once_with(3)

class TestBrowseWebsite(object):

    def test_constants(self):
        assert BrowseWebsite.multi_instance
        assert BrowseWebsite.name == "browsewebsite"

    @mock.patch("modules.auxiliary.human.Window")
    @mock.patch("modules.auxiliary.human.Autotyper")
    @mock.patch("modules.auxiliary.human.Software")
    def test_init(self, ms, ma, mw):
        software = mock.MagicMock()
        ms.return_value = software
        window = mock.MagicMock()
        mw.return_value = window
        b = BrowseWebsite()
        b.set_config({"url": "http://example.com/42"})
        b.init()

        ms.assert_called_once_with(
            "iexplorer",
            "C:\\Program Files\\Internet Explorer\\iexplore.exe",
            ["http://example.com/42"]
        )
        software.start.assert_called_once()
        mw.assert_called_once_with(software.hwnd)
        ma.assert_called_once_with(window)

    def test_calcruns(self):
        b = BrowseWebsite()
        b.calculate_runs(120)
        assert b.runs == 12
        b.calculate_runs(124)
        assert b.runs == 12

    @mock.patch("time.sleep")
    def test_run(self, ms):
        b = BrowseWebsite()
        b.software = mock.MagicMock()
        b.window = mock.MagicMock()
        b.mouse = mock.MagicMock()
        b.run()

        b.window.set_maximized.assert_called_once()
        b.window.set_foreground.assert_called_once()
        b.window.set_focus.assert_called_once()
        b.mouse.scroll.assert_called_with(-30)

    @mock.patch("modules.auxiliary.human.USER32")
    def test_action_end(self, mu):
        b = BrowseWebsite()
        b.window = mock.MagicMock()
        b.typer = mock.MagicMock()
        b.software = mock.MagicMock()
        b.action_end()

        b.window.set_maximized.assert_called_once()
        b.window.set_focus.assert_called_once()
        b.typer.press_key.assert_has_calls([
            mock.call(0x21), mock.call(0x21), mock.call(0x21),
            mock.call(0x21), mock.call(0x21)
        ])
        b.window.set_minimized.assert_called_once()

    @mock.patch("modules.auxiliary.human.USER32")
    def test_action_end_maximized(self, mu):
        mu.IsIconic.return_value = False
        b = BrowseWebsite()
        b.window = mock.MagicMock()
        b.typer = mock.MagicMock()
        b.software = mock.MagicMock()
        b.action_end()

        b.window.set_maximized.assert_not_called()
        b.typer.press_key.assert_has_calls([
            mock.call(0x21), mock.call(0x21), mock.call(0x21),
            mock.call(0x21), mock.call(0x21)
        ])
        b.window.set_minimized.assert_called_once()
