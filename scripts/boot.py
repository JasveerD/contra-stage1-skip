import sys
import time
import pickle
from emu import NES, START, RIGHT, A_, B_

nes = NES(sys.argv[1])
r = nes.ram
t0 = time.time()


def st():
    return ('f=%d mode$2C=%02X lvl=%02X state=%02X X=%02X Y=%02X scr=%02X.%02X FD=%02X FC=%02X lives=%02X rng=%02X'
            % (nes.frames, r[0x2C], r[0x30], r[0x90], r[0x334], r[0x31A], r[0x64], r[0x65], r[0xFD], r[0xFC], r[0x32], r[0x34]))


for i in range(120):
    nes.frame()
print(st())
# tap start a few times until the game begins
for attempt in range(8):
    for i in range(4):
        nes.frame(START)
    for i in range(100):
        nes.frame()
    print(st())
    if r[0x90] == 1:
        break
for i in range(400):
    nes.frame()
    if r[0x90] == 1 and r[0x2C] >= 4:
        break
print(st())
for i in range(60):
    nes.frame()
print('in level:', st(), '%.1f fps' % (nes.frames / (time.time() - t0)))
pickle.dump(nes.snapshot(), open('start.pkl', 'wb'))
# sanity: hold right for 300 frames
for i in range(300):
    nes.frame(RIGHT)
    if i % 50 == 49:
        print(st())
