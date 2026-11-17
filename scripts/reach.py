"""Which RAM does code reachable from a given entry write? Follows branches, JMP and JSR (incl. bank trampolines)."""
import re
import sys
from dis import T, LEN, dis_one, REL, ABS

prg = open(sys.argv[1], 'rb').read()[16:16 + 8 * 0x4000]
WRITE_OPS = {'STA', 'STX', 'STY', 'INC', 'DEC', 'ASL', 'LSR', 'ROL', 'ROR'}


def byte(bank, addr):
    if addr >= 0xC000:
        return prg[0x1C000 + addr - 0xC000]
    return prg[bank * 0x4000 + addr - 0x8000] if addr >= 0x8000 else None


def reach(entries, stop=()):
    seen, writes, calls = set(), {}, set()
    work = list(entries)
    while work:
        bank, addr = work.pop()
        ldy = None
        while addr >= 0x8000:
            k = (7 if addr >= 0xC000 else bank, addr)
            if k in seen or addr in stop:
                break
            seen.add(k)
            op = byte(bank, addr)
            if op not in T:
                break
            m, mode = T[op]
            n = LEN[mode]
            base = 0xC000 if addr >= 0xC000 else 0x8000
            blob = prg[0x1C000:] if addr >= 0xC000 else prg[bank * 0x4000:(bank + 1) * 0x4000]
            _, text = dis_one(blob, addr - base, base)
            arg = text.partition(' ')[2]
            nxt = addr + n
            if m in WRITE_OPS and mode not in (2,):
                mm = re.match(r'^\$([0-9A-F]{2,4})(,[XY])?$', arg)
                if mm and int(mm.group(1), 16) < 0x800:
                    writes.setdefault(arg, set()).add('%d:%04X' % k)
                elif arg.startswith('('):
                    writes.setdefault(arg, set()).add('%d:%04X' % k)
            if op == 0xA0:
                ldy = byte(bank, addr + 1)
            w = (byte(bank, addr + 1) | (byte(bank, addr + 2) << 8)) if n == 3 else None
            if mode == REL:
                off = byte(bank, addr + 1)
                work.append((bank, (nxt + (off - 256 if off > 127 else off)) & 0xFFFF))
            if m == 'JSR':
                calls.add(w)
                if w in (0xC139, 0xC13F) and ldy is not None and ldy < 7:
                    bank = ldy
                elif w == 0xC857:
                    break
                else:
                    work.append((bank, w))
            if m == 'JMP':
                if mode == ABS:
                    work.append((bank, w))
                break
            if m in ('RTS', 'RTI', 'BRK'):
                break
            addr = nxt
    return writes, seen


if __name__ == '__main__':
    lag_writes, lag_seen = reach([(7, 0xC0B6)], stop={0xC0AF})
    print('lag-frame NMI path: %d instructions reachable' % len(lag_seen))
    for a in sorted(lag_writes, key=lambda s: (len(s), s)):
        print('  %-10s %s' % (a, ' '.join(sorted(lag_writes[a])[:5])))
