"""Replay the video: walk to the cliff area, jump into each pit from the left ledge, trace the player each frame."""
import sys, pickle
from emu import NES, RIGHT, LEFT, A_
from exp2 import traverse
ROM = sys.argv[1]
snaps = traverse()
nes = NES(ROM); r = nes.ram
for P0 in range(0x0700, 0x0B80, 0x10):
    if P0 not in snaps: continue
    for X0 in range(0x20, 0xE0, 4):
        nes.restore(snaps[P0])
        r[0x334] = X0; r[0x31A] = 0x40; r[0xA0] = 1; r[0xAE] = 0
        for a in (0xC4, 0xC6, 0xBA, 0xB2, 0xA4, 0x96, 0x98, 0x92, 0x94): r[a] = 0
        tr = []; saw_low = False
        for f in range(500):
            r[0x32] = 9
            nes.frame(RIGHT if 30 < f < 60 else 0)
            tr.append((f, r[0x90], r[0x334], r[0x31A], r[0xBA], r[0xB2], r[0x2C], r[0x3B], r[0x64], r[0x65]))
            if r[0x90] == 1 and (r[0x31A] >= 0xD8 or r[0xBA]):
                saw_low = True
            if r[0x2C] != 4 or r[0x3B]:
                print('*** P0=%04X X0=%02X: stage exit at f%d' % (P0, X0, f))
                for t in tr[-40::2]: print('   f%d st=%02X X=%02X Y=%02X BA=%02X water=%02X mode=%02X 3B=%02X scr=%02X.%02X' % t)
                sys.exit()
        if saw_low and tr[-1][1] == 1 and tr[-1][4]:
            print('P0=%04X X0=%02X alive with BA set at end: %s' % (P0, X0, tr[-1]))
print('no exit found')
