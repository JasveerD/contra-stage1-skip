"""Poke the stage-clear flag mid-stage-1 under different conditions and see whether stage 2 loads."""
import sys
import pickle
from emu import NES, RIGHT


def trial(name, poke, frames=1500):
    nes = NES(sys.argv[1])
    nes.restore(pickle.load(open('start.pkl', 'rb')))
    r = nes.ram
    for _ in range(200):
        r[0x32] = 9
        nes.frame(RIGHT)
    poke(r)
    modes = []
    for f in range(frames):
        nes.frame(0)
        if not modes or modes[-1][1] != r[0x2C]:
            modes.append((f, r[0x2C]))
        if r[0x30] == 1 and r[0x2C] == 4:
            break
    path = ' -> '.join('%02X@f%d' % (m, f) for f, m in modes)
    result = 'STAGE 2 LOADED' if r[0x30] == 1 else 'still level %d, mode %02X, $2A=%02X' % (r[0x30], r[0x2C], r[0x2A])
    print('%-46s %s\n%46s modes: %s' % (name, result, '', path))


def set_(**kv):
    def f(r):
        for k, v in kv.items():
            r[int(k[1:], 16)] = v
    return f


trial('$3B=1, $2A=0 (timer already idle)', set_(x3B=1, x2A=0))
trial('$3B=1, $2A=$FF (boss never arms the timer)', set_(x3B=1, x2A=0xFF))
trial('$3B=1, $2A=0, player 1 dead ($90=2)', set_(x3B=1, x2A=0, x90=2))
trial('$3B=1, $2A=0, player 1 game over ($38=1)', set_(x3B=1, x2A=0, x38=1))
trial('$3B=0 (no flag), $2C=8 forced', set_(x2C=8, x2A=0))
