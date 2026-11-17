"""Minimal headless NES (UxROM, logic only, no PPU rendering) for poking at game state."""
import copy
from dis import T, IMP, ACC, IMM, ZP, ZPX, ZPY, ABS, ABX, ABY, IND, IZX, IZY, REL

A_, B_, SEL, START, UP, DOWN, LEFT, RIGHT = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01

BASE_CYC = {IMP: 2, ACC: 2, IMM: 2, ZP: 3, ZPX: 4, ZPY: 4, ABS: 4, ABX: 4, ABY: 4, IND: 5, IZX: 6, IZY: 5, REL: 2}
RMW = {'ASL', 'LSR', 'ROL', 'ROR', 'INC', 'DEC'}
FRAME_CYCLES = 29781


class NES:
    def __init__(self, path):
        d = open(path, 'rb').read()
        self.prg = d[16:16 + 8 * 0x4000]
        self.ram = bytearray(0x800)
        self.bank = 0
        self.a = self.x = self.y = 0
        self.sp = 0xFD
        self.c = self.z = self.i = self.d = self.v = self.n = 0
        self.i = 1
        self.nmi_enable = 0
        self.vbl = False
        self.pad = [0, 0]
        self.latch = [0, 0]
        self.strobe = 0
        self.cyc = 0
        self.frames = 0
        self.pc = self.rd16(0xFFFC)
        self.table = [None] * 256
        for op, (m, mode) in T.items():
            cyc = BASE_CYC[mode]
            if m in RMW and mode != ACC:
                cyc += 2
            if m in ('JSR', 'RTS', 'RTI'):
                cyc = 6
            if m == 'JMP':
                cyc = 3 if mode == ABS else 5
            if m in ('PHA', 'PHP'):
                cyc = 3
            if m in ('PLA', 'PLP'):
                cyc = 4
            if m == 'BRK':
                cyc = 7
            if m in ('STA',) and mode in (ABX, ABY):
                cyc = 5
            if m == 'STA' and mode == IZY:
                cyc = 6
            self.table[op] = (getattr(self, 'op_' + m), mode, cyc)

    # ---- memory
    def rd(self, addr):
        if addr < 0x2000:
            return self.ram[addr & 0x7FF]
        if addr >= 0xC000:
            return self.prg[0x10000 + addr]
        if addr >= 0x8000:
            return self.prg[self.bank * 0x4000 + addr - 0x8000]
        if addr < 0x4000:
            if addr & 7 == 2:
                v = 0x80 if self.vbl else 0
                self.vbl = False
                return v
            return 0
        if addr == 0x4016 or addr == 0x4017:
            k = addr - 0x4016
            if self.strobe:
                return 0x40 | ((self.pad[k] >> 7) & 1)
            b = (self.latch[k] >> 7) & 1
            self.latch[k] = ((self.latch[k] << 1) | 1) & 0xFF
            return 0x40 | b
        return 0

    def rd16(self, addr):
        return self.rd(addr) | (self.rd(addr + 1) << 8)

    def wr(self, addr, v):
        if addr < 0x2000:
            self.ram[addr & 0x7FF] = v
        elif addr >= 0x8000:
            self.bank = v & 7
        elif addr < 0x4000:
            if addr & 7 == 0:
                self.nmi_enable = v & 0x80
        elif addr == 0x4016:
            if self.strobe and not (v & 1):
                self.latch = list(self.pad)
            self.strobe = v & 1

    # ---- stack
    def push(self, v):
        self.ram[0x100 + self.sp] = v
        self.sp = (self.sp - 1) & 0xFF

    def pop(self):
        self.sp = (self.sp + 1) & 0xFF
        return self.ram[0x100 + self.sp]

    def getp(self):
        return self.c | (self.z << 1) | (self.i << 2) | (self.d << 3) | 0x20 | (self.v << 6) | (self.n << 7)

    def setp(self, p):
        self.c = p & 1
        self.z = (p >> 1) & 1
        self.i = (p >> 2) & 1
        self.d = (p >> 3) & 1
        self.v = (p >> 6) & 1
        self.n = (p >> 7) & 1

    def nz(self, v):
        self.z = 1 if v == 0 else 0
        self.n = v >> 7
        return v

    # ---- addressing
    def ea(self, mode):
        pc = self.pc
        if mode == ZP:
            self.pc = pc + 1
            return self.rd(pc)
        if mode == ABS:
            self.pc = pc + 2
            return self.rd(pc) | (self.rd(pc + 1) << 8)
        if mode == ZPX:
            self.pc = pc + 1
            return (self.rd(pc) + self.x) & 0xFF
        if mode == ZPY:
            self.pc = pc + 1
            return (self.rd(pc) + self.y) & 0xFF
        if mode == ABX:
            self.pc = pc + 2
            return ((self.rd(pc) | (self.rd(pc + 1) << 8)) + self.x) & 0xFFFF
        if mode == ABY:
            self.pc = pc + 2
            return ((self.rd(pc) | (self.rd(pc + 1) << 8)) + self.y) & 0xFFFF
        if mode == IZY:
            self.pc = pc + 1
            zp = self.rd(pc)
            return ((self.ram[zp] | (self.ram[(zp + 1) & 0xFF] << 8)) + self.y) & 0xFFFF
        if mode == IZX:
            self.pc = pc + 1
            zp = (self.rd(pc) + self.x) & 0xFF
            return self.ram[zp] | (self.ram[(zp + 1) & 0xFF] << 8)
        raise RuntimeError('bad mode')

    def val(self, mode):
        if mode == IMM:
            v = self.rd(self.pc)
            self.pc += 1
            return v
        return self.rd(self.ea(mode))

    # ---- ops
    def op_LDA(self, m): self.a = self.nz(self.val(m))
    def op_LDX(self, m): self.x = self.nz(self.val(m))
    def op_LDY(self, m): self.y = self.nz(self.val(m))
    def op_STA(self, m): self.wr(self.ea(m), self.a)
    def op_STX(self, m): self.wr(self.ea(m), self.x)
    def op_STY(self, m): self.wr(self.ea(m), self.y)
    def op_TAX(self, m): self.x = self.nz(self.a)
    def op_TAY(self, m): self.y = self.nz(self.a)
    def op_TXA(self, m): self.a = self.nz(self.x)
    def op_TYA(self, m): self.a = self.nz(self.y)
    def op_TSX(self, m): self.x = self.nz(self.sp)
    def op_TXS(self, m): self.sp = self.x
    def op_INX(self, m): self.x = self.nz((self.x + 1) & 0xFF)
    def op_INY(self, m): self.y = self.nz((self.y + 1) & 0xFF)
    def op_DEX(self, m): self.x = self.nz((self.x - 1) & 0xFF)
    def op_DEY(self, m): self.y = self.nz((self.y - 1) & 0xFF)
    def op_CLC(self, m): self.c = 0
    def op_SEC(self, m): self.c = 1
    def op_CLD(self, m): self.d = 0
    def op_SED(self, m): self.d = 1
    def op_CLI(self, m): self.i = 0
    def op_SEI(self, m): self.i = 1
    def op_CLV(self, m): self.v = 0
    def op_NOP(self, m): pass
    def op_PHA(self, m): self.push(self.a)
    def op_PLA(self, m): self.a = self.nz(self.pop())
    def op_PHP(self, m): self.push(self.getp() | 0x10)
    def op_PLP(self, m): self.setp(self.pop())
    def op_AND(self, m): self.a = self.nz(self.a & self.val(m))
    def op_ORA(self, m): self.a = self.nz(self.a | self.val(m))
    def op_EOR(self, m): self.a = self.nz(self.a ^ self.val(m))

    def op_ADC(self, m):
        v = self.val(m)
        s = self.a + v + self.c
        self.v = 1 if (~(self.a ^ v) & (self.a ^ s) & 0x80) else 0
        self.c = 1 if s > 0xFF else 0
        self.a = self.nz(s & 0xFF)

    def op_SBC(self, m):
        v = self.val(m) ^ 0xFF
        s = self.a + v + self.c
        self.v = 1 if (~(self.a ^ v) & (self.a ^ s) & 0x80) else 0
        self.c = 1 if s > 0xFF else 0
        self.a = self.nz(s & 0xFF)

    def cmp(self, r, v):
        self.c = 1 if r >= v else 0
        self.nz((r - v) & 0xFF)

    def op_CMP(self, m): self.cmp(self.a, self.val(m))
    def op_CPX(self, m): self.cmp(self.x, self.val(m))
    def op_CPY(self, m): self.cmp(self.y, self.val(m))

    def op_BIT(self, m):
        v = self.val(m)
        self.z = 1 if (v & self.a) == 0 else 0
        self.n = v >> 7
        self.v = (v >> 6) & 1

    def rmw(self, m, f):
        if m == ACC:
            self.a = self.nz(f(self.a))
        else:
            addr = self.ea(m)
            self.wr(addr, self.nz(f(self.rd(addr))))

    def _asl(self, v):
        self.c = v >> 7
        return (v << 1) & 0xFF

    def _lsr(self, v):
        self.c = v & 1
        return v >> 1

    def _rol(self, v):
        r = ((v << 1) | self.c) & 0xFF
        self.c = v >> 7
        return r

    def _ror(self, v):
        r = (v >> 1) | (self.c << 7)
        self.c = v & 1
        return r

    def op_ASL(self, m): self.rmw(m, self._asl)
    def op_LSR(self, m): self.rmw(m, self._lsr)
    def op_ROL(self, m): self.rmw(m, self._rol)
    def op_ROR(self, m): self.rmw(m, self._ror)
    def op_INC(self, m): self.rmw(m, lambda v: (v + 1) & 0xFF)
    def op_DEC(self, m): self.rmw(m, lambda v: (v - 1) & 0xFF)

    def branch(self, cond):
        off = self.rd(self.pc)
        self.pc += 1
        if cond:
            self.pc = (self.pc + (off - 256 if off > 127 else off)) & 0xFFFF
            self.cyc += 1

    def op_BCC(self, m): self.branch(not self.c)
    def op_BCS(self, m): self.branch(self.c)
    def op_BEQ(self, m): self.branch(self.z)
    def op_BNE(self, m): self.branch(not self.z)
    def op_BMI(self, m): self.branch(self.n)
    def op_BPL(self, m): self.branch(not self.n)
    def op_BVC(self, m): self.branch(not self.v)
    def op_BVS(self, m): self.branch(self.v)

    def op_JMP(self, m):
        t = self.rd(self.pc) | (self.rd(self.pc + 1) << 8)
        if m == IND:
            t = self.rd(t) | (self.rd((t & 0xFF00) | ((t + 1) & 0xFF)) << 8)
        self.pc = t

    def op_JSR(self, m):
        t = self.rd(self.pc) | (self.rd(self.pc + 1) << 8)
        r = self.pc + 1
        self.push(r >> 8)
        self.push(r & 0xFF)
        self.pc = t

    def op_RTS(self, m):
        lo = self.pop()
        self.pc = ((self.pop() << 8) | lo) + 1

    def op_RTI(self, m):
        self.setp(self.pop())
        lo = self.pop()
        self.pc = (self.pop() << 8) | lo

    def op_BRK(self, m):
        raise RuntimeError('BRK at %04X bank %d' % (self.pc - 1, self.bank))

    # ---- run
    def nmi(self):
        self.push(self.pc >> 8)
        self.push(self.pc & 0xFF)
        self.push(self.getp())
        self.i = 1
        self.pc = self.rd16(0xFFFA)
        self.cyc += 7

    def frame(self, p1=0, p2=0):
        self.pad = [p1, p2]
        self.vbl = True
        self.cyc -= FRAME_CYCLES if self.cyc >= FRAME_CYCLES else self.cyc
        if self.nmi_enable:
            self.nmi()
        table = self.table
        ram = self.ram
        while self.cyc < FRAME_CYCLES:
            pc = self.pc
            if pc == 0xC057:
                # idle loop: $34 += $1A (+carry), 12 cycles per pass
                n = (FRAME_CYCLES - self.cyc + 11) // 12
                a = ram[0x1A]
                s = ram[0x34]
                c = self.c
                for _ in range(n):
                    t = a + s + c
                    c = 1 if t > 0xFF else 0
                    s = t & 0xFF
                ram[0x34] = s
                self.c = c
                self.a = s
                self.cyc += n * 12
                break
            op = self.rd(pc)
            self.ipc = pc
            self.pc = pc + 1
            e = table[op]
            if e is None:
                raise RuntimeError('illegal opcode %02X at %04X bank %d' % (op, pc, self.bank))
            e[0](e[1])
            self.cyc += e[2]
        self.frames += 1

    def snapshot(self):
        return (bytes(self.ram), self.bank, self.a, self.x, self.y, self.sp, self.pc, self.getp(),
                self.nmi_enable, self.vbl, list(self.latch), self.strobe, self.cyc, self.frames)

    def restore(self, s):
        self.ram[:] = s[0]
        (self.bank, self.a, self.x, self.y, self.sp, self.pc) = s[1:7]
        self.setp(s[7])
        self.nmi_enable, self.vbl = s[8], s[9]
        self.latch = list(s[10])
        self.strobe, self.cyc, self.frames = s[11], s[12], s[13]
