# ds2fix — Windows end-to-end test checklist

Goal: verify ds2fix patches + launches Dungeon Siege II correctly on **native Windows** (the patcher
core is cross-platform; this confirms the Windows-specific paths — registry install detection, the
borderless-window launch, `%APPDATA%` config/save-backup — plus the one thing Wine can't tell us: whether the
**party leader's portrait** renders correctly on native D3D9).

> **Run 2026-09-11/12** — Windows 11 Pro 26200, GOG DS2 v2.3 in `C:\GOG Games\Dungeon Siege 2`, Intel UHD 620,
> 2560x1440 at 200% display scaling. First pass with ds2fix 0.1.8 from source; **repeated 2026-09-13 with the
> released v0.1.9 binaries** and again **2026-09-14 with the released v0.1.10 binaries** (`ds2fix_windows.exe` /
> `ds2fix-gui_windows.exe` downloaded from the GitHub Release: detect, restore, info, patch, idempotent re-patch,
> `play` into gameplay with the scaled dragged-item icon, GUI Patch + Play and Restore) — every ✅ below holds for
> the release build. Results are marked ✅ / ❌ / ⬜ (not run) below.

## 0. Prerequisites
- A Windows 10/11 machine.
- Dungeon Siege II installed (GOG or Steam; base DS2, matching the Linux target). Note the folder that
  contains `DungeonSiege2.exe`.
- The build: download `ds2fix_windows.exe` (CLI) and `ds2fix-gui_windows.exe` (GUI) from the latest **GitHub Release**
  (https://github.com/twhalley/ds2fix/releases). No Python needed.

## 1. Detection (registry auto-detect)
```
ds2fix.exe detect
```
- [x] ✅ Prints the correct game folder (the one with `DungeonSiege2.exe`) — found via the GOG registry key.
- If it can't find it: `ds2fix.exe --gamedir "C:\GOG Games\Dungeon Siege II" detect` (or set
  `DS2_GAMEDIR`). Detection walks HKLM `GOG.com\Games`, Steam `libraryfolders.vdf`, then default folders.

## 2. State / info
```
ds2fix.exe info
```
- [x] ✅ `exe: pristine/unpatched`, `platform: windows (borderless window, native D3D9)`, a `display:` line
      with the monitor res, and `saves:` at `...\Documents\My Games\Dungeon Siege 2\Save` (once the game has
      created it — a never-run install shows `(save folder not found)`).

## 3. Patch (from pristine)
```
ds2fix.exe patch
```
- [x] ✅ Backs up saves, writes `DungeonSiege2.exe.ds2fix-pristine` + `Logic.ds2res.ds2fix-pristine`,
      patches exe + tank, ends `patch complete.` (every exe patch site matched the GOG Windows exe).
- [x] ✅ `ds2fix.exe info` now shows `exe: PATCHED (ds2fix)`.
- [x] ✅ Re-running `patch` is idempotent (rebuilds from pristine, never double-patches) — identical exe MD5
      across repeated runs of the release binary.

## 4. Launch + in-game verification
```
ds2fix.exe play
```
(`play` re-patches from pristine then launches a **borderless window at your monitor's resolution** —
borderless fullscreen, clean alt-tab. `--res 1920x1080` renders smaller, centred; `--no-patch` launches only.
Exclusive `fullscreen=true` is deliberately NOT used: on native Windows it ran the whole frontend at 800x600.)

Verify in-game:
- [x] ✅ Launches as a **borderless window at (0,0), client == render res** (2560x1440 and 1920x1080 tested;
      1080p is centred on the 1440p monitor). DPI-aware (no bitmap scaling at 200%).
- [x] ✅ Main menu is **16:9**, scaled 2× at 1440p / 1.5× at 1080p and centred; the **Continue preview model**
      and the create-hero paperdoll sit in their panels; all three difficulties selectable.
- [x] ✅ **Multiplayer** button is enabled; in-game overlay reads `ds2fix 0.1.8`.
- [x] ✅ **Saves list and load** — a party created in one run appears and loads in the next.
- [x] ✅ Journal → **Map** (cloth map) **scales with the journal** at 1440p (v0.1.10: the tab-aligned `rect`
      fix); compass and travel log aligned. (There is no full-screen world-map key in retail DS2 — the
      `toggle_cloth_map` binding is commented out in `config/input_bindings.gas` — so nothing to drive there.)
- [x] ✅ A party created BEFORE the v0.1.9 portrait fix ("Tester") shows the correct leader portrait after
      loading with the fixed build: the hero's portrait is regenerated on load, old saves need no re-creation.
- [x] ✅ 4:3 mode: `--res 1440x1080` → borderless window centred on the 1440p monitor, menus 1.5×, gameplay + inventory OK.
- [x] ✅ **In-game panels** (v0.1.10): inventory / character / spell book / specialties scaled 1.5× (1080p) and
      2× (1440p); item grid cells, icons and the icon carried on the cursor scale; drag from an equipment slot into the grid, move between cells
      and re-equip all work (verified with synthetic input at both resolutions).
- [x] ✅ **Play session** (v0.1.11, 2560x1440): tutorial beach — NPC conversations (Captain Ogrank, Lt. Jerind)
      in the 2x-scaled dialogue box with portraits/replies aligned; quest log updates; ESC menu, Options + all four
      tabs scaled 2x and centred, Cancel; Save Game writes the party file; save + reload mid-map; camera rotate/zoom;
      ground-click movement across the camp and over the tower; quest-marker NPC (Jerind) advances the quest and
      opens the gate; **combat**: right-click a training dummy → it breaks, loot drops, `Z` collects it into the
      scaled inventory grid; three-option NPC dialogue trees; bow equipped by dragging it from the scaled grid
      onto the ranged slot (stat deltas shown), ranged attack on the archery target (arrows fly and stick);
      location banner, task/handbook notifications and tutorial-tip pop-ups (scaled) render.
      Note for drivers: alt-tabbing into DS2 pauses it ("Game Paused" banner); Space / Pause toggles.
- [x] ✅ ⭐ **Party leader portrait (member 1):** was black on native D3D9 at 1920x1080 and 2560x1440 in
      v0.1.8 (the stock DS2 "black portrait above 1280 wide" bug, not Wine). **Fixed in v0.1.9** — verified
      for a new hero in play, after an in-game save + reload, and the saved party file. Mechanism and patch
      in `docs/TODO.md` item 4.

## 5. Saves safety + restore
- [x] ✅ `ds2fix.exe info` lists save backups once a Save folder exists (auto-made before each patch).
- [x] ✅ `ds2fix.exe restore` reverts exe + tank to pristine; `info` shows `pristine/unpatched` again.

## 6. GUI smoke test
- [x] ✅ `ds2fix-gui_windows.exe` (release build) opens, auto-detects the install and shows its patch state; defaults
      are the monitor res (2560x1440) and `auto` UI scale. **Patch + Play** re-patches, launches the borderless
      window and places it at (0,0); the log pane shows the patch output and "window placed". **Restore (uninstall)**
      reverts to pristine (confirmed with `ds2fix_windows.exe info`).

## 7. Optional mods
- [x] ✅ `ds2fix_windows.exe mods list` shows the registry; `mods install reset-skills` with no download present
      auto-fetches the file from the author's GitHub, SHA512 matches the pinned hash, copies it to `Resources/`
      and a pristine copy to `.ds2fix-mods/`; `info` lists it; `patch` rebuilds the mod tank and re-injects the
      version overlay into the mod's `data_bar.gas`.
- [x] ✅ In-game with the mod: the overlay label still reads `ds2fix <version>`; the reset button sits on the
      hotbar (bottom-right), its tooltip reads "LEFT-CLICK to unassign all skill points", clicking it opens the
      Specialties tab, reports "Number of unassigned skill points" and refunds the points. No crash on base DS2.
- [x] ✅ `mods remove reset-skills` deletes the tank and the pristine copy, empties the manifest; `patch` runs
      clean without it; re-install works.
- [ ] ⬜ Storage Vault / HD Textures: need a Nexus login to download — not exercised.

## 8. LAN / direct-IP multiplayer (two instances on one PC)
Setup: `ds2fix_windows.exe patch --res 1280x720`, then start two copies of the game with the launch arg
`multi=true` (skips DS2's single-instance mutex; `ds2-scratch/twoinst.py` launches both 1280x720 windows side by
side). Run 2026-09-20, ds2fix 0.1.12 from source.
- [x] ✅ Main menu → Multiplayer → Local Network → nickname: both instances reach the LAN lobby ("Guest has
      joined the portal"), see each other under **Room**; the lobby, chat, Party Selection and the notice dialogs
      render correctly at 1280x720 / scale 1.
- [x] ✅ **Party Creation** (multiplayer hero): name, race/gender/appearance/hair, Accept → the hero is listed with
      its portrait top-left (the MP portrait renders, like the single-player one since v0.1.9).
- [x] ✅ **Game List → Host Game** dialog (name, password, Classic / Couples / Party mode) renders correctly.
- [ ] ❌ **Host Game → OK with DirectPlay off:** Windows pops *"An app on your PC needs the following Windows
      feature: DirectPlay"*. Choosing *Skip this installation* makes DS2 **crash** (access violation in
      `Flick::FlickManager::RSCreateAndLaunchServerSequence`, NULL `DirectPlay8Server` — see
      `Documents\My Games\Dungeon Siege 2\Logs\DungeonSiege2.crash`). That is stock DS2 on Windows 10/11, where
      DirectPlay is a disabled legacy feature and `SysWOW64\dpnet.dll` is a 10 KB "DirectPlay Stub" — not a
      ds2fix regression. **v0.1.13** detects the stub (`info` → `directplay: NOT enabled`, `play` prints a note,
      the GUI shows a warning line) and `ds2fix directplay --enable` / the GUI's **Enable DirectPlay (admin)…**
      button turns the feature on through an elevated DISM call.
- [x] ✅ **With DirectPlay enabled** (2026-09-20, second pass): Host Game → OK now works — the host lands in the
      **Staging Area** (room LANTEST, party row, chat log, Map Settings with the difficulty list, Game Settings,
      Party Details) and every one of those screens renders correctly. Note: the world defaults to **Elite**
      (highest unlocked, a side effect of the difficulty unlock) — hosts should pick Mercenary in Map Settings.
- [ ] ❌ **Two copies on ONE PC cannot complete a LAN game.** The guest's Game List stays "No games available"
      after Refresh / Find Games (the guest does broadcast the GameSpy QR2 echo to UDP 6500-6600; the host never
      answers its 6500 socket), and the host's **Start** button does nothing. Both instances share the GameSpy
      peer port UDP 13139 with SO_REUSEADDR, so one of them never receives the peer unicast replies — a
      single-machine artefact, not a ds2fix bug. **Needs two machines** (e.g. host on this Windows box, join from
      the Linux box): Multiplayer → No (firewall prompt) / Yes for real LAN → Local Network → nickname → Choose
      Party → Game List; host: Host Game → name → OK → Map Settings: Mercenary → Start; guest: Refresh → select
      the room → Join Game; then check the staging screen and the in-game HUD on both.
- [x] ✅ **Internet mode** (v0.1.14): stock DS2's "Internet" option is the GameSpy peer lobby; it resolved
      `peerchat.gamespy.com`, failed, and showed "Unable to connect". With the new OpenSpy patch (every
      `gamespy.com` string → `openspy.net`) the DNS step passes and the lobby moves on to the CD-key check.
- [ ] ❌ **CD key:** the Internet lobby then says "Could not find a valid CDKey. You will require a valid CDKey
      to play online." The exe reads registry value `PID` under `HKLM\Software\Microsoft\Microsoft Games\DungeonSiege2` (WOW6432Node view). GOG's installer writes no such key (retail/Steam do), so the GOG build
      cannot enter the Internet lobby as shipped; `ds2fix info` now reports `cd key : not in the registry`.
      Not a ds2fix regression; there is no direct-IP path outside that lobby (the LAN Join Game button needs a
      listed room).

## What to report back
- Any command that errors (copy the message).
- The member-1 portrait result (#4) — the key unknown.
- Anything that behaves differently from the Linux/Wine build.
