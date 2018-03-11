# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission

import logging
import os
import re
import shutil
import socket
import threading
import time
import zipfile

from lib.common.abstracts import Auxiliary
from lib.common.exceptions import CuckooError
from lib.common.rand import random_string
from lib.common.results import upload_to_host

log = logging.getLogger(__name__)

class RecordMacro(threading.Thread, Auxiliary):
    def __init__(self, options={}, analyzer=None):
        threading.Thread.__init__(self)
        Auxiliary.__init__(self, options, analyzer)
        self.do_run = True
        self.upload = None
        self.uploaded = None
        self.macro_dir = None
        self.settings = {
            "name": self.options.get("macrorecord.name") or "macro_recording",
            "CurForm": "3",
            "chbTray": "0",
            "chbMinimize": "0",
            "cbLeftTray": "2",
            "Visible": "0"
        }

    def stop(self):
        self.do_run = False

    def init(self):
        """Unpack the macro software at the target, and ensure
        the user will have time to record a macro, without the analyzer
        stopping. Also prepare the software config."""
        if self.analyzer.config.package != "recordmacro":
            return

        if not self.options.get("free"):
            log.debug("Options free not passed, setting free=True")
            self.options["free"] = True

        self.analyzer.config.timeout = 3600

        self.macro_dir = os.path.join(os.environ["TEMP"], random_string(10))
        zipfile.ZipFile(self.analyzer.target).extractall(self.macro_dir)
        os.environ["MACRORECORD"] = self.macro_dir

        self.upload = os.path.join(
            os.environ["USERPROFILE"], "Desktop", "Upload to Cuckoo"
        )
        self.uploaded = os.path.join(self.upload, "uploaded")

        try:
            os.makedirs(self.uploaded)
        except (WindowsError, OSError) as e:
            raise CuckooError(
                "Failed to create upload or store dir at '%s': %s" %
                (self.upload, e)
            )

        # Set the default save dir to the dir that will be uploaded
        self.settings["outdir"] = self.upload

        conf_path = os.path.join(self.macro_dir, "options.gt")
        macro_options = open(conf_path, "rb").read()

        # Find and replace the options to prepare the macro recorder as much
        # as possible for the user
        for key, value in self.settings.iteritems():
            replace = "<%s >%s</>" % (key, value)
            found = re.search("<%s >(.*)</>" % key, macro_options).group()
            macro_options = macro_options.replace(found, replace, 1)

        with open(conf_path, "wb") as fp:
            fp.write(macro_options)

    def run(self):
        uploaded = {}

        if self.analyzer.config.package != "recordmacro":
            return

        while self.do_run:
            time.sleep(1)

            for filename in os.listdir(self.upload):
                mpath = os.path.join(self.upload, filename)
                if not os.path.isfile(mpath):
                    continue

                # Only re-upload if it is a new file or if it has been edited
                edittime = os.path.getmtime(mpath)
                if uploaded.get(filename, 0) >= edittime:
                    continue

                macro_name = filename
                copy_to = os.path.join(self.uploaded, filename)

                # Make sure the file name is unique before uploading and
                # copying
                count = 1
                while os.path.isfile(copy_to):
                    name, ext = os.path.splitext(filename)
                    macro_name = "%s-%s%s" % (name, count, ext)
                    copy_to = os.path.join(self.uploaded, macro_name)
                    count += 1

                try:
                    upload_to_host(mpath, os.path.join("macros", macro_name))
                except (IOError, socket.error) as e:
                    log.error(
                        "Failed to upload macro '%s' to host. %s", mpath, e
                    )
                else:
                    log.info(
                        "Uploaded macro '%s' to host as '%s'", mpath,
                        macro_name
                    )
                    shutil.copyfile(mpath, copy_to)
                    uploaded[filename] = edittime
