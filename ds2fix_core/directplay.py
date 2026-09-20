"""DirectPlay 8 detection + enable helper (Windows).

DS2 multiplayer (host AND join, LAN or direct-IP) is built on DirectPlay 8 (`Microsoft DirectPlay8 Server`
via COM). Windows 10/11 ship DirectPlay as a disabled *legacy* optional feature: `dpnet.dll` is a 10 KB
"DirectPlay Stub" that pops the "An app on your PC needs the following Windows feature" installer the first
time a game touches it. If the player skips that prompt, DS2's CoCreateInstance fails and the game
dereferences the NULL interface (crash at `Flick::FlickManager::RSCreateAndLaunchServerSequence`, verified
on Windows 11 / GOG 2.3). So: detect the stub up front, say so in `info`/`play`/the GUI, and offer to
enable the feature (an elevated DISM call — UAC prompt — nothing else is touched).

Not a ds2fix bug and not patchable in the exe in any useful way (the engine needs the real DirectPlay
provider); on Linux, Wine ships its own dpnet, so this module reports "n/a" there.
"""
import os

FEATURE = "DirectPlay"
STUB_MARK = "DirectPlay Stub".encode("utf-16-le")   # FileDescription of the Windows 10/11 FoD stub
STUB_MAX = 64 * 1024                                # the real DirectPlay 8 dpnet.dll is a few hundred KB
SETTINGS_PATH = ("Settings > Apps > Optional features > More Windows features > Legacy Components > DirectPlay")
DISM_ARGS = f"/online /enable-feature /featurename:{FEATURE} /all /norestart"


def dpnet_path():
    """The dpnet.dll a 32-bit process (DS2) loads: SysWOW64 on 64-bit Windows, System32 on 32-bit."""
    windir = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
    for sub in ("SysWOW64", "System32"):
        p = os.path.join(windir, sub, "dpnet.dll")
        if os.path.exists(p):
            return p
    return os.path.join(windir, "SysWOW64", "dpnet.dll")


def is_stub(path):
    """True when `path` is the Feature-on-Demand stub rather than the real DirectPlay 8 provider."""
    try:
        size = os.path.getsize(path)
        if size > STUB_MAX:
            return False
        with open(path, "rb") as fh:
            return STUB_MARK in fh.read()
    except OSError:
        return False


def status():
    """'enabled' | 'stub' | 'missing' | 'n/a' (not Windows)."""
    if os.name != "nt":
        return "n/a"
    p = dpnet_path()
    if not os.path.exists(p):
        return "missing"
    return "stub" if is_stub(p) else "enabled"


def describe(st=None):
    """One human line for `info` / the GUI."""
    st = st or status()
    if st == "n/a":
        return "n/a (Linux/Wine ships its own DirectPlay)"
    if st == "enabled":
        return "enabled (multiplayer host/join OK)"
    return (f"NOT enabled — multiplayer Host/Join will crash. Run `ds2fix directplay --enable` (admin prompt) "
            f"or turn on {SETTINGS_PATH}")


def needs_enable():
    return status() in ("stub", "missing")


def _dism_exe():
    windir = os.environ.get("SystemRoot") or r"C:\Windows"
    # a 32-bit process is redirected to SysWOW64 (no dism there); Sysnative reaches the real System32.
    for sub in ("Sysnative", "System32"):
        p = os.path.join(windir, sub, "dism.exe")
        if os.path.exists(p):
            return p
    return "dism.exe"


def enable(log=print):
    """Enable the DirectPlay optional feature through an elevated DISM (UAC prompt). Returns the new status.
    Raises RuntimeError if the prompt is declined or DISM fails."""
    if os.name != "nt":
        raise RuntimeError("DirectPlay enabling is a Windows-only step (Wine has its own).")
    if status() == "enabled":
        log("DirectPlay is already enabled.")
        return "enabled"
    import ctypes
    from ctypes import wintypes as w

    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [("cbSize", w.DWORD), ("fMask", w.ULONG), ("hwnd", w.HWND), ("lpVerb", w.LPCWSTR),
                    ("lpFile", w.LPCWSTR), ("lpParameters", w.LPCWSTR), ("lpDirectory", w.LPCWSTR),
                    ("nShow", ctypes.c_int), ("hInstApp", w.HINSTANCE), ("lpIDList", ctypes.c_void_p),
                    ("lpClass", w.LPCWSTR), ("hkeyClass", w.HKEY), ("dwHotKey", w.DWORD),
                    ("hIcon", w.HANDLE), ("hProcess", w.HANDLE)]

    SEE_MASK_NOCLOSEPROCESS = 0x40
    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = "runas"
    sei.lpFile = _dism_exe()
    sei.lpParameters = DISM_ARGS
    sei.nShow = 1   # SW_SHOWNORMAL — the DISM console shows its progress bar
    log(f"enabling the Windows '{FEATURE}' feature (UAC prompt): dism {DISM_ARGS}")
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        err = ctypes.get_last_error() or ctypes.windll.kernel32.GetLastError()
        if err == 1223:   # ERROR_CANCELLED
            raise RuntimeError("the admin prompt was declined — DirectPlay was not enabled.")
        raise RuntimeError(f"could not start DISM (error {err}).")
    ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, 0xFFFFFFFF)
    code = w.DWORD()
    ctypes.windll.kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(sei.hProcess)
    if code.value not in (0, 3010):
        raise RuntimeError(f"DISM exited with code {code.value} — DirectPlay was not enabled.")
    st = status()
    if code.value == 3010:
        log("DirectPlay enabled — Windows asks for a reboot before it takes effect.")
    else:
        log(f"DirectPlay: {describe(st)}")
    return st
