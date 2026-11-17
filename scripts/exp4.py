"""Pit drops on the second half of stage 1, no forced invincibility; flag any early stage exit."""
import sys, pickle
from multiprocessing import Pool
from emu import NES, RIGHT, LEFT, A_
from exp2 import traverse
ROM = sys.argv[1]

def trial(args):
    P0, snap = args
    nes = NES(ROM); r = nes.ram
    hits = []
    for X0 in range(8, 249, 6):
        for pad_after in (0, RIGHT, LEFT):
            nes.restore(snap)
            r[0x334] = X0; r[0x31A] = 0x10; r[0xA0] = 1; r[0xAE] = 0
            for a in (0xC4, 0xC6, 0xBA, 0xB2, 0xA4, 0x96, 0x98, 0x92, 0x94):
                r[a] = 0
            trace = []
            for f in range(300):
                r[0x32] = 9
                try:
                    nes.frame(pad_after if f > 20 else 0)
                except Exception as e:
                    hits.append((P0, X0, pad_after, 'EXC %s' % e, trace[-8:])); break
                trace.append((f, r[0x90], r[0x31A], r[0xBA], r[0xB2], r[0x2C], r[0x3B], r[0x64], r[0x65]))
                if r[0x3B] or r[0x2C] != 4 or r[0x30] != 0:
                    hits.append((P0, X0, pad_after, 'EXIT mode=%02X 3B=%02X lvl=%02X' % (r[0x2C], r[0x3B], r[0x30]), trace[-12:]))
                    break
    return hits

if __name__ == '__main__':
    snaps = {P: s for P, s in traverse().items() if 0x0500 <= P < 0x0C00}
    print('testing %d scroll positions' % len(snaps), flush=True)
    with Pool(8) as p:
        res = p.map(trial, sorted(snaps.items()), chunksize=1)
    hits = [h for hs in res for h in hs]
    print('early exits: %d' % len(hits))
    for P0, X0, pad, why, tr in hits[:15]:
        print('P=%04X X0=%02X pad=%02X %s' % (P0, X0, pad, why))
        for t in tr: print('     f%d state=%02X Y=%02X BA=%02X water=%02X mode=%02X 3B=%02X scr=%02X.%02X' % t)
    pickle.dump(hits, open('exits.pkl', 'wb'))
