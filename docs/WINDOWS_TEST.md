# ds2fix — Windows end-to-end test checklist

Goal: verify ds2fix patches + launches Dungeon Siege II correctly on **native Windows** (the patcher
core is cross-platform; this confirms the Windows-specific paths — registry install detection, native
fullscreen launch, `%APPDATA%` config/save-backup — plus the one thing Wine can't tell us: whether the
**party leader's portrait** renders correctly on native D3D9).

## 0. Prerequisites
- A Windows 10/11 machine.
- Dungeon Siege II installed (GOG or Steam; base DS2, matching the Linux target). Note the folder that
  contains `DungeonSiege2.exe`.
- The build: download `ds2fix-windows-x64` from the **v0.1.7 GitHub Release**
  (https://github.com/twhalley/ds2fix/releases/tag/v0.1.7) — it contains `ds2fix.exe` (CLI) and
  `ds2fix-gui.exe` (GUI). No Python needed.

## 1. Detection (registry auto-detect)
```
ds2fix.exe detect
```
- [ ] Prints the correct game folder (the one with `DungeonSiege2.exe`).
- If it can't find it: `ds2fix.exe --gamedir "C:\GOG Games\Dungeon Siege II" detect` (or set
  `DS2_GAMEDIR`). Detection walks HKLM `GOG.com\Games`, Steam `libraryfolders.vdf`, then default folders.

## 2. State / info
```
ds2fix.exe info
```
- [ ] `exe: pristine/unpatched`, `platform: windows (native launch)`, and the `saves:` line points at
      `...\Documents\My Games\Dungeon Siege 2\Save`.

## 3. Patch (from pristine)
```
ds2fix.exe patch
```
- [ ] Backs up saves, writes `DungeonSiege2.exe.ds2fix-pristine` + `Logic.ds2res.ds2fix-pristine`,
      patches exe + tank, ends `patch complete.`
- [ ] `ds2fix.exe info` now shows `exe: PATCHED (ds2fix)`.
- [ ] Re-running `patch` is idempotent (rebuilds from pristine, never double-patches).

## 4. Launch + in-game verification
```
ds2fix.exe play
```
(`play` re-patches from pristine then launches native fullscreen at 1920x1080. Use
`ds2fix.exe play --res 2560x1440` to match your monitor, or `--no-patch` to launch only.)

Verify in-game:
- [ ] Launches **native fullscreen** (no gamescope/Wine involved).
- [ ] Main menu is **16:9** (not pillar-boxed 4:3) and the **Continue preview model** sits in its panel.
- [ ] **Multiplayer** button is enabled; in-game overlay reads `ds2fix 0.1.7`.
- [ ] **Saves list and load** (footprint bypass) — the Thomas/any existing party appears and loads.
- [ ] Journal → **Map** (cloth map) renders.
- [ ] ⭐ **Party leader portrait (member 1, top-left):** does the face render **correctly framed**, or is
      it low/offset with a green area above? On Wine it renders offset+green (an engine live-render/wined3d
      quirk); the hypothesis is native D3D9 renders it correctly. **Record the result** (screenshot) — this
      decides whether TODO #4 is a Wine-only issue or a real bug.

## 5. Saves safety + restore
- [ ] `ds2fix.exe info` lists at least one save backup (auto-made before the patch).
- [ ] `ds2fix.exe restore` reverts exe + tank to pristine; `info` shows `pristine/unpatched` again.

## 6. GUI smoke test
- [ ] `ds2fix-gui.exe` opens, detects the install, and its **Play** button launches the game.

## What to report back
- Any command that errors (copy the message).
- The member-1 portrait result (#4) — the key unknown.
- Anything that behaves differently from the Linux/Wine build.
