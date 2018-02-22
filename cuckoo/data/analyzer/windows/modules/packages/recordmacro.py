# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from lib.common.abstracts import Package
from lib.common.exceptions import CuckooPackageError

class RecordMacro(Package):
    """Unpack the macro software to the desktop of the current user"""

    def start(self, path):
        macro_dir = os.environ.get("MACRORECORD")
        if not macro_dir or not os.path.isdir(macro_dir):
            raise CuckooPackageError(
                "Macro recording software '%s' does not exist" % macro_dir
            )

        return self.execute(os.path.join(macro_dir, "pautomation.exe"), None)
