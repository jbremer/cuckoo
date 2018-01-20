# Copyright (C) 2011-2013 Claudio Guarnieri.
# Copyright (C) 2014-2017 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from ctypes import *

NTDLL    = windll.ntdll
KERNEL32 = windll.kernel32
ADVAPI32 = windll.advapi32
USER32   = windll.user32
SHELL32  = windll.shell32
PSAPI    = windll.psapi

BYTE      = c_ubyte
WORD      = c_ushort
DWORD     = c_ulong
LONG      = c_ulong
LPBYTE    = POINTER(c_ubyte)
LPTSTR    = POINTER(c_char)
PWSTR     = c_wchar_p
HANDLE    = c_void_p
PVOID     = c_void_p
LPVOID    = c_void_p
UINT_PTR  = c_ulong
SIZE_T    = c_ulong
HMODULE   = c_void_p
NULL      = c_int(0)

DEBUG_PROCESS             = 0x00000001
CREATE_NEW_CONSOLE        = 0x00000010
CREATE_SUSPENDED          = 0x00000004
DBG_CONTINUE              = 0x00010002
INFINITE                  = 0xFFFFFFFF
PROCESS_ALL_ACCESS        = 0x001F0FFF
THREAD_ALL_ACCESS         = 0x001f03ff
TOKEN_ALL_ACCESS          = 0x000F01FF
SE_PRIVILEGE_ENABLED      = 0x00000002
STILL_ACTIVE              = 0x00000103

PAGE_EXECUTE_READWRITE    = 0x00000040
PAGE_EXECUTE              = 0x00000010
PAGE_EXECUTE_READ         = 0x00000020
PAGE_READONLY             = 0x00000002
PAGE_READWRITE            = 0x00000004

MEM_COMMIT                = 0x00001000
MEM_RESERVE               = 0x00002000
MEM_DECOMMIT              = 0x00004000
MEM_RELEASE               = 0x00008000
MEM_RESET                 = 0x00080000

MEM_IMAGE                 = 0x01000000
MEM_MAPPED                = 0x00040000
MEM_PRIVATE               = 0x00020000

PAGE_NOACCESS             = 0x00000001
PAGE_READONLY             = 0x00000002
PAGE_READWRITE            = 0x00000004
PAGE_WRITECOPY            = 0x00000008
PAGE_EXECUTE              = 0x00000010
PAGE_EXECUTE_READ         = 0x00000020
PAGE_EXECUTE_READWRITE    = 0x00000040
PAGE_EXECUTE_WRITECOPY    = 0x00000080
PAGE_GUARD                = 0x00000100
PAGE_NOCACHE              = 0x00000200
PAGE_WRITECOMBINE         = 0x00000400

PIPE_ACCESS_INBOUND       = 0x00000001
PIPE_ACCESS_DUPLEX        = 0x00000003
PIPE_TYPE_MESSAGE         = 0x00000004
PIPE_READMODE_MESSAGE     = 0x00000002
PIPE_WAIT                 = 0x00000000
PIPE_UNLIMITED_INSTANCES  = 0x000000ff
PIPE_TYPE_BYTE            = 0x00000000
PIPE_READMODE_BYTE        = 0x00000000
FILE_FLAG_WRITE_THROUGH   = 0x80000000
INVALID_HANDLE_VALUE      = 0xffffffff
ERROR_BROKEN_PIPE         = 0x0000006d
ERROR_MORE_DATA           = 0x000000EA
ERROR_PIPE_CONNECTED      = 0x00000217

WAIT_TIMEOUT              = 0x00000102

FILE_ATTRIBUTE_HIDDEN     = 0x00000002

WM_CLOSE                  = 0x00000010
WM_GETTEXT                = 0x0000000D
WM_GETTEXTLENGTH          = 0x0000000E
WM_SETFOCUS               = 0x00000007
WM_LBUTTONDOWN            = 0x00000201
WM_LBUTTONUP              = 0x00000202

BM_CLICK                  = 0x000000F5

MOUSEEVENTF_LEFTDOWN      = 0x00000002
MOUSEEVENTF_LEFTUP        = 0x00000004
MOUSEEVENTF_RIGHTDOWN     = 0x00000008
MOUSEEVENTF_RIGHTUP       = 0x00000010
MOUSEEVENTF_WHEEL         = 0x00000800

SW_RESTORE                = 9
SW_MAXIMIZE               = 3
SW_MINIMIZE               = 6

SHARD_PATHA               = 0x00000002

GENERIC_READ              = 0x80000000
GENERIC_WRITE             = 0x40000000
GENERIC_EXECUTE           = 0x20000000
GENERIC_ALL               = 0x10000000

FILE_SHARE_READ           = 0x00000001
FILE_SHARE_WRITE          = 0x00000002
FILE_SHARE_DELETE         = 0x00000004

CREATE_NEW                = 1
CREATE_ALWAYS             = 2
OPEN_EXISTING             = 3
OPEN_ALWAYS               = 4
TRUNCATE_EXISTING         = 5


class VirtualKeys(object):
    VK_0 = 0x30
    VK_1 = 0x31
    VK_2 = 0x32
    VK_3 = 0x33
    VK_4 = 0x34
    VK_5 = 0x35
    VK_6 = 0x36
    VK_7 = 0x37
    VK_8 = 0x38
    VK_9 = 0x39
    VK_A = 0x41
    VK_B = 0x42
    VK_C = 0x43
    VK_D = 0x44
    VK_E = 0x45
    VK_F = 0x46
    VK_G = 0x47
    VK_H = 0x48
    VK_I = 0x49
    VK_J = 0x4A
    VK_K = 0x4B
    VK_L = 0x4C
    VK_M = 0x4D
    VK_N = 0x4E
    VK_O = 0x4F
    VK_P = 0x50
    VK_Q = 0x51
    VK_R = 0x52
    VK_S = 0x53
    VK_T = 0x54
    VK_U = 0x55
    VK_V = 0x56
    VK_W = 0x57
    VK_X = 0x58
    VK_Y = 0x59
    VK_Z = 0x5A
    VK_SPACE = 0x20
    VK_RETURN = 0x0D
    VK_OEM_PERIOD = 0xBE
    VK_OEM_COMMA = 0xBC
    VK_ADD = 0x6B
    VK_BACK = 0x08
    VK_SHIFT = 0x10
    VK_END = 0x23
    VK_PRIOR = 0x21
    VK_NEXT = 0x22

    key_mappings = {
        "a": VK_A,
        "b": VK_B,
        "c": VK_C,
        "d": VK_D,
        "e": VK_E,
        "f": VK_F,
        "g": VK_G,
        "h": VK_H,
        "i": VK_I,
        "j": VK_J,
        "k": VK_K,
        "l": VK_L,
        "m": VK_M,
        "n": VK_N,
        "o": VK_O,
        "p": VK_P,
        "q": VK_Q,
        "r": VK_R,
        "s": VK_S,
        "t": VK_T,
        "u": VK_U,
        "v": VK_V,
        "w": VK_W,
        "x": VK_X,
        "y": VK_Y,
        "z": VK_Z,
        "0": VK_0,
        "9": VK_9,
        "8": VK_8,
        "7": VK_7,
        "6": VK_6,
        "5": VK_5,
        "4": VK_4,
        "3": VK_3,
        "2": VK_2,
        "1": VK_1,
        ".": VK_OEM_PERIOD,
        ",": VK_OEM_COMMA,
        " ": VK_SPACE,
        "+": VK_ADD
    }

class STARTUPINFO(Structure):
    _fields_ = [
        ("cb",            DWORD),
        ("lpReserved",    LPTSTR),
        ("lpDesktop",     LPTSTR),
        ("lpTitle",       LPTSTR),
        ("dwX",           DWORD),
        ("dwY",           DWORD),
        ("dwXSize",       DWORD),
        ("dwYSize",       DWORD),
        ("dwXCountChars", DWORD),
        ("dwYCountChars", DWORD),
        ("dwFillAttribute",DWORD),
        ("dwFlags",       DWORD),
        ("wShowWindow",   WORD),
        ("cbReserved2",   WORD),
        ("lpReserved2",   LPBYTE),
        ("hStdInput",     HANDLE),
        ("hStdOutput",    HANDLE),
        ("hStdError",     HANDLE),
    ]

class PROCESS_INFORMATION(Structure):
    _fields_ = [
        ("hProcess",    HANDLE),
        ("hThread",     HANDLE),
        ("dwProcessId", DWORD),
        ("dwThreadId",  DWORD),
    ]

class LUID(Structure):
    _fields_ = [
        ("LowPart", DWORD),
        ("HighPart", LONG),
    ]

class LUID_AND_ATTRIBUTES(Structure):
    _fields_ = [
        ("Luid", LUID),
        ("Attributes", DWORD),
    ]

class TOKEN_PRIVILEGES(Structure):
    _fields_ = [
        ("PrivilegeCount", DWORD),
        ("Privileges", LUID_AND_ATTRIBUTES),
    ]

class MEMORY_BASIC_INFORMATION(Structure):
    _fields_ = [
        ("BaseAddress", PVOID),
        ("AllocationBase", PVOID),
        ("AllocationProtect", DWORD),
        ("RegionSize", SIZE_T),
        ("State", DWORD),
        ("Protect", DWORD),
        ("Type", DWORD),
    ]

class PROC_STRUCT(Structure):
    _fields_ = [
        ("wProcessorArchitecture", WORD),
        ("wReserved", WORD),
    ]

class SYSTEM_INFO_UNION(Union):
    _fields_ = [
        ("dwOemId", DWORD),
        ("sProcStruc", PROC_STRUCT),
    ]

class SYSTEM_INFO(Structure):
    _fields_ = [
        ("uSysInfo", SYSTEM_INFO_UNION),
        ("dwPageSize", DWORD),
        ("lpMinimumApplicationAddress", LPVOID),
        ("lpMaximumApplicationAddress", LPVOID),
        ("dwActiveProcessorMask", DWORD),
        ("dwNumberOfProcessors", DWORD),
        ("dwProcessorType", DWORD),
        ("dwAllocationGranularity", DWORD),
        ("wProcessorLevel", WORD),
        ("wProcessorRevision", WORD),
    ]

class SYSTEMTIME(Structure):
    _pack_ = 1
    _fields_ = [
        ("wYear", WORD),
        ("wMonth", WORD),
        ("wDayOfWeek", WORD),
        ("wDay", WORD),
        ("wHour", WORD),
        ("wMinute", WORD),
        ("wSecond", WORD),
        ("wMilliseconds", WORD),
    ]

class UNICODE_STRING(Structure):
    _fields_ = [
        ("Length", c_ushort),
        ("MaximumLength", c_ushort),
        ("Buffer", c_wchar_p),
    ]

class POINT(Structure):
    _fields_ = [
        ("x", c_ulong),
        ("y", c_ulong)
    ]

class _RECT(Structure):
    _fields_ = [
        ("left", c_ulong),
        ("top", c_ulong),
        ("right", c_ulong),
        ("bottom", c_ulong),
    ]

EnumWindowsProc = WINFUNCTYPE(c_bool, POINTER(c_int), POINTER(c_int))
EnumChildProc = WINFUNCTYPE(c_bool, POINTER(c_int), POINTER(c_int))
