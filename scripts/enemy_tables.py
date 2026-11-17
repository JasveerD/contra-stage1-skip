"""Stage-1 enemy types -> state tables; flag state routines that can reach the stage-clear call ($EAEA)."""
import sys
from reach import reach, byte

ROM = sys.argv[1]
LEVEL = int(sys.argv[2]) if len(sys.argv) > 2 else 0
CLEAR_SITES = {'7:E745', '0:A8DB', '0:AD4E', '0:BD51'}


def word(bank, a):
    return byte(bank, a) | (byte(bank, a + 1) << 8)


def clears(entry):
    _, seen = reach([(0, entry)])
    return any('%d:%04X' % k in CLEAR_SITES for k in seen)


types = [(t, word(7, 0xE6A8 + 2 * t)) for t in range(16)]
lt = word(7, 0xE698 + 2 * LEVEL)
for i in range(24):
    st = word(7, lt + 2 * i)
    if st < 0x8000 or (i and st == types[-1][1] and False):
        break
    types.append((0x10 + i, st))
    nxt = word(7, lt + 2 * (i + 1))
    if lt + 2 * (i + 1) >= word(7, 0xE698 + 2 * (LEVEL + 1)):
        break

owner = {}
for t, st in types:
    owner.setdefault(st, []).append(t)
starts = sorted(owner)
cache = {}
print('level %d enemy state tables (state n entry is at table + 2n):' % LEVEL)
for i, st in enumerate(starts):
    end = starts[i + 1] if i + 1 < len(starts) else st + 2 * 12
    n = min(12, max(1, (end - st) // 2))
    ents = []
    for s in range(1, n + 1):
        p = word(0, st + 2 * s)
        if p < 0x8000:
            break
        if p not in cache:
            cache[p] = clears(p)
        ents.append('%d:%04X%s' % (s, p, '*CLEAR*' if cache[p] else ''))
    print('  types %-12s table %04X  %s' % (','.join('$%02X' % t for t in owner[st]), st, ' '.join(ents)))
