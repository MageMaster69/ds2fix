#!/usr/bin/env python3
"""Optional, NON-BUNDLED DS2 mod installer.

DS2 auto-loads `.ds2res` tank files from the game's `Resources/` folder. We do not distribute any mod
(licensing / Nexus terms) — you download the mod yourself, and ds2fix: locates the downloaded file in your
common folders, **SHA512-verifies** it against a known-good registry, then copies the `.ds2res` into
`Resources/` and records it in a manifest (`<gamedir>/.ds2fix-mods.json`) for clean removal.

Mods persist across `ds2fix patch`/`restore` (those only rebuild the exe+tank from pristine); manage them
with `ds2fix mods install/remove`. NOTE: adding/removing a mod changes DS2's save "content footprint", so
existing saves may hide from the load list until the save-footprint bypass is enabled (see docs/TODO.md).
"""
import fnmatch
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path

RESOURCES = "Resources"
MANIFEST = ".ds2fix-mods.json"

# name -> metadata. `sha512` = set of known-good hashes of the DOWNLOADED file (archive or .ds2res); empty
# until a verified hash is recorded (then verification is enforced). `globs` locate the download by name.
REGISTRY = {
    "storage-vault": {
        "id": 26,
        "title": "Storage Vault — bigger stash + higher gold cap",
        "url": "https://www.nexusmods.com/dungeonsiegeii/mods/26",
        "globs": ["*storage*vault*", "*storagevault*"],
        "sha512": set(),   # TODO: add the verified download hash to enforce strict verification
    },
    "hd-textures": {
        "id": 29,
        "title": "HD Edition Textures AI Upscaled (x4) — needs LAA (on by default)",
        "url": "https://www.nexusmods.com/dungeonsiegeii/mods/29",
        "globs": ["*hd*edition*texture*", "*hd*texture*", "*ds2*hd*"],
        "sha512": set(),
    },
}
_ARCHIVE_EXTS = (".ds2res", ".zip")


def sha512(path, _bufsize=1 << 20):
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_bufsize), b""):
            h.update(chunk)
    return h.hexdigest()


def _common_dirs(gamedir):
    """Common places a download lands, de-duplicated. Includes the game's parent dir + Windows profile."""
    cands = [Path.home() / "Downloads", Path.home() / "Desktop", Path.home(), Path.cwd(), Path(gamedir).parent]
    up = os.environ.get("USERPROFILE")
    if up:
        cands += [Path(up) / "Downloads", Path(up) / "Desktop"]
    seen, out = set(), []
    for d in cands:
        try:
            rp = d.resolve()
        except OSError:
            continue
        if rp not in seen and rp.is_dir():
            seen.add(rp)
            out.append(rp)
    return out


def _find_candidates(gamedir, mod):
    """Files in common folders whose name matches the mod's globs and looks like a tank/archive."""
    hits = []
    for d in _common_dirs(gamedir):
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for f in entries:
            if not f.is_file():
                continue
            nl = f.name.lower()
            if nl.endswith(_ARCHIVE_EXTS) and any(fnmatch.fnmatch(nl, g) for g in mod["globs"]):
                hits.append(f)
    return hits


def _manifest_path(gamedir):
    return Path(gamedir) / MANIFEST


def _load_manifest(gamedir):
    p = _manifest_path(gamedir)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return {}
    return {}


def _save_manifest(gamedir, m):
    _manifest_path(gamedir).write_text(json.dumps(m, indent=2))


def installed_mods(gamedir):
    return _load_manifest(gamedir)


def _extract_ds2res(path, resdir):
    """Place the mod's .ds2res file(s) into Resources/. Accepts a bare .ds2res or a .zip containing them."""
    resdir.mkdir(exist_ok=True)
    out = []
    if path.suffix.lower() == ".ds2res":
        shutil.copy2(path, resdir / path.name)
        out.append(path.name)
    elif path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            members = [n for n in z.namelist() if n.lower().endswith(".ds2res")]
            if not members:
                raise SystemExit(f"ds2fix: no .ds2res inside {path.name}")
            for n in members:
                fn = Path(n).name
                (resdir / fn).write_bytes(z.read(n))
                out.append(fn)
    else:
        raise SystemExit(f"ds2fix: unsupported file '{path.name}' — extract the .ds2res and use --from it.")
    return out


def install(gamedir, name, src=None, force=False, log=print):
    gamedir = Path(gamedir)
    mod = REGISTRY.get(name)
    if not mod:
        raise SystemExit(f"ds2fix: unknown mod '{name}'. See `ds2fix mods list`.")

    if src:
        path = Path(src).expanduser()
        if not path.is_file():
            raise SystemExit(f"ds2fix: file not found: {path}")
    else:
        cands = _find_candidates(gamedir, mod)
        if not cands:
            raise SystemExit(
                f"ds2fix: no download found for '{name}' in your common folders.\n"
                f"  Download it from {mod['url']} (into ~/Downloads), then re-run — or pass --from <file>.")
        path = max(cands, key=lambda p: p.stat().st_mtime)   # newest matching file
        log(f"found download: {path}")

    digest = sha512(path)
    known = mod["sha512"]
    if known and digest in known:
        log("SHA512: verified (known-good).")
    elif known and not force:
        raise SystemExit(
            f"ds2fix: SHA512 does NOT match a known-good value for '{name}'.\n"
            f"  file: {path.name}\n  sha512: {digest}\n"
            f"  Re-download from {mod['url']}, or pass --force to install anyway.")
    else:
        log(f"SHA512: {digest}")
        log("  (no known-good hash on record — installing unverified; make sure it came from Nexus.)")

    files = _extract_ds2res(path, gamedir / RESOURCES)
    m = _load_manifest(gamedir)
    m[name] = {"id": mod["id"], "title": mod["title"], "files": files, "sha512": digest, "source": str(path)}
    _save_manifest(gamedir, m)
    log(f"installed '{name}': {', '.join(files)} -> Resources/")
    log("NOTE: adding a mod changes DS2's save content-footprint — existing saves may hide from the load")
    log("  list until the save-footprint bypass is enabled (docs/TODO.md). Saves on disk are never lost.")


def remove(gamedir, name, log=print):
    gamedir = Path(gamedir)
    m = _load_manifest(gamedir)
    ent = m.get(name)
    if not ent:
        raise SystemExit(f"ds2fix: '{name}' is not installed.")
    resdir = gamedir / RESOURCES
    for fn in ent.get("files", []):
        fp = resdir / fn
        if fp.exists():
            fp.unlink()
            log(f"removed Resources/{fn}")
    del m[name]
    _save_manifest(gamedir, m)
    log(f"uninstalled '{name}'.")


def print_list(gamedir, log=print):
    m = _load_manifest(gamedir)
    log("Optional mods — download from Nexus, then `ds2fix mods install <name>`:")
    for name, mod in REGISTRY.items():
        state = "INSTALLED" if name in m else "not installed"
        log(f"  {name:13} [{state:13}] #{mod['id']}  {mod['title']}")
        log(f"                {mod['url']}")
    if m:
        log("Installed files tracked in <gamedir>/.ds2fix-mods.json (remove with `ds2fix mods remove <name>`).")
