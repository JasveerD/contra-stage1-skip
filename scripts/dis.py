import sys

IMP, ACC, IMM, ZP, ZPX, ZPY, ABS, ABX, ABY, IND, IZX, IZY, REL = range(13)
LEN = {IMP: 1, ACC: 1, IMM: 2, ZP: 2, ZPX: 2, ZPY: 2, ABS: 3, ABX: 3, ABY: 3, IND: 3, IZX: 2, IZY: 2, REL: 2}

T = {}


def add(m, pairs):
    for op, mode in pairs:
        T[op] = (m, mode)


add('ADC', [(0x69, IMM), (0x65, ZP), (0x75, ZPX), (0x6D, ABS), (0x7D, ABX), (0x79, ABY), (0x61, IZX), (0x71, IZY)])
add('AND', [(0x29, IMM), (0x25, ZP), (0x35, ZPX), (0x2D, ABS), (0x3D, ABX), (0x39, ABY), (0x21, IZX), (0x31, IZY)])
add('ASL', [(0x0A, ACC), (0x06, ZP), (0x16, ZPX), (0x0E, ABS), (0x1E, ABX)])
add('BCC', [(0x90, REL)]); add('BCS', [(0xB0, REL)]); add('BEQ', [(0xF0, REL)]); add('BMI', [(0x30, REL)])
add('BNE', [(0xD0, REL)]); add('BPL', [(0x10, REL)]); add('BVC', [(0x50, REL)]); add('BVS', [(0x70, REL)])
add('BIT', [(0x24, ZP), (0x2C, ABS)])
add('BRK', [(0x00, IMP)])
add('CLC', [(0x18, IMP)]); add('CLD', [(0xD8, IMP)]); add('CLI', [(0x58, IMP)]); add('CLV', [(0xB8, IMP)])
add('CMP', [(0xC9, IMM), (0xC5, ZP), (0xD5, ZPX), (0xCD, ABS), (0xDD, ABX), (0xD9, ABY), (0xC1, IZX), (0xD1, IZY)])
add('CPX', [(0xE0, IMM), (0xE4, ZP), (0xEC, ABS)])
add('CPY', [(0xC0, IMM), (0xC4, ZP), (0xCC, ABS)])
add('DEC', [(0xC6, ZP), (0xD6, ZPX), (0xCE, ABS), (0xDE, ABX)])
add('DEX', [(0xCA, IMP)]); add('DEY', [(0x88, IMP)])
add('EOR', [(0x49, IMM), (0x45, ZP), (0x55, ZPX), (0x4D, ABS), (0x5D, ABX), (0x59, ABY), (0x41, IZX), (0x51, IZY)])
add('INC', [(0xE6, ZP), (0xF6, ZPX), (0xEE, ABS), (0xFE, ABX)])
add('INX', [(0xE8, IMP)]); add('INY', [(0xC8, IMP)])
add('JMP', [(0x4C, ABS), (0x6C, IND)])
add('JSR', [(0x20, ABS)])
add('LDA', [(0xA9, IMM), (0xA5, ZP), (0xB5, ZPX), (0xAD, ABS), (0xBD, ABX), (0xB9, ABY), (0xA1, IZX), (0xB1, IZY)])
add('LDX', [(0xA2, IMM), (0xA6, ZP), (0xB6, ZPY), (0xAE, ABS), (0xBE, ABY)])
add('LDY', [(0xA0, IMM), (0xA4, ZP), (0xB4, ZPX), (0xAC, ABS), (0xBC, ABX)])
add('LSR', [(0x4A, ACC), (0x46, ZP), (0x56, ZPX), (0x4E, ABS), (0x5E, ABX)])
add('NOP', [(0xEA, IMP)])
add('ORA', [(0x09, IMM), (0x05, ZP), (0x15, ZPX), (0x0D, ABS), (0x1D, ABX), (0x19, ABY), (0x01, IZX), (0x11, IZY)])
add('PHA', [(0x48, IMP)]); add('PHP', [(0x08, IMP)]); add('PLA', [(0x68, IMP)]); add('PLP', [(0x28, IMP)])
add('ROL', [(0x2A, ACC), (0x26, ZP), (0x36, ZPX), (0x2E, ABS), (0x3E, ABX)])
add('ROR', [(0x6A, ACC), (0x66, ZP), (0x76, ZPX), (0x6E, ABS), (0x7E, ABX)])
add('RTI', [(0x40, IMP)]); add('RTS', [(0x60, IMP)])
add('SBC', [(0xE9, IMM), (0xE5, ZP), (0xF5, ZPX), (0xED, ABS), (0xFD, ABX), (0xF9, ABY), (0xE1, IZX), (0xF1, IZY)])
add('SEC', [(0x38, IMP)]); add('SED', [(0xF8, IMP)]); add('SEI', [(0x78, IMP)])
add('STA', [(0x85, ZP), (0x95, ZPX), (0x8D, ABS), (0x9D, ABX), (0x99, ABY), (0x81, IZX), (0x91, IZY)])
add('STX', [(0x86, ZP), (0x96, ZPY), (0x8E, ABS)])
add('STY', [(0x84, ZP), (0x94, ZPX), (0x8C, ABS)])
add('TAX', [(0xAA, IMP)]); add('TAY', [(0xA8, IMP)]); add('TSX', [(0xBA, IMP)])
add('TXA', [(0x8A, IMP)]); add('TXS', [(0x9A, IMP)]); add('TYA', [(0x98, IMP)])


def load(path):
    d = open(path, 'rb').read()
    return d[16:16 + 8 * 0x4000]


def bank_bytes(prg, bank):
    return prg[bank * 0x4000:(bank + 1) * 0x4000]


def base_of(bank):
    return 0xC000 if bank == 7 else 0x8000


def dis_one(b, off, base):
    op = b[off]
    addr = base + off
    if op not in T:
        return 1, '.byte $%02X' % op
    m, mode = T[op]
    n = LEN[mode]
    if off + n > len(b):
        return 1, '.byte $%02X' % op
    lo = b[off + 1] if n > 1 else 0
    w = lo | (b[off + 2] << 8) if n > 2 else lo
    if mode == IMP: s = m
    elif mode == ACC: s = m + ' A'
    elif mode == IMM: s = '%s #$%02X' % (m, lo)
    elif mode == ZP: s = '%s $%02X' % (m, lo)
    elif mode == ZPX: s = '%s $%02X,X' % (m, lo)
    elif mode == ZPY: s = '%s $%02X,Y' % (m, lo)
    elif mode == ABS: s = '%s $%04X' % (m, w)
    elif mode == ABX: s = '%s $%04X,X' % (m, w)
    elif mode == ABY: s = '%s $%04X,Y' % (m, w)
    elif mode == IND: s = '%s ($%04X)' % (m, w)
    elif mode == IZX: s = '%s ($%02X,X)' % (m, lo)
    elif mode == IZY: s = '%s ($%02X),Y' % (m, lo)
    else:
        t = addr + 2 + (lo - 256 if lo > 127 else lo)
        s = '%s $%04X' % (m, t & 0xFFFF)
    return n, s


def dis_range(prg, bank, start, end):
    b = bank_bytes(prg, bank)
    base = base_of(bank)
    off = start - base
    out = []
    while off < end - base and off < len(b):
        n, s = dis_one(b, off, base)
        raw = ' '.join('%02X' % x for x in b[off:off + n])
        out.append('%d:%04X  %-9s %s' % (bank, base + off, raw, s))
        off += n
    return out


if __name__ == '__main__':
    prg = load(sys.argv[1])
    bank = int(sys.argv[2])
    start = int(sys.argv[3], 16)
    end = int(sys.argv[4], 16)
    print('\n'.join(dis_range(prg, bank, start, end)))
