"""Play stage 1 to a boss kill and on into stage 2, logging every executed write to the stage-flow variables."""
import sys
import pickle
import random
from emu import NES, RIGHT, LEFT, DOWN, UP, A_, B_

WATCH = {0x29: 'deathtimer', 0x2A: 'timerLo', 0x2B: 'timerHi', 0x2C: 'mode', 0x2D: 'submode', 0x30: 'level',
         0x38: 'p1GameOver', 0x39: 'p2GameOver', 0x3A: 'continues', 0x3B: 'stageClear',
         0x190: 'walkDelay', 0x191: 'walkTimeout', 0x192: 'p1Walk', 0x193: 'p2Walk', 0x194: 'playersAlive'}
QUIET = {0x2A, 0x190, 0x191}


class Tracer(NES):
    def __init__(self, path):
        super().__init__(path)
        self.log = []
        self.seen = set()
        self.calls = []

    def wr(self, addr, v):
        if addr in WATCH and self.ram[addr] != v:
            key = (addr, self.ipc)
            if addr not in QUIET or key not in self.seen:
                self.log.append((self.frames, WATCH[addr], addr, self.ram[addr], v, self.bank, self.ipc, self.ram[0x2C]))
            self.seen.add(key)
        super().wr(addr, v)

    def op_JSR(self, m):
        t = self.rd(self.pc) | (self.rd(self.pc + 1) << 8)
        if t == 0xEAEA:
            self.calls.append((self.frames, self.ipc, self.bank, self.x, self.ram[0x528 + self.x]))
        super().op_JSR(m)


ACTIONS = [(RIGHT, 0, 40), (RIGHT, A_, 14), (LEFT, 0, 4), (LEFT, A_, 3), (DOWN, A_, 8), (0, 0, 3), (DOWN, 0, 2),
           (RIGHT | DOWN, A_, 4), (RIGHT | UP, B_, 4), (RIGHT, B_, 8)]

nes = Tracer(sys.argv[1])
nes.restore(pickle.load(open('start.pkl', 'rb')))
r = nes.ram
rng = random.Random(7)
left = 0
for f in range(30000):
    if left == 0:
        hold, tap, w = rng.choices(ACTIONS, weights=[a[2] for a in ACTIONS])[0]
        left = rng.randint(3, 50)
        first = True
    pad = hold | (tap if first or rng.random() < 0.1 else 0)
    first = False
    left -= 1
    if r[0x30] == 0:
        r[0xAE] = 0x40
        r[0x32] = 9
    else:
        pad = 0
    nes.frame(pad)
    if r[0x30] == 1 and r[0x2C] == 4:
        print('stage 2 running at frame %d' % nes.frames)
        break

print('\nJSR $EAEA (stage clear) calls: frame, caller, bank, enemy slot X, enemy type $0528,X')
for c in nes.calls:
    print('  f%d  %X:%04X  slot %d  type %02X' % (c[0], c[2], c[1], c[3], c[4]))
print('\nexecuted writes (frame  variable  old->new  writer  mode-at-time):')
for fr, name, addr, old, new, bank, pc, mode in nes.log:
    where = '%X:%04X' % (bank if pc < 0xC000 else 7, pc)
    print('  f%-6d %-13s $%04X  %02X -> %02X   %s   mode %02X' % (fr, name, addr, old, new, where, mode))
