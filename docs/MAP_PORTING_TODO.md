# Map screens — resolution porting to-do

> **Status 2026-07-22:** Tier 1 + Tier 2 + Tier 3 are **coded and shipped** in `tank.py`
> (`MAP_PREFIXES`/`MAP_FILES`/`MAP_FILL_TARGETS`) and applied to the live install via `ds2fix patch`.
> Transform verified offline; the build launches, reaches gameplay, and the HUD/menus/difficulty all
> work. **The final map VISUAL is not yet confirmed in-game** — the agent can reach gameplay and
> screenshot, but cannot drive in-game clicks/hotkeys under KDE Wayland (DS2 gameplay uses DirectInput/
> raw input, which Wine doesn't receive from synthetic xdotool events; frontend menus use window
> messages, so those *were* drivable). Final check needs a human at the keyboard: open Journal → Map and
> confirm the cloth map renders bigger + centered (watch for the object_view actor-cull risk: base map
> should draw, town/character icons *might* not). If the viewport misbehaves, the fix is one flag away —
> flip `scale_object_view`/`fill_object_view` handling in `scale_center`.


The ds2fix widescreen work (dynamic UI canvas + `MENU_169`) makes the UI canvas track the live
backbuffer (1912×1046 in 16:9 gameplay). Every interface authored against the fixed **800×600**
canvas therefore renders at its raw 800-space coordinates — i.e. crammed into the **top-left ~42 %**
of the screen. Menus were fixed with the `scale_center` tank transform; the **map screens were never
ported**, which is why the Journal → Map view sits in a corner / is hard to see at widescreen.

This file tracks every `.gas` that renders a map and its porting status. Source of truth =
`ds2fix_core/tank.py`. Survey script: `scratchpad/mapscan.py`.

## The object_view crux

The real map screens draw the world through a **`[t:object_view]`** viewport (a live 3D/cloth scene),
not flat 2D widgets. From the hero-preview RE (`ds2-hero-preview-resfix`): at backbuffer > 800×600 the
object_view *scene* (the map itself) renders fine, but *actors* placed in it (character / location
icons) can get culled. The old "never touch an object_view rect" rule in `scale_center` was for the
**frontend hero preview**, and bug-1's root cause proved the party-list break is the `dir.lqd22`
**recompile of frontend interfaces**, not the rect edit. All map screens below are **backend**, so
editing + recompiling them is **party-list-safe**. Whether scaling the cloth-map viewport rect draws a
correctly-sized map (vs. breaking it) is the **one thing that must be verified in-game** before we
trust it — do the mapbook test first, then apply the same transform to the rest.

---

## Tier 1 — cloth-map object_view screens (scale chrome + viewport, then center)

These share the mapbook pattern: a book frame + a `map_view` object_view showing the cloth map of
Aranna with icons. Transform = the standard `scale_center` (scale ×1.5, center in 1912×1046),
**including** the object_view rect. Icons may or may not survive (actor cull); the base map is what
matters.

- [ ] `ui/interfaces/backend/journal/books/mapbook/mapbook.gas` — **Journal → Map tab (reported bug).**
      object_view `map_view` = `100,110,600,540`. skrit=yes, dir.lqd22=yes. **← verify here first.**
- [ ] `ui/interfaces/backend/teleport/teleport.gas` — teleporter destination map.
      object_view `teleport_map` = `355,106,742,490`. skrit=yes, dir.lqd22=yes.
- [ ] `ui/interfaces/backend/quest_teleporter/quest_teleporter.gas` — quest teleporter map.
      object_view `teleport_map` = `360,109,742,490`. skrit=yes, dir.lqd22=yes.

## Tier 2 — full-screen drawn map (M key) — needs STRETCH-to-fill, not center-scale

`map_view` here is authored at `0,0,800,600` (fills the whole canvas). Center-scaling by 1.5 would
leave it a 1200-wide box floating in the middle. Correct transform = **stretch `0,0,800,600` →
`0,0,1912,1046`** (map + overlay together). Separate code path from Tier 1.

- [ ] `ui/interfaces/backend/drawn_map/drawn_map.gas` — full-screen world map (M).
      object_view `map_view` = `0,0,800,600`. skrit=yes, dir.lqd22=yes.
- [ ] `ui/interfaces/backend/radar_overlay/radar_overlay.gas` — radar/map frame overlay drawn on top.
      map_gfx only (no object_view). dir.lqd22=yes. Must stretch to match drawn_map.

## Tier 3 — 2D map-image lore pages (trivial — pure texture rects, no object_view)

Flat texture rects only, so the plain `scale_center` handles them with no object_view risk. Low
priority (cosmetic lore/handbook entries), but cheap to include.

- [ ] `ui/interfaces/backend/journal/pages/page_map/page_map.gas` — lore/handbook "Map Details" image.
- [ ] `ui/interfaces/backend/journal/pages/page_map_2/page_map_2.gas` — variant of the above.

## Journal container (needed alongside Tier 1)

- [ ] `ui/interfaces/backend/journal/journal.gas` — the book frame + tab bar the map pages live inside.
      Must be scaled with the same transform so the tabs/frame line up with the scaled pages.
      skrit=yes, dir.lqd22=yes.

## Shared component to check

- [ ] `ui/interfaces/backend/cloth_map/cloth_map.gas` (2254 B, no object_view, no skrit) — the cloth-map
      template pulled in by `CreateClothMap`. Confirm it carries no rect that needs porting.

---

## Explicitly NOT maps (leave alone)

object_view here = character/monster **model previews**, and `WorldMap.*` = location-**name text**
lookups — neither renders a map:
`character_main_tab.gas`, `bestiary.gas`, `page_monsterdetails.gas`, `page_monsterstats.gas`
(model previews); `questbook.gas`, `page_questtasks.gas` (WorldMap name text only); the frontend
hero/party previews `main_menu/single_player/create_party/profile_party_*` (separate hero-preview
res gate — see `ds2-hero-preview-resfix`).
