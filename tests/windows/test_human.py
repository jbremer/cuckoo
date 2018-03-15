# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import mock

from modules.auxiliary.human import (
    Human, BrowseWebsite, DoNothing, PlayMacro, UseCalculator, WordProcessor,
    ClickMouse, MoveMouse, WindowHandler
)

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
