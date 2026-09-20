#!/usr/bin/env python3
"""ds2fix unit tests (stdlib unittest — no external deps).

Run: python -m unittest discover -s tests   (or  python tests/test_ds2fix.py)

Game-file-independent tests always run. The exe/tank tests run only if a pristine DungeonSiege2 install is
reachable (dev machine); otherwise they're skipped, so CI stays green without shipping copyrighted files.
"""
import io
import os
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ds2fix_core import __version__, tank, mods, exe_patch, directplay  # noqa: E402

# A pristine exe, if present on this machine (dev only): $DS2_PRISTINE_EXE, the Linux dev path, or the
# pinned/auto-detected install's `.ds2fix-pristine` backup (Windows dev box). Never shipped/committed.
def _find_pristine_exe():
    cands = [Path(os.environ["DS2_PRISTINE_EXE"])] if os.environ.get("DS2_PRISTINE_EXE") else []
    cands.append(Path("/run/media/legion/4tb_btrfs/Games/ds2-gog/prefix/drive_c/Games/Dungeon Siege II/"
                      "DungeonSiege2.exe.ds2fix-pristine"))
    try:
        import ds2fix
        gd = ds2fix.detect_gamedir(None, pin=False)
        cands.append(ds2fix.pristine_paths(gd)[0])
    except (SystemExit, Exception):  # noqa: BLE001 — no install here: fine, tests skip
        pass
    return next((c for c in cands if c.is_file()), cands[-1])


_PRISTINE_EXE = _find_pristine_exe()


class TestVersion(unittest.TestCase):
    def test_version_is_short_enough_for_menu_slot(self):
        # the in-game menu label lives in a fixed 17-char slot: "ds2fix <version>" must fit.
        self.assertLessEqual(len(f"ds2fix {__version__}"), 17, "version too long for the exe menu-label slot")

    def test_version_nonempty(self):
        self.assertRegex(__version__, r"^\d+\.\d+")


class TestTankTransform(unittest.TestCase):
    def test_scale_center_scales_and_centers(self):
        out = tank.scale_center(b"[t:window,n:w]\nrect = 100,110,600,540;\n", 1.5)
        self.assertIn(b"rect = 506,238,1256,883", out)

    def test_object_view_verbatim_by_default(self):
        # frontend preview viewport must stay untouched unless scale_object_view is set
        src = b"[t:object_view,n:hero]\nrect = 100,110,600,540;\n"
        self.assertIn(b"rect = 100,110,600,540", tank.scale_center(src, 1.5))
        self.assertIn(b"rect = 506,238,1256,883",
                      tank.scale_center(src, 1.5, scale_object_view=True))

    def test_fill_object_view_stretches(self):
        src = b"[t:object_view,n:map_view]\nrect = 0,0,800,600;\n"
        out = tank.scale_center(src, 1.5, scale_object_view=True, fill_object_view=True)
        self.assertIn(b"rect = 0,0,%d,%d" % (tank.CW, tank.CH), out)

    def test_canvas_param_centres_into_given_client_size(self):
        # Windows borderless 2560x1440: 800x600 @2.0 = 1600x1200 -> centred at (480,120)
        src = b"[t:window,n:w]\nrect = 0,0,800,600;\n"
        self.assertIn(b"rect = 480,120,2080,1320", tank.scale_center(src, 2.0, canvas=(2560, 1440)))
        # default canvas is unchanged (Linux 1912x1046 client of a captioned 1920x1080 window)
        self.assertEqual(tank.scale_center(src, 1.5), tank.scale_center(src, 1.5, canvas=(1912, 1046)))
        # the version-label override anchors to the canvas' right edge
        lab = b"[t:text,n:text_version]\nrect = 1,576,284,599;\n"
        self.assertIn(b"rect = 2238,12,2548,40", tank.scale_center(lab, 2.0, canvas=(2560, 1440)))
        self.assertIn(b"rect = 1590,12,1900,40", tank.scale_center(lab, 1.5))
        # fill stretches to the given canvas
        mv = b"[t:object_view,n:map_view]\nrect = 0,0,800,600;\n"
        self.assertIn(b"rect = 0,0,2560,1440",
                      tank.scale_center(mv, 2.0, scale_object_view=True, fill_object_view=True, canvas=(2560, 1440)))

    def test_scale_panel_scales_rects_and_pixel_fields_about_top_left(self):
        src = (b"[t:text,n:t]\n{\n\t  i max_width = 87;\n\t  i draw_order = 101;\n\trect = 10,20,110,120;\n}\n")
        out = tank.scale_panel(src, 2.0)
        self.assertIn(b"rect = 20,40,220,240", out)           # top-left origin, not centred
        self.assertIn(b"i max_width = 174;", out)
        self.assertIn(b"i draw_order = 101;", out)            # non-pixel ints untouched

    def test_dialogue_box_is_a_panel_target(self):
        self.assertIn('ui/interfaces/backend/dialogue_box/dialogue_box.gas', tank.PANEL_TARGETS)
        src = b"[t:dialog_box,n:dialog_box_main_bg]" + b"\n{\n\t\trect = 236,21,788,249;\n}\n"
        self.assertIn(b"rect = 472,42,1576,498", tank.scale_panel(src, 2.0))

    def test_centered_dialog_detection(self):
        NL, TAB = b"\n", b"\t"
        self.assertTrue(tank.is_centered_dialog(b"[t:interface,n:options]" + NL + b"{" + NL + TAB + b"centered = background;" + NL))
        self.assertTrue(tank.is_centered_dialog(TAB + b"centered" + TAB + b"= dialog_box_bg;" + b"\r" + NL))
        self.assertFalse(tank.is_centered_dialog(TAB + b"justify = center;" + NL + TAB + b"  b center_height = true;" + NL))
        self.assertFalse(tank.is_centered_dialog(b"// centered = old;" + NL))

    def test_scale_gridbox_scales_rect_not_cells(self):
        src = (b"[t:gridbox,n:g]\n{\n\t  i border_padding = 10;\n\t  f box_height = 32.000000;\n"
               b"\t  f box_width = 32.000000;\n\t  i columns = 5;\n\t\trect = 366,132,526,548;\n\t  i rows = 13;\n}\n")
        out = tank.scale_gridbox(src, 1.5)
        self.assertIn(b"rect = 549,198,789,822", out)         # whole rect x1.5 about the origin
        self.assertIn(b"f box_width = 32.000000;", out)       # cell size untouched (engine scales it)
        self.assertIn(b"i border_padding = 10;", out)

    def test_tab_aligned_rect_is_scaled(self):
        # mapbook.gas / drawn_map.gas write `rect<tabs>= ...;` -- must scale like `rect = ...;`
        src = b'[t:object_view,n:map_view]\n\t\trect\t\t\t\t= 100,110,600,540;\n'
        out = tank.scale_center(src, 2.0, scale_object_view=True, canvas=(2560, 1440))
        self.assertIn(b'rect = 680,340,1680,1200', out)
        fill = tank.scale_center(b'[t:object_view,n:map_view]\n\trect\t= 0,0,800,600;\n', 2.0,
                                 scale_object_view=True, fill_object_view=True, canvas=(2560, 1440))
        self.assertIn(b'rect = 0,0,2560,1440', fill)

    def test_is_map_target(self):
        self.assertTrue(tank._is_map_target("ui/interfaces/backend/journal/books/mapbook/mapbook.gas"))
        self.assertTrue(tank._is_map_target("ui/interfaces/backend/teleport/teleport.gas"))
        self.assertFalse(tank._is_map_target("ui/interfaces/frontend/main_menu/main_menu.gas"))

    def test_overlay_insert_idempotent(self):
        u = b"[data_bar]\n{\n\t[t:button,n:button_collect_loot_bg]\n\t{}\n}\n"
        once = tank.insert_overlay(u, "0.1.5")
        self.assertIn(b"text_ds2fix", once)
        self.assertIn(b"ds2fix 0.1.5", once)
        self.assertEqual(once, tank.insert_overlay(once, "0.1.5"))   # second call is a no-op


class TestDirectPlay(unittest.TestCase):
    def test_stub_detection(self):
        with tempfile.TemporaryDirectory() as d:
            stub = Path(d) / "dpnet.dll"
            stub.write_bytes(b"MZ" + b"\0" * 512 + "DirectPlay Stub".encode("utf-16-le") + b"\0" * 64)
            self.assertTrue(directplay.is_stub(stub))
            real = Path(d) / "dpnet_real.dll"
            real.write_bytes(b"MZ" + b"\0" * (directplay.STUB_MAX + 1024))   # big, no marker
            self.assertFalse(directplay.is_stub(real))
            small = Path(d) / "dpnet_small.dll"
            small.write_bytes(b"MZ" + b"\0" * 512)                        # small but not the FoD stub
            self.assertFalse(directplay.is_stub(small))
            self.assertFalse(directplay.is_stub(Path(d) / "missing.dll"))

    def test_status_and_describe(self):
        st = directplay.status()
        if os.name == "nt":
            self.assertIn(st, ("enabled", "stub", "missing"))
        else:
            self.assertEqual(st, "n/a")
        self.assertTrue(directplay.describe("enabled").startswith("enabled"))
        self.assertIn("directplay --enable", directplay.describe("stub"))
        self.assertIn("Legacy Components", directplay.describe("missing"))

    def test_cli_has_directplay_command(self):
        import ds2fix
        a = ds2fix.build_parser().parse_args(["directplay", "--enable"])
        self.assertEqual(a.cmd, "directplay"); self.assertTrue(a.enable)
        self.assertFalse(ds2fix.build_parser().parse_args(["directplay"]).enable)


class TestLauncherDefaults(unittest.TestCase):
    def test_auto_scale_and_canvas(self):
        import ds2fix
        self.assertEqual(ds2fix.auto_scale(1080), 1.5)
        self.assertEqual(ds2fix.auto_scale(1440), 2.0)
        self.assertEqual(ds2fix.auto_scale(720), 1.0)
        self.assertEqual(ds2fix.canvas_for(1920, 1080, borderless=False), (1912, 1046))   # Linux legacy
        self.assertEqual(ds2fix.canvas_for(2560, 1440, borderless=True), (2560, 1440))    # Windows

    def test_play_command_windows_is_borderless_windowed(self):
        import ds2fix
        if not ds2fix.IS_WINDOWS:
            self.skipTest("Windows launch path")
        cmd, env, note = ds2fix.play_command(Path("C:/game"), 2560, 1440, 2560, 1440, False)
        self.assertIn("fullscreen=false", cmd)
        self.assertIn("width=2560", cmd)
        self.assertIn("highdpiaware", env.get("__COMPAT_LAYER", "").lower())
        self.assertIn("borderless", note)


def _build_tank(entries, dbase=0x324):
    """Minimal DSg2Tank writer mirroring what tank.parse() reads: header (dirset/fileset/data offsets), a dir
    tree, one FileEntry per file with a single zlib chunk, data right after the header and the index AFTER the
    data (the real layout: Logic.ds2res and Tank-Creator mods alike). Enough for parse/_read_file/edit_tank."""
    dirs = [""]
    for p in entries:
        parts = p.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            dp = "/".join(parts[:i])
            if dp not in dirs:
                dirs.append(dp)
    ds = bytearray(struct.pack("<I", len(dirs)) + b"\0" * 4 * len(dirs)); dir_eo = {}
    for i, dp in enumerate(dirs):
        eo = len(ds); dir_eo[dp] = eo; struct.pack_into("<I", ds, 4 + 4 * i, eo)
        name = dp.split("/")[-1].encode() if dp else b""
        parent = 0 if not dp else dir_eo["/".join(dp.split("/")[:-1])]
        ds += struct.pack("<I", parent) + b"\0" * 12 + struct.pack("<H", len(name)) + name + b"\0"
        while len(ds) % 4:
            ds += b"\0"
    data = bytearray(); fs = bytearray(struct.pack("<I", len(entries)) + b"\0" * 4 * len(entries))
    for i, (p, content) in enumerate(entries.items()):
        eo = len(fs); struct.pack_into("<I", fs, 4 + 4 * i, eo)
        name = p.split("/")[-1].encode(); parent = dir_eo["/".join(p.split("/")[:-1])]
        c = zlib.compress(content, 9); dataoff = len(data); data += c
        fs += struct.pack("<IIII", parent, len(content), dataoff, zlib.crc32(content) & 0xffffffff) + b"\0" * 12
        fs += struct.pack("<H", len(name)) + name + b"\0"
        while len(fs) % 4:
            fs += b"\0"
        fs += struct.pack("<II", len(c), tank.BLK) + struct.pack("<4I", len(content), len(c), 0, 0)
    while len(data) % 4:                       # keep the index 4-aligned (parse aligns chunk tables absolutely)
        data += b"\0"
    hdr = bytearray(dbase); hdr[0:8] = b"DSg2Tank"; struct.pack_into("<I", hdr, 8, 0x00010100)
    ds_off = dbase + len(data); fs_off = ds_off + len(ds)
    struct.pack_into("<III", hdr, 0x0c, ds_off, fs_off, len(ds) + len(fs)); struct.pack_into("<I", hdr, 0x18, dbase)
    return bytes(hdr) + bytes(data) + bytes(ds) + bytes(fs)


class TestTankIO(unittest.TestCase):
    """Round-trip through a Tank-Creator-style tank (data offset 0x324, index after the data)."""
    DATA_BAR = b"[data_bar]\n{\n\t[t:button,n:button_collect_loot_bg]\n\t{\n\t\trect = 153,567,185,599;\n\t}\n}\n"

    def test_parse_reads_data_offset_from_header_and_roundtrips(self):
        blob = _build_tank({"ui/interfaces/backend/data_bar/data_bar.gas": self.DATA_BAR, "config/x.gas": b"[x]{}\n"})
        files, offs = tank.parse(bytearray(blob))
        self.assertEqual(set(files), {"ui/interfaces/backend/data_bar/data_bar.gas", "config/x.gas"})
        self.assertEqual(files["config/x.gas"]["dbase"], 0x324)
        self.assertEqual(tank._read_file(bytearray(blob), files, "ui/interfaces/backend/data_bar/data_bar.gas"),
                         self.DATA_BAR)

    def test_edit_tank_on_mod_tank_injects_overlay_without_clobbering_the_index(self):
        blob = _build_tank({"ui/interfaces/backend/data_bar/data_bar.gas": self.DATA_BAR * 40})   # > slack
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Mod-Test.ds2res"; p.write_bytes(blob)
            logs = []
            tank.edit_tank(str(p), scale=2.0, backup=False, canvas=(2560, 1440), version="9.9", log=logs.append)
            d = bytearray(p.read_bytes()); files, _ = tank.parse(d)          # index still readable
            u = tank._read_file(d, files, "ui/interfaces/backend/data_bar/data_bar.gas")
            self.assertIn(b"text_ds2fix", u); self.assertIn(b"ds2fix 9.9", u)
            self.assertTrue(any("relocated" in m for m in logs), logs)   # grew past its slot -> appended
            self.assertFalse(any("SKIP" in m for m in logs), logs)       # no noise for absent targets


class TestMods(unittest.TestCase):
    def test_registry_reset_skills_entry(self):
        import fnmatch
        m = mods.REGISTRY["reset-skills"]
        self.assertTrue(any(fnmatch.fnmatch("mod-resetskills.ds2res", g) for g in m["globs"]))
        self.assertEqual(len(next(iter(m["sha512"]))), 128)
        self.assertTrue(m["direct"].startswith("https://raw.githubusercontent.com/"))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.game = Path(self.tmp.name) / "game"
        (self.game / "Resources").mkdir(parents=True)
        self.dl = Path(self.tmp.name) / "dl"
        self.dl.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _fake_ds2res(self, name="hd.ds2res", body=b"DSg2Tank fake payload"):
        p = self.dl / name
        p.write_bytes(body)
        return p

    def test_install_and_remove_ds2res(self):
        src = self._fake_ds2res()
        logs = []
        mods.install(self.game, "hd-textures", src=str(src), log=logs.append)
        self.assertTrue((self.game / "Resources" / "hd.ds2res").exists())
        self.assertIn("hd-textures", mods.installed_mods(self.game))
        mods.remove(self.game, "hd-textures", log=logs.append)
        self.assertFalse((self.game / "Resources" / "hd.ds2res").exists())
        self.assertNotIn("hd-textures", mods.installed_mods(self.game))

    def test_install_from_zip(self):
        z = self.dl / "hd_pack.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("readme.txt", "hi")
            zf.writestr("HD_Textures.ds2res", b"DSg2Tank")
        mods.install(self.game, "hd-textures", src=str(z), log=lambda m: None)
        self.assertTrue((self.game / "Resources" / "HD_Textures.ds2res").exists())

    def test_unknown_mod_errors(self):
        with self.assertRaises(SystemExit):
            mods.install(self.game, "does-not-exist", src=str(self._fake_ds2res()), log=lambda m: None)

    def test_sha512_mismatch_blocks_without_force(self):
        mods.REGISTRY["hd-textures"]["sha512"] = {"0" * 128}
        try:
            with self.assertRaises(SystemExit):
                mods.install(self.game, "hd-textures", src=str(self._fake_ds2res()), log=lambda m: None)
            # --force overrides
            mods.install(self.game, "hd-textures", src=str(self._fake_ds2res()), force=True, log=lambda m: None)
            self.assertIn("hd-textures", mods.installed_mods(self.game))
        finally:
            mods.REGISTRY["hd-textures"]["sha512"] = set()

    def test_sha512_matches_installs(self):
        src = self._fake_ds2res(body=b"known-good bytes")
        good = mods.sha512(src)
        mods.REGISTRY["storage-vault"]["sha512"] = {good}
        try:
            mods.install(self.game, "storage-vault", src=str(src), log=lambda m: None)
            self.assertIn("storage-vault", mods.installed_mods(self.game))
        finally:
            mods.REGISTRY["storage-vault"]["sha512"] = set()


@unittest.skipUnless(_PRISTINE_EXE.exists(), "pristine DungeonSiege2.exe not available")
class TestExePatch(unittest.TestCase):
    def test_patch_sets_laa_and_is_detectable_and_idempotent(self):
        patched = exe_patch.patch_exe(str(_PRISTINE_EXE), None, log=lambda m: None)
        pe = struct.unpack("<I", patched[0x3c:0x40])[0]
        chars = struct.unpack("<H", patched[pe + 22:pe + 24])[0]
        self.assertTrue(chars & 0x0020, "LAA bit not set")
        self.assertIn(b".ds2fix\x00", bytes(patched))   # ds2fix section marker => detectable as patched
        # re-patching the pristine input must be byte-stable
        again = exe_patch.patch_exe(str(_PRISTINE_EXE), None, log=lambda m: None)
        self.assertEqual(bytes(patched), bytes(again))

    def test_window_style_captioned_vs_borderless(self):
        fo = 0x5ebc45 - 0x400000
        pristine = _PRISTINE_EXE.read_bytes()
        self.assertEqual(pristine[fo:fo + 4], (0x10ce0000).to_bytes(4, "little"), "pristine style imm changed")
        captioned = exe_patch.patch_exe(str(_PRISTINE_EXE), None, log=lambda m: None)
        self.assertEqual(captioned[fo:fo + 4], (0x10ca0000).to_bytes(4, "little"), "THICKFRAME not dropped")
        borderless = exe_patch.patch_exe(str(_PRISTINE_EXE), None, borderless=True, log=lambda m: None)
        self.assertEqual(borderless[fo:fo + 4], (0x90000000).to_bytes(4, "little"), "WS_POPUP not applied")
        # the two variants differ ONLY in that one style immediate
        diff = [i for i, (a, b) in enumerate(zip(captioned, borderless)) if a != b]
        self.assertTrue(diff and all(fo <= i < fo + 4 for i in diff), f"unexpected extra diffs: {diff[:8]}")

    def test_leader_portrait_rects_centred(self):
        sites = (0x4435ac, 0x4435b3, 0x4435ba, 0x4435c1)
        rd = lambda b, va: int.from_bytes(b[va - 0x400000:va - 0x400000 + 4], 'little')
        pristine = _PRISTINE_EXE.read_bytes()
        self.assertEqual([rd(pristine, s) for s in sites], [380, 277, 444, 341])
        p = exe_patch.patch_exe(str(_PRISTINE_EXE), None, res_w=2560, res_h=1440, log=lambda m: None)
        self.assertEqual([rd(p, s) for s in sites], [1260, 697, 1324, 761])          # frontend: W/2-20, H/2-23
        p = exe_patch.patch_exe(str(_PRISTINE_EXE), None, res_w=1920, res_h=1080, log=lambda m: None)
        self.assertEqual([rd(p, s) for s in sites], [940, 517, 1004, 581])
        # in-game generator: x = (w>>1)-20, y = (h>>1)-23, fudge table skipped
        self.assertEqual(p[0xf2af1:0xf2af1 + 8], bytes.fromhex('8b 45 8c d1 e8 83 e8 14'))
        self.assertEqual(p[0xf2b19:0xf2b19 + 8], bytes.fromhex('8b 45 8c d1 e8 83 e8 17'))
        self.assertEqual(p[0xf2b3e:0xf2b3e + 6], b'\xe9' + (0x4f2be6 - 0x4f2b43).to_bytes(4, 'little', signed=True) + b'\x90')
        p = exe_patch.patch_exe(str(_PRISTINE_EXE), None, portrait=False, log=lambda m: None)
        self.assertEqual([rd(p, s) for s in sites], [380, 277, 444, 341])          # opt-out leaves stock
        self.assertEqual(p[0xf2af1:0xf2af1 + 3], bytes.fromhex('db 45 8c'))
        fo = 0x443629 - 0x400000                                                 # SetPortrait untouched
        self.assertEqual(p[fo - 1:fo + 6], bytes.fromhex('53 57 e8 c2 32 3e 00'))

    def test_inventory_grid_setscale_patched(self):
        fo = 0x49c5a1 - 0x400000
        pristine = _PRISTINE_EXE.read_bytes()
        self.assertEqual(pristine[fo:fo + 20], bytes.fromhex('8b4038d9e88b88d00000008b0151d91c24ff505c'))
        p = exe_patch.patch_exe(str(_PRISTINE_EXE), None, res_w=2560, res_h=1440, ui_scale=2.0, log=lambda m: None)
        self.assertEqual(p[fo], 0xe9)                                             # jmp stub
        self.assertEqual(p[fo + 5:fo + 20], bytes([0x90]) * 15)
        self.assertEqual(p[0x7d50f0:0x7d50f4], struct.pack('<f', 2.0))           # scale constant
        p = exe_patch.patch_exe(str(_PRISTINE_EXE), None, res_w=1920, res_h=1080, log=lambda m: None)
        self.assertEqual(p[0x7d50f0:0x7d50f4], struct.pack('<f', 1.5))           # default = height/720
        p = exe_patch.patch_exe(str(_PRISTINE_EXE), None, gridscale=False, log=lambda m: None)
        self.assertEqual(p[fo:fo + 20], pristine[fo:fo + 20])                     # opt-out

    def test_dragscale_hook_and_rolloff_patch(self):
        pristine = _PRISTINE_EXE.read_bytes()
        fo = lambda va: va - 0x400000
        self.assertEqual(pristine[fo(0x7820a2):fo(0x7820a2) + 5], bytes.fromhex('a1 d4 b2 bc 00'))
        self.assertEqual(pristine[fo(0x77dccf):fo(0x77dccf) + 2], bytes.fromhex('74 66'))
        p = exe_patch.patch_exe(str(_PRISTINE_EXE), None, res_h=1440, log=lambda m: None)
        self.assertEqual(p[fo(0x7820a2)], 0xe9)                                       # hook installed
        self.assertEqual(p[fo(0x77dccf):fo(0x77dccf) + 2], bytes.fromhex('90 90'))     # P3
        self.assertEqual(struct.unpack('<f', p[fo(0x77dd0c):fo(0x77dd0c) + 4])[0], 2.0)   # P1 = UI scale @1440p
        p = exe_patch.patch_exe(str(_PRISTINE_EXE), None, gridscale=False, log=lambda m: None)
        self.assertEqual(p[fo(0x7820a2):fo(0x7820a2) + 5], bytes.fromhex('a1 d4 b2 bc 00'))   # off with gridscale
        self.assertEqual(p[fo(0x77dccf):fo(0x77dccf) + 2], bytes.fromhex('74 66'))

    def test_save_footprint_check_bypassed(self):
        # IsContentCrcAcceptable (FUN_004139d0) must be forced to "mov al,1 ; ret 4" so saves always
        # list/load regardless of the install's content signature.
        pristine = bytearray(_PRISTINE_EXE.read_bytes())
        fo = 0x4139d0 - 0x400000
        self.assertEqual(bytes(pristine[fo:fo + 5]), bytes([0x55, 0x8b, 0xec, 0x8b, 0x0d]),
                         "pristine save-footprint site changed — RE stale")
        patched = exe_patch.patch_exe(str(_PRISTINE_EXE), None, log=lambda m: None)
        self.assertEqual(bytes(patched[fo:fo + 5]), bytes([0xb0, 0x01, 0xc2, 0x04, 0x00]),
                         "save-footprint check not bypassed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
