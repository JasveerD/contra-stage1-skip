"""Systematic falls: at every 16px of stage 1 scroll, drop the player from the top at each column,
let them land / splash / die, then walk right and left off whatever is there. Flag discontinuities."""
import sys
import pickle
from multiprocessing import Pool
from emu import NES, RIGHT, LEFT

ROM = sys.argv[1]
XSTEP = int(sys.argv[2]) if len(sys.argv) > 2 else 8


def traverse():
    nes = NES(ROM)
    nes.restore(pickle.load(open('start.pkl', 'rb')))
    r = nes.ram
    snaps = {}
    stuck = 0
    lastP = -1
    while stuck < 400:
        r[0xAE] = 0x40
        r[0x32] = 9
        r[0x31A] = 0x30
        r[0xC4] = r[0xC6] = 0
        r[0xBA] = 0
        if r[0xA0] == 0:
            r[0xA0] = 1
        nes.frame(RIGHT)
        if r[0x2C] != 4:
            break
        P = (r[0x64] << 8) | r[0x65]
        if P != lastP:
            stuck = 0
            lastP = P
            if P % 16 == 0:
                snaps[P] = nes.snapshot()
        else:
            stuck += 1
    return snaps


def trial(args):
    P0, snap = args
    nes = NES(ROM)
    r = nes.ram
    flags = []
    respawns = {}
    for X0 in range(8, 249, XSTEP):
        nes.restore(snap)
        r[0x334] = X0
        r[0x31A] = 0x10
        r[0xA0] = 1
        for a in (0xC4, 0xC6, 0xBA, 0xB2, 0xA4, 0x96, 0x98, 0x92, 0x94):
            r[a] = 0
        prevP = (r[0x64] << 8) | r[0x65]
        prevX, prevY, prevS = r[0x334], r[0x31A], r[0x90]
        dead_at = None
        for f in range(360):
            pad = 0 if f < 120 else (RIGHT if f < 240 else LEFT)
            r[0xAE] = 0x40
            r[0x32] = 9
            try:
                nes.frame(pad)
            except Exception as e:
                flags.append('P0=%04X X0=%02X f%d EXCEPTION %s' % (P0, X0, f, e))
                break
            P = (r[0x64] << 8) | r[0x65]
            X, Y, S = r[0x334], r[0x31A], r[0x90]
            if P - prevP > 1 or P < prevP:
                flags.append('P0=%04X X0=%02X f%d SCROLL JUMP %04X->%04X' % (P0, X0, f, prevP, P))
            if S == 1 and prevS == 1 and (abs(X - prevX) > 2 or abs(Y - prevY) > 17):
                flags.append('P0=%04X X0=%02X f%d POS JUMP X %02X->%02X Y %02X->%02X water=%02X'
                             % (P0, X0, f, prevX, X, prevY, Y, r[0xB2]))
            if S == 2 and prevS == 1:
                dead_at = (P, prevX)
            if S == 1 and prevS == 0 and dead_at is not None:
                respawns[dead_at] = X
                dead_at = None
            if r[0x2C] != 4:
                break
            prevP, prevX, prevY, prevS = P, X, Y, S
    return P0, flags, respawns


if __name__ == '__main__':
    snaps = traverse()
    print('snapshots: %d, from P=%04X to P=%04X' % (len(snaps), min(snaps), max(snaps)))
    with Pool(8) as p:
        res = p.map(trial, sorted(snaps.items()), chunksize=2)
    nflags = 0
    far = []
    for P0, flags, respawns in res:
        nflags += len(flags)
        for fl in flags[:6]:
            print('  ', fl)
        for (P, X), RX in respawns.items():
            far.append((RX, P, X))
    print('total flags: %d' % nflags)
    print('deaths with respawn recorded: %d' % len(far))
    hist = {}
    for RX, P, X in far:
        hist[RX] = hist.get(RX, 0) + 1
    print('respawn X histogram:', ' '.join('%02X:%d' % kv for kv in sorted(hist.items())))
    far.sort(reverse=True)
    print('furthest-right respawns (respawn X, scroll P at death, X at death):')
    for RX, P, X in far[:12]:
        print('   respawn X=%02X  at P=%04X (screen %d + %d px), died at X=%02X' % (RX, P, P >> 8, P & 0xFF, X))
    pickle.dump(far, open('respawns.pkl', 'wb'))
