"""Simulate a one-frame cartridge misread of the stage-clear check (BNE at $CEEC read as BEQ)
while the player falls into a Stage 1 cliff pit, and time what happens next."""
import sys
import pickle
from emu import NES
from exp2 import traverse

ROM = sys.argv[1]
BAD_ADDR, BAD_BYTE = 0xCEEC, 0xF0


class Glitchy(NES):
    glitch_frame = -1

    def rd(self, addr):
        if addr == BAD_ADDR and self.frames == self.glitch_frame:
            return BAD_BYTE
        return super().rd(addr)


def drop(snap, x0, inject=None, frames=900):
    nes = Glitchy(ROM)
    nes.restore(snap)
    r = nes.ram
    r[0x334] = x0
    r[0x31A] = 0x40
    r[0xA0] = 1
    r[0xAE] = 0
    for a in (0xC4, 0xC6, 0xBA, 0xB2, 0xA4, 0x96, 0x98, 0x92, 0x94):
        r[a] = 0
    start = nes.frames
    if inject is not None:
        nes.glitch_frame = start + inject
    ev = {}
    prev = (r[0x90], r[0x2C], r[0x300])
    for f in range(frames):
        r[0x32] = 5
        nes.frame(0)
        st, mode, spr = r[0x90], r[0x2C], r[0x300]
        if st == 2 and prev[0] == 1 and 'death' not in ev:
            ev['death'] = f
        if st == 1 and prev[0] == 0 and 'respawn' not in ev:
            ev['respawn'] = f
        if mode != prev[1]:
            ev.setdefault('mode%02X' % mode, f)
        if spr == 0 and prev[2] != 0 and 'vanish' not in ev:
            ev['vanish'] = f
        if r[0x30] == 1:
            ev['stage2'] = f
            break
        prev = (st, mode, spr)
    return ev


if __name__ == '__main__':
    snaps = traverse()
    pits = []
    for P in range(0x0700, 0x0B00, 0x20):
        if P not in snaps:
            continue
        for x0 in range(0x30, 0xD0, 8):
            ev = drop(snaps[P], x0, frames=200)
            if 'death' in ev:
                pits.append((P, x0, ev['death']))
                break
    print('pits found (scroll, x, frames from drop to fall-death):')
    for p in pits:
        print('   P=%04X X=%02X death at f%d' % p)
    pickle.dump(pits, open('pits.pkl', 'wb'))

    for P, x0, d in pits[:3]:
        base = drop(snaps[P], x0, frames=400)
        print('\n=== pit P=%04X X=%02X  baseline (no glitch): %s' % (P, x0, base))
        print('  inject  | events (frames after drop)')
        for k in list(range(0, d + 1, 3)) + list(range(d + 1, d + 120, 8)):
            ev = drop(snaps[P], x0, inject=k)
            gap = ev['mode05'] - ev['vanish'] if 'vanish' in ev and 'mode05' in ev else None
            tag = 'STAGE 2' if 'stage2' in ev else 'no skip'
            print('  f%-4d %-7s %s%s' % (k, tag, ' '.join('%s@%d' % kv for kv in sorted(ev.items(), key=lambda kv: kv[1])),
                                         '   vanish->fade %d frames' % gap if gap is not None else ''))
