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

from ds2fix_core import __version__, tank, mods, exe_patch  # noqa: E402

# A pristine exe/tank, if present on this machine (dev only).
_PRISTINE_EXE = Path("/run/media/legion/4tb_btrfs/Games/ds2-gog/prefix/drive_c/Games/Dungeon Siege II/"
                     "DungeonSiege2.exe.ds2fix-pristine")


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


class TestMods(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
