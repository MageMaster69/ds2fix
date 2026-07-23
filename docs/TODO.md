# DS2Fix — status & roadmap

## ✅ Done (v0.1.5)
- Widescreen HUD anchoring, native 16:9 menus, frontend + ESC-menu scaling, configurable UI scale/res.
- All campaign difficulties unlocked; data-mod support (content CRC disabled); non-resizable window;
  version label + in-game overlay; Multiplayer button re-enabled (LAN + direct-IP).
- **wined3d render fix** — DS2's 3D `object_view` viewports (Journal cloth map, character/inventory
  paperdoll, hero-creation preview) render correctly at widescreen. (DXVK blanks them; we force wined3d.)
  This overturned the long-standing "hero preview is an engine limit" belief — it was DXVK all along.
- gamescope no longer lingers after the game exits (supervised launcher).
- Save auto-backup + install pinning; cross-platform CLI + GUI + PyInstaller packaging.

## 🔴 To reach "done" (recommended)
1. **Save-footprint bypass** *(high value, small)* — DS2 stamps each save with a content "footprint" and
   HIDES saves whose footprint no longer matches the installed content, so **any re-patch/tank change
   hides your saves** (the "Thomas disappears/reappears" bug). Disable that check in the exe (same shape
   as the tank-CRC bypass we already do). Payoff: **saves always show, re-patching is safe, and the
   in-game version label can finally update** (updating it currently requires a re-patch → hides saves).
   This is the one thing that turns "works if you don't touch it" into "robust."

## 🟡 Optional polish (project is complete without these)
2. **Uncap framerate** — add `maxfps=120` (or `0`) to the launch args. One line, free.
3. **Scale in-game panels** (inventory / character / spellbook / trade / dialogue) — currently native/small
   in the top-left. The 2D-only ones scale cleanly; the ones with the paperdoll show the model offset (#4).
4. **object_view content offset** — 3D models/map render low-and-left inside their frame at the 1920
   backbuffer (ruled out our canvas patch; it's backbuffer-tied). Cosmetic. Deep viewport RE. Blocks #5.
5. **Map scale + center** — re-enable once #4 is solved (scaling now renders but goes "out of line").
6. **Re-test a newer DXVK** — if a current DXVK renders the object_views, switch back for its performance.
7. **Optional mod installer** — first-class installs for **#26 Storage Vault** and **#29 HD Textures**
   (both approved as good-to-go, non-bundled). Or leave as documented manual drops into `Resources/`.
8. **Windows end-to-end test** — patcher core is cross-platform; verify a real Windows run.

## ⛔ Won't do / N/A
- **#27 Aranna Legacy**, **#163 HD Cutscenes** — Broken World (v2.3) only; install is base DS2.
- **#119 Enhanced UI HD** — bundles Cristi80 Resolution Fix, which conflicts with our launch-param res.
- **Pre-rendered cutscenes** stay 4:3 (engine limit; would need re-encoding the video files).

## The "done" line
The project **meets its goal today** — a fully playable, widescreen, fullscreen DS2 with working saves,
menus, map, and 3D models. Do **#1 (save-footprint bypass)** and it becomes *robust* (saves never
fragile, safe to re-patch) → that's the natural **v1.0 / done** point. **#2** is a free bonus. Everything
else is genuinely optional and can be left as "someday."
