r"""DS2 CD-key presence check (Windows).

The Internet lobby (GameSpy, now OpenSpy via PATCH OPENSPY) refuses to start without the retail CD key:
"Could not find a valid CDKey. You will require a valid CDKey to play online." The exe reads it from the
registry value `PID` under HKLM\Software\Microsoft\Microsoft Games\DungeonSiege2 (32-bit view, i.e.
WOW6432Node on 64-bit Windows) — written by the retail/Steam installers, NOT by GOG's. LAN play never needs
it. This module only reports the state; ds2fix never writes keys.
"""
import os

KEY_PATH = r"Software\Microsoft\Microsoft Games\DungeonSiege2"
VALUE = "PID"


def present():
    """True if the PID value exists (either registry view); False if not; None off Windows."""
    if os.name != "nt":
        return None
    import winreg
    for flag in (getattr(winreg, "KEY_WOW64_32KEY", 0), getattr(winreg, "KEY_WOW64_64KEY", 0)):
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(root, KEY_PATH, 0, winreg.KEY_READ | flag) as k:
                    winreg.QueryValueEx(k, VALUE)
                    return True
            except OSError:
                continue
    return False


def describe():
    st = present()
    if st is None:
        return "n/a (Linux/Wine)"
    if st:
        return "present (Internet/OpenSpy lobby can log in)"
    return ("not in the registry — the Internet (OpenSpy) lobby will say \"Could not find a valid CDKey\"; "
            "GOG installs ship no key (retail/Steam do). LAN play does not need it.")
