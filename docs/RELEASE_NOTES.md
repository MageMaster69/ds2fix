**ds2fix** makes a legally-owned *Dungeon Siege II* (GOG v2.3) play like a modern game: widescreen HUD, native 16:9 menus scaled for your monitor, fullscreen that alt-tabs cleanly, every campaign difficulty unlocked, saves that never disappear, and (new) correctly scaled in-game panels and a working party-leader portrait. It patches your install in place, from a pristine backup, and **Restore** puts the original files back.

### Download

| Platform | Download | Run |
|---|---|---|
| Windows 10/11 | `ds2fix-gui_windows.exe` (GUI) or `ds2fix_windows.exe` (command line) | double-click the GUI, press **Patch + Play** |
| Linux (Wine/Proton, GOG or Heroic install) | `ds2fix-gui_linux` (GUI) or `ds2fix_linux` (command line) | `chmod +x ds2fix-gui_linux && ./ds2fix-gui_linux` |

No Python needed. The install is auto-detected (GOG/Steam registry on Windows; Wine prefixes, Steam and Heroic on Linux). Your saves are backed up before every patch.

### What's new since v0.1.7

- **Windows launcher** (v0.1.8): the game runs as a borderless window at your monitor's resolution, so alt-tab is clean and there is no exclusive-mode switch. Menus scale to match (1.5× at 1080p, 2× at 1440p). DPI-aware on high-scaling laptops.
- **Party-leader portrait fixed** (v0.1.9): stock DS2 shows the leader's HUD portrait black above 1280 px wide. Both of the game's portrait generators now grab the right pixels at any resolution. Existing parties heal on their next load.
- **In-game panels scaled** (v0.1.10): inventory, character, spell book and specialties panels are scaled with the menus, item grids included. Drag and drop, hover and re-equip all work at the scaled size, and the icon on the cursor while dragging is scaled too.
- **Journal map scaled** (v0.1.10): the Journal's cloth map (and the teleporter maps) now scale with the journal instead of staying small in the corner.
- **In-game dialogs scaled** (v0.1.11): the NPC conversation box, the Options menu and its tabs, tutorial tips, yes/no confirmations, defeat, save/load and quick-save dialogs are scaled like the menus (the engine centres them; ds2fix now scales them).
- **Reset Skill Points mod** (v0.1.12): `ds2fix mods install reset-skills` (or the GUI's Install… → Cancel) fetches the community respec mod, verifies it, and keeps ds2fix's HUD edits on top of it. Mods that replace files ds2fix edits are now rebuilt from a pristine copy on every patch, and multi-file mod zips ask you to `--pick` one.
- **DirectPlay check** (v0.1.13): DS2 multiplayer (LAN and direct-IP) runs on DirectPlay 8, which Windows 10/11 leave off; stock DS2 crashes on Host/Join if the Windows install prompt is skipped. ds2fix now reports it (`info`, `play`, GUI) and `ds2fix directplay --enable` / the GUI's **Enable DirectPlay (admin)…** button turns the feature on (one elevated DISM call, nothing else touched).
- **OpenSpy redirect** (v0.1.14): the Internet lobby used to die on `peerchat.gamespy.com` ("Unable to connect"). Every GameSpy hostname in the exe now points at the community OpenSpy servers, the standard fix DS2 players use. The lobby still needs the retail CD key in the registry, which GOG installs do not have; `ds2fix info` reports both the DirectPlay and CD-key state. Multiplayer hosting on Windows was verified with DirectPlay enabled (staging area, map and game settings); a LAN join has to be tested between two machines because two copies on one PC cannot see each other.
- **Mercenary by default in multiplayer** (v0.1.15): with every difficulty unlocked, a newly hosted room used to come up on the Elite world, which a fresh hero cannot start. New rooms now default to Mercenary; Veteran and Elite stay selectable in Map Settings (`DS2FIX_MPWORLD=0` restores the stock behaviour).
- **LAN joins between ds2fix installs** (v0.1.15): a real two-machine test (Windows host, Linux client) found the host's room in the LAN list, but the join was refused with "The game you are trying to join has been modified", because ds2fix's per-machine UI edits change the content id the client compares. That refusal is now skipped (`DS2FIX_MPCONTENT=0` restores it). Keep gameplay mods identical on both sides.
- Verified end to end on Windows 11 and on Linux/Wine.

### Uninstall

Press **Restore (uninstall)** in the GUI, or run `ds2fix restore`. The original exe and data are put back from the pristine backup. Saves are never touched.

### Known limits

- Store, stash, trade and pet panels are not scaled (deliberate, they stay consistent).
- Base *Dungeon Siege II* v2.3 only; *Broken World* is not supported yet.
