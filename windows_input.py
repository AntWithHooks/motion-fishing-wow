"""Send one real key down/up pair for one intentionally performed gesture.

Windows SendInput, like the previous v0.2 tested by the user.
"""
from __future__ import annotations
import os
import time

KEYS = {**{f'F{i}': 0x70 + i - 1 for i in range(1, 13)}, 'SPACE': 0x20, 'ENTER': 0x0D}


def foreground_title() -> str:
    if os.name != 'nt':
        return ''
    import ctypes
    u32 = ctypes.WinDLL('user32', use_last_error=True)
    hwnd = u32.GetForegroundWindow()
    buffer = ctypes.create_unicode_buffer(512)
    u32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def tap(key: str) -> None:
    if os.name != 'nt':
        raise RuntimeError('Клавиатурный ввод поддерживается только на Windows')
    if key not in KEYS:
        raise ValueError(f'Неизвестная клавиша: {key}')
    import ctypes
    from ctypes import wintypes

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD),
                    ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD),
                    ('dwExtraInfo', ctypes.c_size_t)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG),
                    ('mouseData', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                    ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [('uMsg', wintypes.DWORD), ('wParamL', wintypes.WORD),
                    ('wParamH', wintypes.WORD)]

    class UNION(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT), ('hi', HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ('u',)
        _fields_ = [('type', wintypes.DWORD), ('u', UNION)]

    u32 = ctypes.WinDLL('user32', use_last_error=True)
    u32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    u32.SendInput.restype = wintypes.UINT
    for flags in (0, 0x0002):
        packet = INPUT(type=1, ki=KEYBDINPUT(KEYS[key], 0, flags, 0, 0))
        sent = u32.SendInput(1, ctypes.byref(packet), ctypes.sizeof(INPUT))
        if sent != 1:
            raise OSError(ctypes.get_last_error(), 'Windows не принял SendInput')
        if flags == 0:
            time.sleep(0.055)
