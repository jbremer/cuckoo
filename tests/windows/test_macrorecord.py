# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission

import mock
import os

from modules.auxiliary.recordmacro import RecordMacro

class TestRecordMacro(object):

    def test_cons_init(self):
        r = RecordMacro({})
        assert r.settings["name"] == "macro1"
        assert r.settings["CurForm"] == "3"
        assert r.settings["chbTray"] == "0"
        assert r.settings["chbMinimize"] == "0"
        assert r.settings["cbLeftTray"] == "2"
        assert r.settings["Visible"] == "0"

    def test_cons_init_options(self):
        r = RecordMacro({"macrorecord.name": "macro500"})
        assert r.settings["name"] == "macro500"

    @mock.patch("modules.auxiliary.recordmacro.random_string")
    def test_init(self, mr):
        mr.return_value = "dogedoge"
        r = RecordMacro({})
        r.analyzer = mock.MagicMock()
        r.analyzer.config.package = "recordmacro"
        r.analyzer.target = "tests/files/recorder.zip"
        r.init()

        uploadpath = os.path.join(
            os.environ["USERPROFILE"], "Desktop", "Upload to Cuckoo"
        )
        macropath = os.path.join(os.environ["TEMP"], "dogedoge")

        assert os.environ["MACRORECORD"] == macropath
        assert r.upload == uploadpath
        assert os.path.exists(uploadpath)
        assert os.path.exists(macropath)
        conf = open(os.path.join(macropath, "options.gt")).read()
        changed_lines = [
            "<name >macro1</>", "<outdir >%s</>" % uploadpath,
            "<CurForm >3</>", "<chbTray >0</>", "<chbMinimize >0</>",
            "<cbLeftTray >2</>", "<Visible >0</>"
        ]

        for change in changed_lines:
            assert change in conf
