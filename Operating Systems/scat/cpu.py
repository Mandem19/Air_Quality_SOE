import sys

import asm

mnemonics = {
    1: asm.type1,
    2: asm.type2,
    3: asm.type3,
    4: asm.type4,
    5: asm.type5}

s32 = lambda x: x if x<2**31 else x-2**32 # convert to signed
u32 = lambda x: x % 2**32                 # convert to unsigned

# In all of these functions:
# - 'x' always comes from a register, so it is unsigned, always
# - 'y' may be either a register (unsigned) or a *signed* immediate
# - the result will always be converted back to an "unsigned" before being written to the destination register
ALUOP = {
    "add": lambda x,y: x+y,
    "sub": lambda x,y: x-y,
    "mul": lambda x,y: x*y,
    "div": lambda x,y: s32(x) // s32(y), # python's integer division is "floored" 
    "mod": lambda x,y: s32(x) %  s32(y),
    "or" : lambda x,y: x|y,
    "xor": lambda x,y: x^y,
    "and": lambda x,y: x&y,
    "lsl": lambda x,y: x<<y if y<32 else 0,
    "lsr": lambda x,y: x>>y if y<32 else 0,
    "asr": lambda x,y: s32(x)>>y,
    "slt": lambda x,y: 1 if s32(x)<s32(y) else 0,
    "sltu":lambda x,y: 1 if u32(x)<u32(y) else 0,
}

for verb,func in list(ALUOP.items()):
    ALUOP[verb+"i"] = func
ALUOP["sltiu"] = ALUOP["sltu"]

COND = {
    "beq": lambda x,y: x == y,
    "bne": lambda x,y: x != y,
    "blt": lambda x,y: s32(x) <  s32(y),
    "bge": lambda x,y: s32(x) >= s32(y),
    "bltu":lambda x,y: x<u32(y), # 'x' is already unsigned
    }

def nibble(value, pos):
    assert pos%4 == 0
    return (value >> pos) & 0xF

class Registers(dict):
    def __init__(self):
        for i in range(16):
            self[i]=0
    def __setitem__(self, key, newvalue):
        if key==0: # ignore writes to R0
            super().__setitem__(key, 0)
            return
        super().__setitem__(key, newvalue)

# when the simulated program cannot execute further (e.g. memory
# error, division by zero, etc), we shall return to the prompt
class SimulatedError(Exception):
    pass

class CPU():
    def __init__(self,bus):
        self.bus=bus
        self.regs=Registers()

    def step(self):
        """Execute a single instruction"""
        
        IR=self.bus.read(self.regs[15],4) # Von Neumann Cycle: fetch
        # print(f"cpu: fetch(0x{self.regs[15]:08x})=0x{IR:08x}")

        # Von Neumann Cycle: decode
        ty  = nibble(IR,28)
        op  = nibble(IR,24)
        rd  = nibble(IR,20)
        rs  = nibble(IR,16)
        imm = IR & 0xFFFF
        if imm >= 2**15: imm-=2**16
        try:
            verb = mnemonics[ty][op]
        except : # either KeyError or IndexError
            raise SimulatedError(f"CPU error: illegal instruction: 0x{IR:08x}")

        # Von Neumann Cycle: execute
        if ty == 1:
            # reg-reg ALU
            rs2=nibble(IR,12)
            if verb in ["div","mod"] and self.regs[rs2] == 0:
                raise SimulatedError("CPU error: division by zero")
            self.regs[rd] = u32(ALUOP[verb]( self.regs[rs], self.regs[rs2]))
            if rd != 15: self.regs[15] += 4
            return 

        elif ty == 2:
            # reg-imm ALU
            if verb in ["lsli","lsri","asri"] and imm<0:
                raise SimulatedError(f"CPU error: illegal negative shift count: '{imm}'")
            self.regs[rd] = u32(ALUOP[verb]( self.regs[rs], imm))
            if rd != 15: self.regs[15] += 4
            return 

        elif ty == 3:
            # conditional jump
            if COND[verb](self.regs[rd], self.regs[rs]):
                self.regs[15] += imm
            else:
                self.regs[15] += 4
            return
        
        elif ty==4:
            if op == 0: # load
                self.regs[rd] = self.bus.read(self.regs[rs]+imm, 4)
                if rd != 15: self.regs[15] += 4
                return
            else: # store
                self.bus.write(self.regs[rd]+imm, self.regs[rs])
                self.regs[15] += 4
                return

        elif ty == 5:
            # Jump-And-Link
            tmp = self.regs[15] 
            self.regs[rd] = u32(self.regs[15] + 4)
            self.regs[15] = u32(self.regs[rs] + imm )
            return

        assert False # this is a bug in the SCAT simulator

    def dumpregs(self):
        width07 = max([len(str(s32(self.regs[i]))) for i in range(0,8) ])
        width07 = max(width07, 3) # allow room for 'dec' header
        width07 += 1 # one space to separate columns

        width8F = max([len(str(s32(self.regs[i]))) for i in range(8,16) ])
        width8F = max(width8F, 3) # allow room for 'dec' header
        width8F += 1 # one space to separate columns
        
        print(( "name"+
                "      hex "+
                "dec".rjust(width07)+
                "       "+
                "name"+
                "      hex "+
                "dec".rjust(width8F)
               ).strip())
        
        for i in range(0,8):
            vali=self.regs[i]
            valj=self.regs[i+8]
            print( f"R{i}".rjust(4)
                  +f" {vali:08x}"
                  +f" {s32(vali):{width07}d}"
                  +"       "
                  +(f"R{i+8}".rjust(4) if i<7 else "  PC")
                  +f" {valj:08x}"
                  +(f" {s32(valj):{width8F}d}" if i<7 else "")
                  )

# example output:

# name      hex   dec       name      hex          dec
#   R0 00000000     0         R8 00000b40         2880
#   R1 00000009     9         R9 b0000000  -1342177280
#   R2 ffffffff    -1        R10 ffffffff           -1
#   R3 fffffffe    -2        R11 0000011c          284
#   R4 fffffffc    -4        R12 00000000            0
#   R5 000007bc  1980        R13 00000000            0
#   R6 00000a00  2560        R14 00000000            0
#   R7 000000a8   168         PC 00000030

