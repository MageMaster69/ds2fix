# DS2Fix — status & roadmap

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
1. **Save-footprint bypass** *(deferred by choice — not blocking play)*. DS2 hides saves whose content
   footprint no longer matches the install, so re-patching or installing a mod hides existing saves until
   the footprint matches again. Disabling that check in the exe (like the tank-CRC bypass) makes saves
   **always** show and re-patching/mods safe — and lets the in-game version label update freely. Pick this
   up before leaning on the mod installer.
2. **Test normal co-op multiplayer** — host a game + join via **LAN** and **direct-IP** (the MP button is
   already unlocked; DS2 MP is peer-to-peer over DirectPlay8). *No dedicated server* — DS2 has no such
   concept (host-based P2P), so that idea is dropped.
3. **object_view content offset** — 3D models/map render low-and-left inside their frame at the 1920
   backbuffer (backbuffer-tied, not our canvas patch). Cosmetic. Deep viewport RE. Blocks #4.
4. **Map scale + center** — re-enable once #3 is solved (scaling renders but goes "out of line").
5. **Scale in-game panels** (inventory / character / spellbook / trade) — currently native/small; 2D parts
   scale cleanly, paperdoll shows the #3 offset.
6. **Re-test a newer DXVK** — if it renders the object_views, switch back for its performance.
7. **Windows end-to-end test** — patcher core is cross-platform; verify a real Windows run.

## ⛔ Won't do / N/A
- **#27 Aranna Legacy**, **#163 HD Cutscenes** — Broken World (v2.3) only; install is base DS2.
- **#119 Enhanced UI HD** — bundles Cristi80 Resolution Fix, which conflicts with our launch-param res.
- **Dedicated MP server** — DS2 MP is peer-to-peer/host-based; no dedicated server exists.
- **Pre-rendered cutscenes** stay 4:3 (engine limit; would need re-encoding the video files).

## The "done" line
The project **meets its goal today** — a fully playable, widescreen, fullscreen DS2 with working saves,
menus, map, and 3D models, plus optional HD-texture/storage mods (LAA-backed) and an uncapped framerate.
The last thing that turns "works" into "robust" is **#1 (save-footprint bypass)** — after that it's **v1.0**.
Everything else (#3–#7) is genuine optional polish.
