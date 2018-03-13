# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import os
import time

from lib.common.abstracts import Package
from lib.common.exceptions import CuckooPackageError
from lib.common.uihelper import HwndHelper, Window

log = logging.getLogger(__name__)

class RecordMacro(Package):
    """Unpack the macro software to the desktop of the current user"""

    def start(self, path):
        macro_dir = os.environ.get("MACRORECORD")
        if not macro_dir or not os.path.isdir(macro_dir):
            raise CuckooPackageError(
                "Macro recording software '%s' does not exist" % macro_dir
            )

        pid = self.execute(os.path.join(macro_dir, "pautomation.exe"), None)

        # If the human module is not specifically disabled, minimize
        # the recorder, as it might be in the way of any macros being played
        if "human" not in self.options:
            # Give the recorder a little time to start before trying to
            # manipulate the window state
            time.sleep(5)
            log.debug(
                "Minimizing macro recorder because human module is not"
                " disabled"
            )
            hwnd = HwndHelper.search_hwnd(pid)
            if hwnd:
                Window(hwnd).set_minimized()

        return pid
