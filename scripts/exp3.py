"""What does a corrupted screen counter look like? Walk (hovering, invincible) to screen 2, bump $64, keep going."""
import sys, pickle
from emu import NES, RIGHT

def run(bump_to):
    nes = NES(sys.argv[1])
    nes.restore(pickle.load(open('start.pkl', 'rb')))
    r = nes.ram
    f = 0
    bumped = None
    while f < 6000:
        r[0xAE] = 0x40; r[0x32] = 9
        r[0x31A] = 0x30; r[0xC4] = r[0xC6] = 0; r[0xBA] = 0
        if r[0xA0] == 0: r[0xA0] = 1
        if bump_to is not None and bumped is None and r[0x64] == 2 and r[0x65] == 0x80:
            r[0x64] = bump_to
            bumped = f
        nes.frame(RIGHT); f += 1
        if r[0x84] or r[0x2C] != 4:
            break
    return f, bumped, r[0x64], r[0x65], r[0x84], r[0x71], r[0x2C]

for b in (None, 6):
    f, bumped, s, o, boss, stop, mode = run(b)
    print('bump $64 to %s: reached screen %02X.%02X after %d frames (bumped at frame %s), boss flag $84=%02X, mode=%02X'
          % (b, s, o, f, bumped, boss, mode))
