# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import os
import shutil

from cuckoo.common.abstracts import Processing
from cuckoo.misc import cwd

log = logging.getLogger(__name__)

class Macro(Processing):
    """Copies a recorded macro exe to make it available for use"""

    def run(self):
        self.key = "recordedmacro"

        if self.task["package"] != "recordmacro":
            return

        data = {
            "record_name": self.task["options"].get("macrorecord.name"),
            "recordings": []
        }

        recordings_dir = cwd("macro")
        if not os.path.isdir(self.macro_path):
            return

        for macro in os.listdir(self.macro_path):
            macro_path = os.path.join(self.macro_path, macro)
            if not os.path.isfile(macro_path) or not macro.endswith(".exe"):
                continue

            data["recordings"].append(macro)
            copied_macro = os.path.join(recordings_dir, macro)

            count = 1
            while os.path.exists(copied_macro):
                name, ext = os.path.splitext(macro)
                newname = "%s-%s%s" % (name, count, ext)
                copied_macro = os.path.join(recordings_dir, newname)
                count += 1

            log.debug(
                "Copying recorded macro '%s' to '%s'", macro, copied_macro
            )
            shutil.copyfile(macro_path, copied_macro)

        data["recordings"].sort()
        return data
