"""Recursive-descent code map for Contra (USA): follows vectors, branches, bank trampolines,
inline C857 jump tables and the enemy routine tables. Writes codemap.pkl = {(bank, addr): (len, text)}."""
import sys
import pickle
from dis import T, LEN, dis_one, REL, ABS, IND

ROM = sys.argv[1]
prg = open(ROM, 'rb').read()[16:16 + 8 * 0x4000]


def byte(bank, addr):
    if addr >= 0xC000:
        return prg[0x1C000 + addr - 0xC000]
    if addr >= 0x8000:
        return prg[bank * 0x4000 + addr - 0x8000]
    return None


def word(bank, addr):
    lo, hi = byte(bank, addr), byte(bank, addr + 1)
    return None if lo is None or hi is None else lo | (hi << 8)


def key(bank, addr):
    return (7 if addr >= 0xC000 else bank, addr)


code = {}
data = set()
work = []


def add(bank, addr, why=''):
    if addr is None or addr < 0x8000:
        return
    k = key(bank, addr)
    if k not in code and k not in data:
        work.append((bank, addr))


def table(bank, addr, n_max, ctx_bank):
    """Read up to n_max pointers; stop at the first that cannot be code."""
    for i in range(n_max):
        a = addr + 2 * i
        if key(bank, a) in code:
            break
        p = word(bank, a)
        if p is None or p < 0x8000 or byte(ctx_bank, p) not in T:
            break
        data.add(key(bank, a))
        data.add(key(bank, a + 1))
        add(ctx_bank, p)


def run():
    while work:
        bank, addr = work.pop()
        last_ldy = None
        while True:
            k = key(bank, addr)
            if k in code or k in data:
                break
            op = byte(bank, addr)
            if op not in T:
                break
            m, mode = T[op]
            n = LEN[mode]
            b = prg[0x1C000:] if addr >= 0xC000 else prg[bank * 0x4000:(bank + 1) * 0x4000]
            base = 0xC000 if addr >= 0xC000 else 0x8000
            _, text = dis_one(b, addr - base, base)
            code[k] = (n, text, bank)
            arg = word(bank, addr + 1) if n == 3 else None
            nxt = addr + n
            if m == 'LDY' and mode != REL and n == 2 and op == 0xA0:
                last_ldy = byte(bank, addr + 1)
            if mode == REL:
                off = byte(bank, addr + 1)
                add(bank, (nxt + (off - 256 if off > 127 else off)) & 0xFFFF)
            if m == 'JSR':
                if arg == 0xC139 and last_ldy is not None and last_ldy < 7:
                    bank_after = last_ldy
                    op2 = byte(bank, nxt)
                    if op2 in (0x4C, 0x20):
                        add(bank_after, word(bank, nxt + 1))
                    bank = bank_after if addr < 0xC000 else bank
                    addr = nxt
                    continue
                if arg == 0xC857:
                    table(bank, nxt, 24, bank)
                    break
                add(bank, arg)
            if m == 'JMP':
                if mode == ABS:
                    add(bank, arg)
                break
            if m in ('RTS', 'RTI', 'BRK'):
                break
            addr = nxt


for v in (0xFFFA, 0xFFFC, 0xFFFE):
    add(7, word(7, v))
run()
# enemy routine tables: global types 0-$0F, then per-level tables of types $10+
for t in range(16):
    st = word(7, 0xE6A8 + 2 * t)
    if st and st >= 0x8000:
        table(0, st + 2, 16, 0)
for lvl in range(8):
    lt = word(7, 0xE698 + 2 * lvl)
    for t in range(24):
        st = word(7, lt + 2 * t)
        if not st or st < 0x8000:
            break
        table(0, st + 2, 16, 0)
run()
# second pass: any bank-switch trampolines in code that reach other banks
pickle.dump(code, open('codemap.pkl', 'wb'))
per = {}
for (b, a) in code:
    per[b] = per.get(b, 0) + 1
print('instructions mapped per bank:', per, 'total', len(code))
