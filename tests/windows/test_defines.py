# Copyright (C) 2018 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import ctypes
import string

from lib.common.defines import (
    NTDLL, KERNEL32, ADVAPI32, USER32, SHELL32, PSAPI, VirtualKeys,
    POINT, RECT
)

def testdlls():
    assert NTDLL == ctypes.windll.ntdll
    assert KERNEL32 == ctypes.windll.kernel32
    assert ADVAPI32 == ctypes.windll.advapi32
    assert USER32 == ctypes.windll.user32
    assert SHELL32 == ctypes.windll.shell32
    assert PSAPI == ctypes.windll.psapi


class TestVirtualKeys(object):

    def test_key_mappings(self):
        for c in "%s%s" % (string.ascii_lowercase, string.digits):
            assert chr(VirtualKeys.key_mappings[c]).lower() == c

        assert VirtualKeys.key_mappings["."] == 0xBE
        assert VirtualKeys.key_mappings[","] == 0xBC
        assert VirtualKeys.key_mappings[" "] == 0x20
        assert VirtualKeys.key_mappings["+"] == 0x6B

    def test_special_keys(self):
        assert VirtualKeys.VK_RETURN == 0x0D
        assert VirtualKeys.VK_BACK == 0x08
        assert VirtualKeys.VK_SHIFT == 0x10
        assert VirtualKeys.VK_END == 0x23
        assert VirtualKeys.VK_PRIOR == 0x21
        assert VirtualKeys.VK_NEXT == 0x22


class TestStructures(object):

    def test_point(self):
        a = POINT.from_buffer_copy("A"*8)
        assert a.x == 0x41414141
        assert a.y == 0x41414141

    def test_rect(self):
        a = RECT.from_buffer_copy("A"*16)
        assert a.left == 0x41414141
        assert a.top == 0x41414141
        assert a.right == 0x41414141
        assert a.bottom == 0x41414141
