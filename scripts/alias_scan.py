"""Static scan over mapped code only: stores that could land on target zero-page bytes, and the index needed."""
import re
import sys
import pickle

TARGETS = [int(t, 16) for t in (sys.argv[1:] or ['2C', '3B'])]
WRITE_OPS = {'STA', 'STX', 'STY', 'INC', 'DEC', 'ASL', 'LSR', 'ROL', 'ROR'}
code = pickle.load(open('codemap.pkl', 'rb'))

rows, ind, direct = [], {}, []
for (bank, addr), (n, text, ctx) in code.items():
    op, _, arg = text.partition(' ')
    if op not in WRITE_OPS:
        continue
    loc = '%d:%04X' % (bank if addr < 0xC000 else 7, addr)
    mz = re.match(r'^\$([0-9A-F]{2}),([XY])$', arg)
    ma = re.match(r'^\$([0-9A-F]{4}),([XY])$', arg)
    md = re.match(r'^\$([0-9A-F]{2,4})$', arg)
    if arg.startswith('('):
        ind.setdefault(arg, []).append(loc)
        continue
    for t in TARGETS:
        if mz:
            need = (t - int(mz.group(1), 16)) & 0xFF
            if need:
                rows.append((t, need, loc, text, mz.group(2)))
        elif ma and int(ma.group(1), 16) <= t:
            rows.append((t, t - int(ma.group(1), 16), loc, text, ma.group(2)))
        elif md and int(md.group(1), 16) == t:
            direct.append((t, loc, text))

for t in TARGETS:
    print('=== $%02X direct writes:' % t, ' '.join('%s(%s)' % (l, x) for tt, l, x in sorted(direct) if tt == t))
    for _, need, loc, text, reg in sorted(r for r in rows if r[0] == t and r[1] <= 0x1F):
        print('  %-8s %-14s needs %s=$%02X' % (loc, text, reg, need))
print('=== indirect stores in code:')
for k, v in sorted(ind.items(), key=lambda kv: -len(kv[1])):
    print('  %-10s %3d sites: %s' % (k, len(v), ' '.join(sorted(v))))
