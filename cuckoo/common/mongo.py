# Copyright (C) 2017 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import gridfs
import os.path
import pymongo

from cuckoo.common.config import config
from cuckoo.common.exceptions import CuckooOperationalError

class Mongo(object):
    def __init__(self):
        self.client = None
        self.db = None

        self.enabled = None
        self.hostname = None
        self.port = None
        self.database = None
        self.username = None
        self.password = None
        self.grid = None

    def init(self):
        self.enabled = config("reporting:mongodb:enabled")
        self.hostname = config("reporting:mongodb:host")
        self.port = config("reporting:mongodb:port")
        self.database = config("reporting:mongodb:db")
        self.username = config("reporting:mongodb:username")
        self.password = config("reporting:mongodb:password")
        return self.enabled

    def connect(self):
        if not self.enabled:
            return

        try:
            self.client = pymongo.MongoClient(self.hostname, self.port)
            self.db = self.client[self.database]
            if self.username and self.password:
                self.db.authenticate(self.username, self.password)
            self.grid = gridfs.GridFS(self.db)
        except pymongo.errors.PyMongoError as e:
            raise CuckooOperationalError(
                "Unable to connect to MongoDB: %s" % e
            )

    def drop(self):
        if not self.enabled:
            return

        try:
            if self.client and self.database in self.client.database_names():
                self.client.drop_database(self.database)
        except TypeError as e:
            raise CuckooOperationalError(
                "Unable to find Database %s in MongoDB: %s" %
                (self.database, e)
            )
        except pymongo.errors.PyMongoError as e:
            raise CuckooOperationalError(
                "Unable to connect to MongoDB: %s" % e
            )

    def _search_one_key(self, key, value):
        return self.db.analysis.find({
            key: {
                "$regex": value,
                "$options": "-i",
            },
        })

    def _search_one_of(self, key, value):
        return self.db.analysis.find({
            key: {
                "$elemMatch": {
                    "$regex": value,
                    "$options": "-i",
                },
            },
        })

    def _search_multiple_keys(self, value, *keys):
        or_ = []
        for key in keys:
            or_.append({
                key: {
                    "$regex": value, "$options":
                    "-i",
                },
            })
        return self.db.analysis.find({"$or": or_})

    def search_filename(self, value):
        return self._search_one_key("target.file.name", value)

    search_name = search_filename

    def search_filetype(self, value):
        return self._search_one_key("target.file.type", value)

    search_type = search_filetype

    def search_string(self, value):
        return self._search_one_key("strings", value)

    def search_ssdeep(self, value):
        return self._search_one_key("target.file.ssdeep", value)

    def search_crc32(self, value):
        return self._search_one_key("target.file.crc32", value)

    def search_file(self, value):
        return self._search_one_key("behavior.summary.files", value)

    def search_key(self, value):
        return self._search_one_key("behavior.summary.keys", value)

    def search_mutex(self, value):
        return self._search_one_key("behavior.summary.mutex", value)

    def search_domain(self, value):
        return self._search_one_key("network.domains.domain", value)

    def search_ip(self, value):
        return self._search_one_key("network.hosts", value)

    def search_signature(self, value):
        return self._search_multiple_keys(
            value, "signatures.families", "signatures.name",
            "signatures.marks.call.api", "signatures.description"
        )

    search_sig = search_signature

    def search_url(self, value):
        return self._search_multiple_keys(
            value, "target.url", "target.file.urls"
        )

    def search_imphash(self, value):
        return self._search_one_key("static.pe_imphash", value)

    def search_md5(self, value):
        return self._search_one_key("target.file.md5", value)

    def search_sha1(self, value):
        return self._search_one_key("target.file.sha1", value)

    def search_sha256(self, value):
        return self._search_one_key("target.file.sha256", value)

    def search_sha512(self, value):
        return self._search_one_key("target.file.sha512", value)

    def search_args(self, value):
        return self._search_one_key("behavior.processes.command_line", value)

    search_cmdline = search_args

    def search_regkey_read(self, value):
        return self._search_one_of("behavior.summary.regkey_read", value)

    def search_regkey_written(self, value):
        return self._search_one_of("behavior.summary.regkey_written", value)

    def search_registry(self, value):
        return self._search_one_of(
            value,
            "behavior.summary.regkey_read", "behavior.summary.regkey_written"
        )

    search_reg = search_registry

    def search(self, term, value):
        results = getattr(self, "search_%s" % term, lambda _: None)(value)
        for result in results or []:
            if result["target"]["category"] == "file":
                target = os.path.basename(result["target"]["name"])
            elif result["target"]["category"] == "archive":
                target = result["target"]["human"]
            elif result["target"]["category"] == "url":
                target = result["target"]["url"]
            else:
                target = None

            yield {
                "id": result["info"]["id"],
                "target": target,
            }

mongo = Mongo()
