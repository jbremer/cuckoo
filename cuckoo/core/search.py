# Copyright (C) 2017 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import re

from cuckoo.common.elastic import elastic
from cuckoo.common.mongo import mongo
from cuckoo.common.utils import validate_url, isipaddress, ishash
from cuckoo.core.database import Database

db = Database()

class Search(object):
    """Search wrapper around MongoDB & ElasticSearch."""

    def guess_term(self, value):
        if ishash(value, 32):
            return "md5"

        if ishash(value, 40):
            return "sha1"

        if ishash(value, 64):
            return "sha256"

        if ishash(value, 128):
            return "sha512"

        # TODO Could, e.g., also be a 32-bit encoded IP address.
        if ishash(value, 8):
            return "crc32"

        if isipaddress(value):
            return "ip"

        if bool(validate_url(value)):
            return "url"

    def find(self, term, value):
        """Combines ElasticSearch and MongoDB for search."""
        if not term:
            term = self.guess_term(value)
        else:
            term = term.strip()

        value = value.strip()

        mongo_elastic_queries = [
            "regkey_read", "regkey_opened", "regkey_written", "file_written",
            "file_deleted", "file_created", "file_moved", "file_opened",
            "file_recreated",
        ]
        elastic_queries = ["buffer", "dropped"]

        value = re.escape(value)

        if not term or term in mongo_elastic_queries:
            mongo_results = list(mongo.search(term, value))
            elastic_results = elastic.search(term, value)
            return mongo_results + elastic_results
        elif term in elastic_queries:
            return elastic.search(term, value)
        else:
            return list(mongo.search(term, value))

searcher = Search()
