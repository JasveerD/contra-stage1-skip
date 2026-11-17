"""Clean bottomless-pit fall with a one-frame $CEEC misread shortly before the fall death.
No values forced after the drop; logs what is drawn for the player after the respawn."""
import sys
from emu import NES
from exp2 import traverse
from sim_misread import Glitchy, ROM

CLEAR = (0xC4, 0xC6, 0xBA, 0xB2, 0xA4, 0x96, 0x98, 0x92, 0x94)


def start(snap, x0):
    nes = Glitchy(ROM)
    nes.restore(snap)
    r = nes.ram
    r[0x334] = x0
    r[0x31A] = 0x60
    r[0xA0] = 1
    r[0x32] = 2
    r[0xAE] = 0
    for a in CLEAR:
        r[a] = 0
    return nes, r


def fall_death(snap, x0):
    nes, r = start(snap, x0)
    lastY = 0
    for f in range(150):
        nes.frame(0)
        if r[0x90] == 2:
            return f if lastY >= 0xD0 else None
        if r[0xA0] == 0:
            return None
        lastY = r[0x31A]
    return None


def timeline(snap, x0, k):
    nes, r = start(snap, x0)
    if k is not None:
        nes.glitch_frame = nes.frames + k
    rows = []
    for f in range(600):
        nes.frame(0)
        rows.append(dict(f=f, mode=r[0x2C], st=r[0x90], spr=r[0x300], y=r[0x31A], x=r[0x334], ba=r[0xBA],
                         lives=r[0x32], walk=r[0x192], sub=r[0x2D]))
        if r[0x30] == 1:
            break
    return rows


def summarize(rows):
    ev = {}
    for a, b in zip(rows, rows[1:]):
        if b['mode'] != a['mode']:
            ev.setdefault('mode%02X' % b['mode'], b['f'])
        if b['st'] == 2 and a['st'] == 1:
            ev.setdefault('death', b['f'])
        if b['lives'] < a['lives']:
            ev.setdefault('livesDown', b['f'])
        if b['st'] == 1 and a['st'] == 0:
            ev.setdefault('respawn', b['f'])
        if b['ba'] == 0xFF and a['ba'] != 0xFF:
            ev.setdefault('removed', b['f'])
    if 'respawn' in ev:
        after = [r for r in rows if r['f'] >= ev['respawn'] and r['mode'] in (8, 9)]
        ev['respawn_drawn_frames'] = sum(1 for r in after if r['spr'] and r['ba'] == 0)
        ev['respawn_frames'] = len(after)
    return ev


if __name__ == '__main__':
    snaps = traverse()
    found = []
    for P in range(0x0600, 0x0B00, 0x20):
        for x0 in range(0x10, 0xF0, 8):
            d = fall_death(snaps[P], x0)
            if d:
                found.append((P, x0, d))
    print('bottomless pit falls found: %d' % len(found))
    for P, x0, d in found[:6]:
        base = summarize(timeline(snaps[P], x0, None))
        print('\nP=%04X X=%02X  fall death at f%d   no misread: %s' % (P, x0, d, base))
        for k in (d - 20, d - 5, d + 10, d + 40):
            ev = summarize(timeline(snaps[P], x0, k))
            gaps = []
            if 'livesDown' in ev and 'mode05' in ev:
                gaps.append('livesDown->fade %d f' % (ev['mode05'] - ev['livesDown']))
            if 'death' in ev and 'livesDown' in ev:
                gaps.append('death->livesDown %d f' % (ev['livesDown'] - ev['death']))
            print('  misread f%-4d %s   %s' % (k, sorted(ev.items(), key=lambda kv: kv[1] if isinstance(kv[1], int) else 0), ', '.join(gaps)))
