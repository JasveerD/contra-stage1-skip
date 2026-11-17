"""Random play through stage 1 with invincibility; flag any scroll / position discontinuity."""
import sys
import pickle
import random
from multiprocessing import Pool
from emu import NES, START, RIGHT, LEFT, DOWN, UP, A_, B_

ROM = sys.argv[1]
FRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
SEEDS = int(sys.argv[3]) if len(sys.argv) > 3 else 8

ACTIONS = [(RIGHT, 0, 40), (RIGHT, A_, 14), (LEFT, 0, 4), (LEFT, A_, 3), (DOWN, A_, 8), (0, 0, 3), (DOWN, 0, 2),
           (RIGHT | DOWN, A_, 4), (RIGHT | UP, B_, 4), (RIGHT, B_, 8)]


def run(seed):
    rng = random.Random(seed)
    nes = NES(ROM)
    nes.restore(pickle.load(open('start.pkl', 'rb')))
    r = nes.ram
    out = []
    deaths = []
    hold = tap = 0
    left = 0
    prevP = (r[0x64] << 8) | r[0x65]
    prevX, prevY, prevS = r[0x334], r[0x31A], r[0x90]
    maxP = prevP
    try:
        for f in range(FRAMES):
            if left == 0:
                hold, tap, w = rng.choices(ACTIONS, weights=[a[2] for a in ACTIONS])[0]
                left = rng.randint(3, 50)
                first = True
            pad = hold | (tap if first or rng.random() < 0.1 else 0)
            first = False
            left -= 1
            r[0xAE] = 0x40          # invincibility timer
            r[0x32] = 9             # lives
            nes.frame(pad)
            if r[0x2C] != 4 or r[0x30] != 0:
                out.append('seed %d f%d left stage: mode %02X level %02X P=%04X' % (seed, f, r[0x2C], r[0x30], prevP))
                break
            P = (r[0x64] << 8) | r[0x65]
            X, Y, S = r[0x334], r[0x31A], r[0x90]
            dP = P - prevP
            if dP > 1 or dP < 0:
                out.append('seed %d f%d SCROLL JUMP %04X -> %04X  X=%02X Y=%02X state=%02X' % (seed, f, prevP, P, X, Y, S))
            if S == 1 and prevS == 1:
                dX = X - prevX
                dY = Y - prevY
                if abs(dX) > 2 or abs(dY) > 17:
                    out.append('seed %d f%d POS JUMP X %02X->%02X Y %02X->%02X P=%04X water=%02X BA=%02X'
                               % (seed, f, prevX, X, prevY, Y, P, r[0xB2], r[0xBA]))
            if S == 2 and prevS == 1:
                deaths.append([P, prevX, prevY, None])
            if S == 1 and prevS == 0 and deaths and deaths[-1][3] is None:
                deaths[-1][3] = X
            prevP, prevX, prevY, prevS = P, X, Y, S
            maxP = max(maxP, P)
    except Exception as e:  # emulator hit something it cannot run
        out.append('seed %d EXCEPTION %s P=%04X' % (seed, e, prevP))
    return seed, maxP, out, deaths


if __name__ == '__main__':
    with Pool(min(SEEDS, 8)) as p:
        res = p.map(run, range(SEEDS))
    alld = []
    for seed, maxP, out, deaths in res:
        print('seed %d reached P=%04X, %d deaths, %d flags' % (seed, maxP, len(deaths), len(out)))
        for o in out[:12]:
            print('   ', o)
        alld += deaths
    print('respawn X by death position (P, X at death, Y at death -> respawn X):')
    seen = set()
    for P, X, Y, RX in sorted(alld):
        if RX is not None and RX != 0x30:
            k = (P >> 4, RX)
            if k not in seen:
                seen.add(k)
                print('   P=%04X X=%02X Y=%02X -> respawn X=%02X' % (P, X, Y, RX))
