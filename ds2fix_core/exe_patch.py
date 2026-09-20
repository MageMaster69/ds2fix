#!/usr/bin/env python3
# DS2 exe patcher (importable core). Same logic as the original patch_dynamic.py, parameterised so the
# CLI/GUI can call it directly. Output is byte-identical to the script for the same options.
#
# Makes UIShell::SetScreenSize (FUN_0073be90) compute the canvas from the LIVE main-window rect
# (*(0xbcb28c))[0xb4-0xac, 0xb8-0xb0] instead of the passed (stale) args, plus CRC-disable, difficulty
# auto-unlock, non-resizable window, the version label, and (MENU_169) the native-16:9 menu patches.
import struct
try:
    from ._version import __version__            # imported as a package (normal)
except ImportError:
    from _version import __version__             # run directly as a script


def patch_exe(orig, dst=None, menu169=True, choke=True, ws169=True, res_w=1920, res_h=1080,
              version=None, log=print, borderless=False, dyncanvas=True, portrait=True,
              gridscale=True, ui_scale=None, openspy=True):
    """Patch a pristine DungeonSiege2.exe. `orig`/`dst` are file paths (dst optional -> returns bytes).
    Returns the patched bytes. Raises AssertionError if a patch site doesn't match (wrong/patched exe).
    `borderless`: give the game window a WS_POPUP (no caption/frame) style instead of the non-resizable
    captioned one — the Windows launcher's borderless-fullscreen mode (see PATCH WIN).
    `portrait`: fix the party-leader HUD portrait (see PATCH PORTRAIT; on by default).
    `gridscale`: inventory grids run at `ui_scale` (the panel UI scale; default res_h/720) via the engine's
    own UIGridbox::SetScale (see PATCH GRIDSCALE; on by default).
    `openspy`: point every GameSpy hostname at the community OpenSpy servers (see PATCH OPENSPY; on by
    default) so the Internet lobby works again.
    `dyncanvas=False` is a debug/bisect switch only."""
    MENU_169, CHOKE, WS169 = menu169, choke, ws169
    version = version or __version__
    with open(orig, 'rb') as _f:
        d = bytearray(_f.read())

    # ---- PATCH 0: menu version label "$MSG$Version - %S" -> "$MSG$ds2fix <version>" (idempotent).
    # Fixed slot: len("$MSG$ds2fix <version>") must be <= len("$MSG$Version - %S"); if the version is
    # too long for the menu, drop it to just "ds2fix" (the gameplay overlay still shows it in full).
    _vold = b'$MSG$Version - %S\x00'
    _label = f'ds2fix {version}'
    _vnew = b'$MSG$' + _label.encode('latin1') + b'\x00'
    if len(_vnew) > len(_vold):
        _label, _vnew = 'ds2fix', b'$MSG$ds2fix\x00'
    _vi = d.find(_vold)
    if _vi > 0:
        d[_vi:_vi+len(_vnew)] = _vnew
        for _k in range(len(_vnew), len(_vold)):
            d[_vi+_k] = 0
        log(f'OK: version label -> "{_label}"')
    elif d.find(b'$MSG$ds2fix') < 0:
        log('WARN: version string not found (already patched or exe differs)')

    # ---- PATCH CRC: disable the tank content-integrity check (enables all .gas data mods).
    _v1 = 0x699df1 - 0x400000
    if bytes(d[_v1:_v1+6]) == bytes([0x55,0x8b,0xec,0x83,0xec,0x10]):
        d[_v1:_v1+6] = bytes([0xb8,0x01,0x00,0x00,0x00,0xc3])   # mov eax,1 ; ret
        log('OK: content-integrity CRC verify disabled (FUN_00699df1 -> return 1)')
    elif bytes(d[_v1:_v1+2]) == bytes([0xb8,0x01]):
        log('OK: CRC verify already disabled')
    else:
        log(f'WARN: CRC-verify site unexpected ({bytes(d[_v1:_v1+2]).hex()}); skipped')
    _crc_fo = 0x6457d6 - 0x400000
    if d[_crc_fo] == 0x74 and d[_crc_fo+1] == 0x45:
        d[_crc_fo] = 0xeb
        log('OK: secondary CRC verify disabled (je -> jmp @0x6457d6)')

    # ---- PATCH SAVEFOOTPRINT: make saves ALWAYS list + load, regardless of content signature.
    # DS2 stamps every save's summary with a "content_crc" = a hash of the installed resource set at
    # save time. When enumerating the Single Player / Continue list AND when loading, it calls
    # IsContentCrcAcceptable (FUN_004139d0), which returns FALSE if the save's crc != the current
    # install's crc (and isn't in a tiny built-in whitelist) -> the save is SILENTLY HIDDEN from the
    # list and refused on load. Re-patching the UI tank or installing a data mod changes the resource
    # set -> changes the crc -> previously-fine saves vanish (the "disappear/reappear" bug). Force the
    # check to always accept (mov al,1 ; ret 4). Its ONLY two callers are the two save-summary readers
    # (list @0x41ee87, load @0x41c5a0); MP content-matching uses a separate path, so multiplayer is
    # unaffected. Reversible; idempotent.
    _sf_fo = 0x4139d0 - 0x400000
    if bytes(d[_sf_fo:_sf_fo+5]) == bytes([0x55,0x8b,0xec,0x8b,0x0d]):
        d[_sf_fo:_sf_fo+5] = bytes([0xb0,0x01,0xc2,0x04,0x00])   # mov al,1 ; ret 4
        log('OK: save content-footprint check bypassed (FUN_004139d0 -> accept; saves always list/load)')
    elif bytes(d[_sf_fo:_sf_fo+5]) == bytes([0xb0,0x01,0xc2,0x04,0x00]):
        log('OK: save content-footprint check already bypassed')
    else:
        log(f'WARN: save-footprint site unexpected ({bytes(d[_sf_fo:_sf_fo+5]).hex()}); skipped')

    # ---- PATCH UNLOCK: auto-unlock all campaign difficulties (FUN_004171d7 -> always completed).
    _unlock_fo = 0x417226 - 0x400000
    if bytes(d[_unlock_fo:_unlock_fo+2]) == bytes([0x8a,0xd8]):
        d[_unlock_fo:_unlock_fo+2] = bytes([0xb3,0x01])   # mov bl,1 (force "completed")
        log('OK: campaign difficulties auto-unlocked (FUN_004171d7 -> always completed; SP+MP)')
    elif bytes(d[_unlock_fo:_unlock_fo+2]) == bytes([0xb3,0x01]):
        log('OK: campaign difficulties already unlocked')
    else:
        log(f'WARN: unlock site unexpected ({bytes(d[_unlock_fo:_unlock_fo+2]).hex()}); skipped')

    # ---- PATCH WIN: window style. The top-level window style is the immediate in
    # `mov [ebp-4], 0x10ce0000` @0x5ebc42 (imm @0x5ebc45; WS_VISIBLE|WS_CAPTION|WS_SYSMENU|WS_THICKFRAME|
    # WS_MINIMIZEBOX) inside the style-builder the windowed CreateWindowExA (@0x5f226d) uses. Two modes:
    #  * default: non-resizable — drop WS_THICKFRAME (0xce -> 0xca @0x5ebc47). DS2 never rebuilds the
    #    swapchain on WM_SIZE, so dragging the border used to black it out. (Linux/Wine + gamescope path.)
    #  * borderless: WS_POPUP|WS_VISIBLE (0x90000000). No caption/frame, so AdjustWindowRect adds nothing
    #    and the client area == the render res exactly; launched `fullscreen=false` at the monitor's res
    #    this IS borderless fullscreen — clean alt-tab, no exclusive mode switch (which on native Windows
    #    also ran the whole frontend at 800x600, ignoring the MENU_169 patches). Windows launcher default.
    _win_imm = 0x5ebc45 - 0x400000
    _cur = bytes(d[_win_imm:_win_imm+4])
    if borderless:
        if _cur in (b'\x00\x00\xce\x10', b'\x00\x00\xca\x10'):
            d[_win_imm:_win_imm+4] = (0x90000000).to_bytes(4, 'little')
            log('OK: window made BORDERLESS (WS_POPUP|WS_VISIBLE @0x5ebc45) -> borderless fullscreen when res == monitor')
        elif _cur == b'\x00\x00\x00\x90':
            log('OK: window already borderless')
        else:
            log(f'WARN: window-style site unexpected ({_cur.hex()}); skipped')
    else:
        _win_fo = 0x5ebc47 - 0x400000
        if d[_win_fo] == 0xce:
            d[_win_fo] = 0xca
            log('OK: window made non-resizable (WS_THICKFRAME removed) -> no resize black-screen')
        elif d[_win_fo] == 0xca:
            log('OK: window already non-resizable')

    # ---- PATCH MPBTN: enable the Multiplayer button. UIFrontend::TransitionToMain (@0x44c2d3)
    # UNCONDITIONALLY calls UIButton::DisableButton on "button_multiplayer" every time the main menu
    # shows (GPG hard-disabled MP in the retail build). NOP that 5-byte call (@0x44c37a) so the button
    # stays enabled -> LAN + Internet(direct-IP) multiplayer become reachable. No GameSpy needed for those.
    _mp_fo = 0x44c37a - 0x400000
    if bytes(d[_mp_fo:_mp_fo+5]) == bytes([0xe8,0x31,0xa0,0x31,0x00]):
        d[_mp_fo:_mp_fo+5] = b'\x90\x90\x90\x90\x90'
        log('OK: Multiplayer button enabled (DisableButton NOP @0x44c37a)')
    elif bytes(d[_mp_fo:_mp_fo+5]) == bytes([0x90,0x90,0x90,0x90,0x90]):
        log('OK: Multiplayer button already enabled')
    else:
        log(f'WARN: MP-button site unexpected ({bytes(d[_mp_fo:_mp_fo+5]).hex()}); skipped')

    # ---- PATCH OPENSPY: GameSpy is dead (2014), so the Internet lobby ("Play anonymously over the Internet")
    # resolves peerchat.gamespy.com, fails and shows "Unable to connect". The community runs DS2 through
    # OpenSpy (openspy.net), a drop-in re-implementation of the GameSpy services (peerchat lobby, master
    # list, natneg, presence). The generic OpenSpy fix is to rewrite every "gamespy.com" hostname to
    # "openspy.net" -- same length, so a pure in-place string swap: peerchat.gamespy.com,
    # natneg1/2.gamespy.com, %s.master/available/ms%d.gamespy.com, gpcm/gpsp/gamestats.gamespy.com.
    # (The GameSpy-account button on the provider screen stays hidden by the tank edit; the anonymous
    # Internet mode needs no account.) Game traffic itself is DirectPlay8 -> the host still forwards ports.
    _gs, _os_ = b'gamespy.com', b'openspy.net'
    assert len(_gs) == len(_os_)
    _gsw, _osw = _gs.decode().encode('utf-16-le'), _os_.decode().encode('utf-16-le')   # motd/vercheck URLs
    if openspy:
        _n, _nw = d.count(_gs), d.count(_gsw)
        if _n:
            d = bytearray(bytes(d).replace(_gs, _os_).replace(_gsw, _osw))
            log(f'OK: GameSpy hostnames -> OpenSpy ({_n} x "gamespy.com" -> "openspy.net" + {_nw} wide; '
                f'Internet lobby revived)')
        elif d.count(_os_):
            log('OK: GameSpy hostnames already point at OpenSpy')
        else:
            log('WARN: no GameSpy hostname strings found; OpenSpy redirect skipped')

    # ---- PATCH PORTRAIT: party-leader (hero) HUD portrait. Stock DS2 bug ("black portrait above 1280 px
    # wide", DS2TroubleshootingGuide 4.1). A portrait is a 64x64 backbuffer pixel-grab taken after an
    # orthographic render of the character whose head lands at the VIEWPORT CENTRE at a fixed pixel size
    # (measured live on Windows 11 at 2560x1440: head centre ~(1284,725) frontend, ~(1300,722) in-game).
    # GPG authored the grab rect for 800x600 as {380,277}-{444,341} = viewport centre + (-20,-23) origin.
    #  * FRONTEND generator (RCGeneratePortrait -> FUN_00443480): the rect is HARD-CODED (imm32
    #    @0x4435ac/b3/ba/c1). With MENU_169 the frontend backbuffer is the game res -> the rect is far from
    #    the head -> black texture, persisted in the party file. Fix: origin = (W/2-20, H/2-23).
    #  * IN-GAME generator (FUN_004f25bb; used for the hero on every LOAD, since the saved Player portrait
    #    is reset at 0x82c0e7, and for hired companions): x = trunc(w*0.00125*380), y = trunc(h*0.0016667*277)
    #    scales the ORIGIN proportionally, so the rect drifts left/up of the head as the window grows
    #    (GPG's fudge table for 1280x1024/1024x768/640x480 hand-corrected exactly this). Fix: replace both
    #    fild/fmul/fmul/ftol blocks with (w>>1)-20 / (h>>1)-23 and jump over the fudges.
    _pt_sites = ((0x4435ac, 380), (0x4435b3, 277), (0x4435ba, 444), (0x4435c1, 341))
    _pt_cur = [bytes(d[a - 0x400000:a - 0x400000 + 4]) for a, _ in _pt_sites]
    _ig_x, _ig_y, _ig_j = 0x4f2af1 - 0x400000, 0x4f2b19 - 0x400000, 0x4f2b3e - 0x400000
    _ig_x_orig = bytes.fromhex('db 45 8c d8 0d 44 5e aa 00 d8 0d 40 5e aa 00 e8 17 7d 53 00')
    _ig_y_orig = bytes.fromhex('db 45 8c d8 0d 3c 5e aa 00 d8 0d 38 5e aa 00 e8 ef 7c 53 00')
    _ig_j_orig = bytes.fromhex('8b 96 b4 00 00 00')
    if portrait:
        _px, _py = int(res_w) // 2 - 20, int(res_h) // 2 - 23
        _rect = (_px, _py, _px + 64, _py + 64)
        if all(c == v.to_bytes(4, 'little') for c, (_, v) in zip(_pt_cur, _pt_sites)):
            for (a, _), v in zip(_pt_sites, _rect):
                d[a - 0x400000:a - 0x400000 + 4] = v.to_bytes(4, 'little')
            log(f"OK: leader portrait (frontend) grab rect 380,277,444,341 -> {','.join(map(str, _rect))} "
                f"(centred on the {res_w}x{res_h} frontend backbuffer; FUN_00443480 @0x4435ac)")
        else:
            log(f'WARN: leader-portrait frontend rect site unexpected ({b"".join(_pt_cur).hex()}); skipped')
        if (bytes(d[_ig_x:_ig_x+20]) == _ig_x_orig and bytes(d[_ig_y:_ig_y+20]) == _ig_y_orig
                and bytes(d[_ig_j:_ig_j+6]) == _ig_j_orig):
            # mov eax,[ebp-0x74] ; shr eax,1 ; sub eax,20|23 ; nop*12   (eax = x|y, as the ftol left it)
            d[_ig_x:_ig_x+20] = bytes.fromhex('8b 45 8c d1 e8 83 e8 14') + b'\x90' * 12
            d[_ig_y:_ig_y+20] = bytes.fromhex('8b 45 8c d1 e8 83 e8 17') + b'\x90' * 12
            d[_ig_j:_ig_j+6] = b'\xe9' + struct.pack('<i', 0x4f2be6 - (0x4f2b3e + 5)) + b'\x90'   # skip fudges
            log('OK: portrait (in-game) grab rect centred on the live window (FUN_004f25bb @0x4f2af1/0x4f2b19; fudges skipped)')
        elif bytes(d[_ig_x:_ig_x+8]) == bytes.fromhex('8b 45 8c d1 e8 83 e8 14'):
            log('OK: portrait (in-game) grab rect already centred')
        else:
            log(f'WARN: portrait in-game rect site unexpected ({bytes(d[_ig_x:_ig_x+8]).hex()}); skipped')

    # ---- parse PE headers ----
    pe = struct.unpack('<I', d[0x3c:0x40])[0]

    # ---- PATCH LAA: Large-Address-Aware. DS2 is a 32-bit exe capped at 2GB of address space; set
    # IMAGE_FILE_LARGE_ADDRESS_AWARE (0x0020) in the COFF Characteristics so it can use up to 4GB. This
    # matters once HD texture mods are installed (x4 upscales ~= 16x memory) — without it they OOM-crash
    # on larger areas. Pure PE-header bit; reversible; works under Wine on a 64-bit host too.
    _chr_fo = pe + 22
    _chars = struct.unpack('<H', d[_chr_fo:_chr_fo+2])[0]
    if not (_chars & 0x0020):
        struct.pack_into('<H', d, _chr_fo, _chars | 0x0020)
        log('OK: Large-Address-Aware enabled (2GB -> 4GB; for HD texture mods)')
    else:
        log('OK: already Large-Address-Aware')

    nsec = struct.unpack('<H', d[pe+6:pe+8])[0]
    optsz = struct.unpack('<H', d[pe+20:pe+22])[0]
    opt = pe + 24
    imgbase = struct.unpack('<I', d[opt+28:opt+32])[0]
    secalign = struct.unpack('<I', d[opt+32:opt+36])[0]
    filealign = struct.unpack('<I', d[opt+36:opt+40])[0]
    sizeofimg_off = opt + 56
    sectab = opt + optsz

    def align(v, a): return (v + a - 1) // a * a

    maxend_va = 0
    for i in range(nsec):
        o = sectab + i*40
        vsz, va, rsz, rptr = struct.unpack('<IIII', d[o+8:o+24])
        maxend_va = max(maxend_va, va + vsz)

    new_va = align(maxend_va, secalign)
    new_raw = align(len(d), filealign)
    new_rawsize = filealign
    new_vsize = 0x100
    S = imgbase + new_va

    def txt_fo(va): return va - imgbase   # .text: PointerToRawData==VirtualAddress==0x1000

    # ---- build the stub (placed at absolute VA S) ----
    def rel32(frm_end, to): return struct.pack('<i', to - frm_end)
    stub = bytearray()
    stub += bytes([0x8b,0x7d,0x08])                       # mov edi,[ebp+8]      (restore passed w)
    stub += bytes([0xa1,0x8c,0xb2,0xbc,0x00])             # mov eax, ds:0xbcb28c (window ptr)
    stub += bytes([0x85,0xc0])                            # test eax,eax
    stub += bytes([0x74,0x18])                            # jz .done (skip 24 bytes)
    stub += bytes([0x8b,0xb8,0xb4,0x00,0x00,0x00])        # mov edi,[eax+0xb4]  (right)
    stub += bytes([0x2b,0xb8,0xac,0x00,0x00,0x00])        # sub edi,[eax+0xac]  (-left = width)
    stub += bytes([0x8b,0x98,0xb8,0x00,0x00,0x00])        # mov ebx,[eax+0xb8]  (bottom)
    stub += bytes([0x2b,0x98,0xb0,0x00,0x00,0x00])        # sub ebx,[eax+0xb0]  (-top = height)
    back = 0x73be9e
    jmp_at = S + len(stub)
    stub += bytes([0xe9]) + rel32(jmp_at+5, back)
    assert len(stub) == 0x29, hex(len(stub))

    # ---- verify + apply the two in-place patches (from pristine bytes) ----
    assert bytes(d[txt_fo(0x73be9b):txt_fo(0x73be9b)+3]) == bytes([0x8b,0x7d,0x08]), "patch-site mismatch"
    assert all(b==0xCC for b in d[txt_fo(0x73bee4):txt_fo(0x73bee4)+12]), "cave not int3"
    if dyncanvas:
        d[txt_fo(0x73be9b):txt_fo(0x73be9b)+3] = bytes([0xEB,0x47,0x90])
        cave = 0x73bee4
        d[txt_fo(cave):txt_fo(cave)+5] = bytes([0xE9]) + rel32(cave+5, S)
        for k in range(5,12): d[txt_fo(cave)+k] = 0xCC
    else:   # debug/bisect: keep SetScreenSize stock (section still appended for the MENU_169 stub)
        log('WARN: [debug] dynamic UI canvas stub DISABLED (SetScreenSize left stock)')

    # ---- append the new section ----
    o = sectab + nsec*40
    d[o:o+8] = b'.ds2fix\x00'
    struct.pack_into('<IIII', d, o+8, new_vsize, new_va, new_rawsize, new_raw)
    struct.pack_into('<III', d, o+24, 0, 0, 0)
    struct.pack_into('<I', d, o+36, 0x60000020)            # CODE | EXECUTE | READ
    struct.pack_into('<H', d, pe+6, nsec+1)
    struct.pack_into('<I', d, sizeofimg_off, align(new_va+new_vsize, secalign))
    if len(d) < new_raw: d += b'\x00' * (new_raw - len(d))
    body = bytearray(stub) + b'\xCC' * (new_rawsize - len(stub))
    d[new_raw:new_raw+new_rawsize] = body

    # ---- PATCH GRIDSCALE: in-game inventory grids at the panel UI scale. ds2fix scales the character panel
    # .gas files (rects x1.5/x2), but a [t:gridbox]'s item icons, cell hit-testing and drag/drop are all
    # driven by the engine's OWN scale field (UIWindow+0x104, multiplied in everywhere: UIGridbox::Update
    # 0x779130 sizes an item as cells*32*scale). The engine even has the setter: UIGridbox::SetScale
    # (0x77b300, vtable slot 23) scales the rect about its top-left, the cell size and rebuilds the cell
    # table - and the game calls it with a literal 1.0 for every party member's inventory grid each time
    # the panel opens (0x49c57f loop: `fld1` @0x49c5a4). So: the tank keeps the gridbox cell size at 32 and
    # only moves its origin, and this patch feeds the panel UI scale into that call instead of 1.0
    # (constant at S+0xF0). Verified live: 48-px cells, a 1x2 dagger draws 48x96, drop/hover exact.
    _gs_site = 0x49c5a1
    _gs_orig = bytes.fromhex('8b 40 38 d9 e8 8b 88 d0 00 00 00 8b 01 51 d9 1c 24 ff 50 5c')
    _gs_cur = bytes(d[txt_fo(_gs_site):txt_fo(_gs_site)+20])
    if gridscale:
        _us = float(ui_scale) if ui_scale else round(int(res_h) / 720.0, 2)
        KS = S + 0xF0                  # the UI-scale float constant (shared with PATCH DRAGSCALE below)
        if _gs_cur == _gs_orig:
            S3 = S + 0x60
            st = bytearray()
            st += bytes([0x8b,0x40,0x38])                          # mov eax,[eax+0x38]
            st += bytes([0x8b,0x88,0xd0,0x00,0x00,0x00])           # mov ecx,[eax+0xd0]   (the member's gridbox)
            st += bytes([0x8b,0x01])                               # mov eax,[ecx]
            st += bytes([0x51])                                    # push ecx
            st += bytes([0xd9,0x05]) + struct.pack('<I', KS)       # fld dword [KS]        (panel UI scale)
            st += bytes([0xd9,0x1c,0x24])                          # fstp dword [esp]      (arg = scale)
            st += bytes([0xff,0x50,0x5c])                          # call [eax+0x5c]       UIGridbox::SetScale
            st += bytes([0xe9]) + rel32(S3 + len(st) + 5, _gs_site + 20)
            d[new_raw+0x60 : new_raw+0x60+len(st)] = st
            d[new_raw+0xF0 : new_raw+0xF4] = struct.pack('<f', _us)
            d[txt_fo(_gs_site):txt_fo(_gs_site)+20] = bytes([0xe9]) + rel32(_gs_site + 5, S3) + bytes([0x90]) * 15
            log(f"OK: inventory grids scaled x{_us:g} via UIGridbox::SetScale (call @0x49c5b2 -> stub @{S3:#x})")
        elif _gs_cur[0] == 0xe9:
            log('OK: inventory grid scale already patched')
        else:
            log(f'WARN: gridbox SetScale call site unexpected ({_gs_cur.hex()}); skipped')

        # ---- PATCH DRAGSCALE: the item icon carried on the cursor while dragging. The dragged icon IS the UIItem
        # window drawn at its own rect; UIItem::SetScale (vslot +0x5c) sets that rect to (texture native size x
        # scale). Two things left it at 1x with scaled grids: (a) items in equipment slots sit at scale 1.0, so a
        # slot pickup starts 1x; (b) UIGridbox's roll-off handler (msg 0xc @0x77dc57) resets every dragged item to
        # 1.0 when the cursor leaves a grid whose scale != 1.0 (dead code in stock DS2, live with GRIDSCALE).
        # Fix: (P1-P3) make that roll-off reset use the UI scale instead of 1.0; (stub) at UIItem::SetActive(true)
        # (0x781fd0, the common funnel for gridbox and itemslot pickups) size the item to native x UI scale right
        # before it is centred on the cursor. Verified live on Windows at 2560x1440 (A/B: 1x -> 2x). Over an
        # unscaled store/stash grid the grid's hover code still drops it to 1x to match those cells.
        _ds_site, _ds_back = 0x7820a2, 0x7820b3
        _ds_orig = bytes.fromhex('a1 d4 b2 bc 00 8b 88 94 00 00 00 8b 80 90 00 00 00 8b 16 51 50 8b ce ff 52 6c')
        _ds_cur = bytes(d[txt_fo(_ds_site):txt_fo(_ds_site)+len(_ds_orig)])
        _ds_pristine = (_ds_cur == _ds_orig
                        and bytes(d[txt_fo(0x77dccf):txt_fo(0x77dccf)+2]) == bytes.fromhex('74 66')
                        and bytes(d[txt_fo(0x77dcf8):txt_fo(0x77dcf8)+6]) == bytes.fromhex('d9 05 14 ec a8 00')
                        and bytes(d[txt_fo(0x77dd0b):txt_fo(0x77dd0b)+5]) == bytes.fromhex('68 00 00 80 3f'))
        if _ds_pristine:
            d[txt_fo(0x77dccf):txt_fo(0x77dccf)+2] = bytes.fromhex('90 90')                  # P3: no 'grid scale == 1.0 -> skip'
            struct.pack_into('<I', d, txt_fo(0x77dcfa), KS)                                 # P2: compare against KS, not 1.0
            struct.pack_into('<f', d, txt_fo(0x77dd0c), _us)                                # P1: SetScale(KS), not 1.0
            S4 = S + 0x90
            st4 = bytearray()
            st4 += bytes.fromhex('83 be a8 00 00 00 00')                 # cmp dword [esi+0xa8], 0   (texture loaded?)
            st4 += bytes([0x74, 0x00]); _jfix = len(st4) - 1             # je .skip
            st4 += bytes.fromhex('c7 86 cc 01 00 00 00 00 00 00')        # mov dword [esi+0x1cc], 0.0 (defeat SetScale's early-out)
            st4 += bytes.fromhex('68 00 00 80 3f 8b ce 8b 06 ff 50 5c')  # push 1.0; ecx=this; call [vt+0x5c]  -> rect = native
            st4 += bytes([0xff, 0x35]) + struct.pack('<I', KS)           # push dword [KS]
            st4 += bytes.fromhex('8b ce 8b 06 ff 50 5c')                 # call SetScale(KS)                 -> rect *= KS
            st4[_jfix] = len(st4) - (_jfix + 1)                          # .skip:
            st4 += _ds_orig[:17]                                         # the 17 displaced bytes (UIShell cursor x/y)
            st4 += bytes([0xe9]) + rel32(S4 + len(st4) + 5, _ds_back)
            assert S4 + len(st4) <= KS, "DRAGSCALE stub overlaps the KS constant"
            d[new_raw+0x90 : new_raw+0x90+len(st4)] = st4
            d[txt_fo(_ds_site):txt_fo(_ds_site)+17] = bytes([0xe9]) + rel32(_ds_site + 5, S4) + bytes([0x90]) * 12
            log(f"OK: dragged-item icon at x{_us:g} (UIItem::SetActive hook @0x7820a2 -> stub @{S4:#x}; grid roll-off keeps it)")
        elif _ds_cur[0] == 0xe9:
            log('OK: dragged-item icon scale already patched')
        else:
            log(f'WARN: DRAGSCALE site unexpected ({_ds_cur[:8].hex()}); skipped')

    if MENU_169:
        _rw = int(res_w); _rh = int(res_h)
        NEW_W = _rw.to_bytes(4, 'little'); NEW_H = _rh.to_bytes(4, 'little')
        OLD_W = (800).to_bytes(4, 'little');  OLD_H = (600).to_bytes(4, 'little')
        log(f"OK: [MENU_169] forced frontend resolution = {_rw}x{_rh}")
        _ws_sites = [(0x4231d8, 0x4231df), (0x424dd7, 0x424dde)] if WS169 else []
        for w_imm_va, h_imm_va in _ws_sites + [(0x5f12c2, 0x5f1316), (0x5f1372, 0x5f1382)]:
            assert bytes(d[txt_fo(w_imm_va):txt_fo(w_imm_va)+4]) == OLD_W, f"menu-w mismatch @{w_imm_va:#x}"
            assert bytes(d[txt_fo(h_imm_va):txt_fo(h_imm_va)+4]) == OLD_H, f"menu-h mismatch @{h_imm_va:#x}"
            d[txt_fo(w_imm_va):txt_fo(w_imm_va)+4] = NEW_W
            d[txt_fo(h_imm_va):txt_fo(h_imm_va)+4] = NEW_H
        if not WS169:
            log("OK: [WS169=0] WorldState logical size kept native 800x600 (@0x4231d8/0x424dd7)")

        if CHOKE:
            S2 = S + 0x30
            stub2 = bytearray()
            stub2 += bytes([0xc7,0x45,0xf8]) + NEW_W          # mov [ebp-0x8], 1920
            stub2 += bytes([0xc7,0x45,0xfc]) + NEW_H          # mov [ebp-0x4], 1080
            back2 = 0x5ebed7
            stub2 += bytes([0xe9]) + struct.pack('<i', back2 - (S2 + len(stub2) + 5))
            d[new_raw+0x30 : new_raw+0x30+len(stub2)] = stub2
            assert bytes(d[txt_fo(0x5ebed1):txt_fo(0x5ebed1)+6]) == bytes([0x89,0x4d,0xf8,0x89,0x45,0xfc]), "sizer store mismatch"
            d[txt_fo(0x5ebed1):txt_fo(0x5ebed1)+6] = bytes([0xe9]) + struct.pack('<i', S2 - (0x5ebed1+5)) + bytes([0x90])
            log(f"OK: [MENU_169] sizer choke-point forced {_rw}x{_rh} (FUN_005ebeba -> stub @{S2:#x})")

        for jne_va in (0x5f12f0, 0x5f1344):
            assert bytes(d[txt_fo(jne_va):txt_fo(jne_va)+2]) == bytes([0x75,0x0c]), f"jne mismatch @{jne_va:#x}"
            d[txt_fo(jne_va):txt_fo(jne_va)+2] = bytes([0x90,0x90])
        log(f"OK: [MENU_169] NOP'd config-read jne @0x5f12f0/0x5f1344 -> creation forced to fallback {_rw}x{_rh}")

        assert bytes(d[txt_fo(0x5f2220):txt_fo(0x5f2220)+6]) == bytes([0x8b,0x40,0x0c,0x2b,0x41,0x04]), "cwx-h mismatch"
        assert bytes(d[txt_fo(0x5f2233):txt_fo(0x5f2233)+5]) == bytes([0x8b,0x40,0x08,0x2b,0x01]), "cwx-w mismatch"
        d[txt_fo(0x5f2220):txt_fo(0x5f2220)+6] = bytes([0xb8]) + NEW_H + bytes([0x90])   # mov eax,1080 ; nop
        d[txt_fo(0x5f2233):txt_fo(0x5f2233)+5] = bytes([0xb8]) + NEW_W                   # mov eax,1920
        log(f"OK: [MENU_169] CreateWindowExA args forced to {_rw}x{_rh} (@0x5f2220/0x5f2233)")
        log(f"OK: [MENU_169] frontend/creation res 800x600 -> {_rw}x{_rh} at 4 sites")


    if dst is not None:
        open(dst, 'wb').write(d)
        log(f"OK: new section .ds2fix RVA={new_va:#x} VA={S:#x} raw={new_raw:#x}")
        log(f"    stub {len(stub)} bytes; cave jmp -> {S:#x}; SizeOfImage={align(new_va+new_vsize,secalign):#x}")
    return bytes(d)


if __name__ == '__main__':
    import sys, os
    _orig, _dst = sys.argv[1], sys.argv[2]
    patch_exe(_orig, _dst,
              menu169=os.environ.get('MENU_169', '1') != '0',
              choke=os.environ.get('CHOKE', '1') != '0',
              ws169=os.environ.get('WS169', '1') != '0',
              res_w=int(os.environ.get('RES_W', '1920')),
              res_h=int(os.environ.get('RES_H', '1080')),
              borderless=os.environ.get('BORDERLESS', '0') == '1',
              portrait=os.environ.get('PORTRAIT', '1') != '0',
              gridscale=os.environ.get('GRIDSCALE', '1') != '0',
              ui_scale=float(os.environ['DS2_UISCALE']) if os.environ.get('DS2_UISCALE') else None)
