import sys

rom = open(sys.argv[1], 'rb').read()[16:]
LEVEL = int(sys.argv[2]) if len(sys.argv) > 2 else 0


def bank(n):
    return rom[n * 0x4000:(n + 1) * 0x4000]


B2 = bank(2)
B7 = bank(7)


def rd(b, addr, base=0x8000):
    return b[addr - base]


def rd16(b, addr, base=0x8000):
    return b[addr - base] | (b[addr - base + 1] << 8)


hdr = [rd(B2, 0xB319 + LEVEL * 32 + i) for i in range(32)]
print('header $40-$5F:', ' '.join('%02X' % x for x in hdr))
layout_ptr = hdr[2] | hdr[3] << 8
super_ptr = hdr[4] | hdr[5] << 8
pal_ptr = hdr[6] | hdr[7] << 8
stop = hdr[8]
t49, t4a, t4b = hdr[9], hdr[10], hdr[11]
print('layout %04X supertiles %04X palette %04X stop screen %02X thresholds %02X %02X %02X auto-scroll screen($58) %02X'
      % (layout_ptr, super_ptr, pal_ptr, stop, t49, t4a, t4b, hdr[0x18]))


def classify(t):
    if t == 0:
        return 0
    if t < t49:
        return 1
    if t < t4a:
        return 0
    if t < t4b:
        return 2
    return 3


def screen(n, prev):
    p = rd16(B2, layout_ptr + n * 2)
    out = []
    i = 0
    while len(out) < 0x38:
        a = rd(B2, p + i)
        i += 1
        if a < 0x80:
            out.append(a)
        elif a < 0xF0:
            v = rd(B2, p + i)
            i += 1
            out.extend([v] * (a & 0x7F))
        else:
            # copy a row of 8 from the buffer currently being written (row index in low nibble)
            r = (a & 0x0F) * 8
            out.extend(out[r:r + 8])
    return out[:0x38]


CH = {0: '.', 1: '=', 2: '~', 3: '#'}
nscreens = stop + 2
rows = [''] * 14
for s in range(nscreens):
    lay = screen(s, None)
    for sr in range(7):
        for cy in range(2):
            line = ''
            for sc in range(8):
                st = lay[sr * 8 + sc]
                base = super_ptr + st * 16
                for cx in range(2):
                    t = rd(bank(3), base + (2 * cy) * 4 + 2 * cx)
                    line += CH[classify(t)]
            rows[sr * 2 + cy] += line + '|'
print('     ' + ''.join(('scr %-2d' % s).ljust(17) for s in range(nscreens)))
for i, r in enumerate(rows):
    print('y=%02X %s' % (i * 16, r))
