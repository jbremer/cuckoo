# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission

def get_prefix_keys(prefix, collection):
    return [key for key in collection if key.startswith(prefix)]