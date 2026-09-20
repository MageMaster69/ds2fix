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
    "reset-skills": {
        "id": 17,
        "title": "Reset Skill Points - hotbar button that refunds a character's skill points",
        "url": "https://www.nexusmods.com/dungeonsiegeii/mods/17",
        "globs": ["*reset*skill*", "mod-resetskills*"],
        # v3.09 (MrBoonie's update, the current Nexus main file) - also published by its author on GitHub, so
        # ds2fix can fetch it for you when no download is found. Same bytes either way: SHA512 enforced.
        "sha512": {"9dd22a2daca7874a652d459131fdc48d767df61d3135f110ebed3b23297d0aa0"
                   "0d7d740f2a33eecdb435d05dfbec4066268edb6b3355b197c5cc3e356bf55d59"},
        "direct": "https://raw.githubusercontent.com/iBoonie/DS2BW-ResetPoints/main/Mod-ResetSkills.ds2res",
        "note": "Replaces the HUD data bar file; ds2fix re-applies its version overlay to the mod's copy on every "
                "patch. The 30 Broken World skill names in the reset list are ignored by base DS2.",
    },
}
_ARCHIVE_EXTS = (".ds2res", ".zip")
ORIGINALS = ".ds2fix-mods"      # <gamedir>/.ds2fix-mods/<file>: pristine copy of each installed mod tank
DOWNLOADS = "downloads"         # <gamedir>/.ds2fix-mods/downloads/: files fetched via a registry `direct` URL


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


def _extract_ds2res(path, resdir, pick=None):
    """Place the mod's .ds2res file(s) into Resources/. Accepts a bare .ds2res or a .zip containing them.
    A zip with SEVERAL .ds2res (e.g. Storage Vault ships every vault size) needs `pick` - installing all of
    them at once would load conflicting variants."""
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
            if len(members) > 1:
                if not pick:
                    raise SystemExit(f"ds2fix: {path.name} contains {len(members)} .ds2res files - choose ONE with "
                                     f"--pick <name>:\n  " + "\n  ".join(Path(n).name for n in members))
                members = [n for n in members if Path(n).name.lower() == pick.lower()]
                if not members:
                    raise SystemExit(f"ds2fix: no '{pick}' inside {path.name}")
            for n in members:
                fn = Path(n).name
                (resdir / fn).write_bytes(z.read(n))
                out.append(fn)
    else:
        raise SystemExit(f"ds2fix: unsupported file '{path.name}' — extract the .ds2res and use --from it.")
    return out


def _download(gamedir, mod, log):
    """Fetch a mod that its author publishes at a direct (non-Nexus) URL. SHA512 is enforced by install()."""
    import urllib.request
    url = mod["direct"]
    dest = Path(gamedir) / ORIGINALS / DOWNLOADS / Path(url.split("?")[0]).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    log(f"  -> {dest} ({dest.stat().st_size} bytes)")
    return dest


def install(gamedir, name, src=None, force=False, log=print, pick=None):
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
        if cands:
            path = max(cands, key=lambda p: p.stat().st_mtime)   # newest matching file
            log(f"found download: {path}")
        elif mod.get("direct"):
            path = _download(gamedir, mod, log)
        else:
            raise SystemExit(
                f"ds2fix: no download found for '{name}' in your common folders.\n"
                f"  Download it from {mod['url']} (into ~/Downloads), then re-run — or pass --from <file>.")

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

    files = _extract_ds2res(path, gamedir / RESOURCES, pick=pick)
    orig = gamedir / ORIGINALS
    orig.mkdir(exist_ok=True)
    for fn in files:                                   # pristine copy, so `patch` can rebuild the mod tank
        shutil.copy2(gamedir / RESOURCES / fn, orig / fn)
    m = _load_manifest(gamedir)
    m[name] = {"id": mod["id"], "title": mod["title"], "files": files, "sha512": digest, "source": str(path)}
    _save_manifest(gamedir, m)
    log(f"installed '{name}': {', '.join(files)} -> Resources/")
    if mod.get("note"):
        log(f"  note: {mod['note']}")
    log("  (ds2fix's save-footprint bypass keeps your existing saves listed after a mod change; run")
    log("   `ds2fix patch` so the mod's files get ds2fix's own UI edits where they overlap.)")


def repatch(gamedir, edit, log=print):
    """Rebuild every installed mod tank from its pristine copy and run ds2fix's tank transform on it (`edit`
    = a callable taking the tank path). Mods that override a file ds2fix also edits (e.g. Reset Skill Points
    replaces the HUD data bar that carries the version overlay) otherwise silently drop those edits, because
    a USER-priority tank wins over Logic.ds2res. Idempotent: always starts from the pristine copy."""
    gamedir = Path(gamedir)
    m = _load_manifest(gamedir)
    for name, ent in m.items():
        for fn in ent.get("files", []):
            src, dst = gamedir / ORIGINALS / fn, gamedir / RESOURCES / fn
            if not src.is_file():
                log(f"mod '{name}': no pristine copy of {fn} (installed by an older ds2fix) — left as is")
                continue
            shutil.copy2(src, dst)
            log(f"mod '{name}': {fn} rebuilt from pristine, applying ds2fix UI edits ...")
            edit(str(dst))


def restore_originals(gamedir, log=print):
    """Put every installed mod tank back to its pristine (un-ds2fix-edited) copy."""
    gamedir = Path(gamedir)
    for name, ent in _load_manifest(gamedir).items():
        for fn in ent.get("files", []):
            src = gamedir / ORIGINALS / fn
            if src.is_file():
                shutil.copy2(src, gamedir / RESOURCES / fn)
                log(f"mod '{name}': {fn} restored to its pristine copy")


def remove(gamedir, name, log=print):
    gamedir = Path(gamedir)
    m = _load_manifest(gamedir)
    ent = m.get(name)
    if not ent:
        raise SystemExit(f"ds2fix: '{name}' is not installed.")
    resdir = gamedir / RESOURCES
    for fn in ent.get("files", []):
        for fp in (resdir / fn, gamedir / ORIGINALS / fn):
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
        log(f"                {mod['url']}" + ("   (auto-download available)" if mod.get("direct") else ""))
    if m:
        log("Installed files tracked in <gamedir>/.ds2fix-mods.json (remove with `ds2fix mods remove <name>`).")
