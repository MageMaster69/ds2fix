# DS2Fix — status & roadmap

## ✅ Done (v0.1.9)
- **Party-leader portrait fixed** (stock DS2 bug above 1280 px wide): both portrait generators now grab a
  rect centred on the viewport (see #4 below for the full mechanism). Verified on Windows 11 / D3D9.

## ✅ Done (v0.1.8)
- **Windows native launcher**: borderless window at the monitor res (the gamescope role), DPI-aware, menus
  scaled/centred for any resolution, monitor-res + auto UI-scale defaults; Windows end-to-end verified.

## ✅ Done (v0.1.7)
- **Save content-footprint bypass** — the v1.0 blocker, solved. DS2 stamps every save with a `content_crc`
  (a hash of the installed resource set) and silently HIDES + refuses saves whose crc no longer matches the
  install; re-patching the tank or installing a data mod changes the crc, so existing saves would "disappear/
  reappear". `IsContentCrcAcceptable` (FUN_004139d0) is now forced to always accept (both the list-summary and
  load-summary readers go through it; MP content-matching is a separate path, untouched). **Proven live:** the
  Thomas party listed *and* loaded into gameplay after a real footprint change (tank crc `8a7b6adb`→`e67d647d`)
  that would otherwise have hidden it.
- **Frontend 3D preview models now render in their panels** (object_view offset, was problem #3). The
  main-menu Continue party model and the Single-Player hero-select paperdoll used to draw at the native
  800×600 top-left corner while their panels scaled to 1920; the viewport rect is now scaled with the panel
  so the model sits on its pedestal. Unblocked by two earlier fixes: wined3d (scaling no longer blanks it) and
  the footprint bypass (the frontend `dir.lqd22` recompile no longer hides the party list). Verified live on
  the main menu + Choose-Hero screen.

## ✅ Done (v0.1.6)
- Widescreen HUD anchoring, native 16:9 menus, frontend + ESC-menu scaling, configurable UI scale/res.
- All campaign difficulties unlocked; data-mod support (content CRC disabled); non-resizable window;
  version label + in-game overlay; Multiplayer button re-enabled (LAN + direct-IP).
- **wined3d render fix** — DS2's 3D `object_view` viewports (Journal cloth map, character/inventory
  paperdoll, hero-creation preview) render correctly at widescreen. (DXVK blanks them; we force wined3d.)
- gamescope no longer lingers after the game exits (supervised launcher).
- **Large-Address-Aware (2GB→4GB)** — PE-header bit, so HD-texture mods don't OOM-crash.
- **Uncapped framerate** — `maxfps` launch arg (default 120; `--maxfps 0` = uncapped).
- **Optional mod installer** — `ds2fix mods list/install/remove` + GUI section; non-bundled, SHA512-verified,
  finds the download in common folders, tracks installs for clean removal. Registered: #26 Storage Vault,
  #29 HD Textures.
- Save auto-backup + install pinning; cross-platform CLI + GUI + PyInstaller packaging; unit tests (`tests/`).

## 🟡 Open / optional
1. **Test normal co-op multiplayer** — host a game + join via **LAN** and **direct-IP** (the MP button is
   already unlocked; DS2 MP is peer-to-peer over DirectPlay8). *No dedicated server* — DS2 has no such
   concept (host-based P2P), so that idea is dropped.
2. **Re-enable the Journal → Map cloth-map scaling** — now that frontend object_view scaling is proven to
   work on wined3d, re-test the backend map targets (currently commented out in `_target_list`) and confirm
   the cloth map scales cleanly (the "out of line" symptom was the same object_view offset just fixed).
3. **Scale in-game panels** (inventory / character / spellbook / trade) — *investigated 2026-07-23.* The
   panels render at native 800×600 size, anchored top-left (functional, just small). They live in
   `character_awp.gas` (204 KB) + `character_*_tab.gas` + `gold_trade.gas`, all currently excluded from
   `_target_list` (the `in_game`/`panel` filter). Scaling is NOT the clean win it is for menus: the item
   **grid cells are fixed-size** (item icons are fixed-pixel textures the engine draws), so scaling the panel
   rect enlarges the frame but the icon grid won't follow — the classic DS2 in-game-UI-scaling wall. Needs a
   grid-aware transform, not a blanket rect scale. (Good news for testing: xdotool `i`/`j` keys DO reach
   gameplay, so panels can be driven + screenshotted.)
4. **Party leader (hero) portrait blank / mis-framed** — **FIXED in v0.1.9** (exe patch, both generators).
   Root cause, established with a runtime tracer on Windows 11 (D3D9): a portrait is a 64x64 backbuffer
   pixel-grab taken after an orthographic render of the character, and the head lands at the **viewport
   centre** at a fixed pixel size. GPG authored the grab rect for 800x600 as `{380,277}-{444,341}`
   (= viewport centre + (-20,-23)). The frontend generator (`FUN_00443480`) hard-codes it; the in-game
   generator (`FUN_004f25bb`) scales the *origin* proportionally (`0.475*w`, `0.4617*h`) so the rect drifts
   left/up of the head as the window grows (GPG's fudge table for 1280x1024 / 1024x768 / 640x480 hand-
   corrected exactly that drift). Above ~1280 wide the rect no longer overlaps the head → black (D3D9) /
   partial (Wine). It hits the hero specifically because the saved Player portrait is reset on load
   (`0x82c0e7`) and the hero is regenerated in-game every load; companions use template portraits.
   Fix (`exe_patch.py` PATCH PORTRAIT): frontend rect = `(W/2-20, H/2-23)` + 64 for the frontend res;
   in-game x/y = `(w>>1)-20` / `(h>>1)-23` from the live window rect, fudges skipped. Verified at 2560x1440:
   new hero correct in play, after in-game save + reload, and the persisted portrait file is correct.
   Existing parties are healed on their next load (the load path regenerates the hero anyway).
   Linux/Wine: same patch applies; re-verify the head lands at the viewport centre under wined3d.
5. **DXVK for performance** — *re-tested 2026-07-23: DXVK v2.7.1 renders the `object_view` viewports
   correctly* (the old blank-viewport bug was specific to v2.6.2). Verified: main-menu preview, journal, and
   gameplay all render under DXVK v2.7.1 (from `GE-Proton10-34/.../dxvk/i386-windows/d3d9.dll`). The launcher
   now supports it as an **opt-in** (`DS2_RENDERER=dxvk`, or just drop a DXVK `d3d9.dll` into the game dir);
   wined3d stays the default. To promote DXVK to default, first re-verify the **cloth Map tab** under DXVK
   (the one screen not yet checked — it was the original v2.6.2 casualty).
6. **Windows end-to-end test** — *done 2026-09-11/12 on Windows 11 (GOG, Intel UHD 620, 2560x1440 @200%):*
   detection, patch/restore/idempotence, borderless launch at 1440p + centred 1080p, 16:9 menus scaled
   (1.5×/2×), previews, MP button, overlay, save list/load, gameplay HUD — all OK. Results in
   `docs/WINDOWS_TEST.md`. Not yet checked on Windows: Journal→Map, the GUI end-to-end, 4:3 modes.
7. **Gamescope fullscreen present flake** — on KDE Wayland `ds2fix play` intermittently hits "Compositor
   released us but we were not acquired" and the game bounces (teardown is clean, no lingering). Windowed
   launch is the reliable path meanwhile. Investigate gamescope flags / a windowed-fullscreen fallback.

## ⛔ Won't do / N/A
- **#27 Aranna Legacy**, **#163 HD Cutscenes** — Broken World (v2.3) only; install is base DS2.
- **#119 Enhanced UI HD** — bundles Cristi80 Resolution Fix, which conflicts with our launch-param res.
- **Dedicated MP server** — DS2 MP is peer-to-peer/host-based; no dedicated server exists.
- **Pre-rendered cutscenes** stay 4:3 (engine limit; would need re-encoding the video files).

## The "done" line
**v1.0 reached.** The two things that stood between "works" and "robust" — the save content-footprint bypass
and the frontend 3D preview offset — are both fixed and verified live. DS2 is fully playable and widescreen:
working + always-visible saves (re-patch/mod safe), native 16:9 menus with correctly-placed preview models,
journal map, LAA-backed HD-texture/storage mods, and an uncapped framerate. Everything left (#1–#5) is
optional polish or verification — nothing blocks a v1.0 tag.
