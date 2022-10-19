#!/usr/bin/env python3

import argparse
import math
import os
import sys
import re

# base instructions (i.e. not pseudo-instructions)
type1=["add",  "sub",   "mul",  "div",  "mod",  "or",  "and",  "xor",  "lsl",  "lsr",  "asr",  "slt",  "sltu" ]
type2=["addi", "subi",  "muli", "divi", "modi", "ori", "andi", "xori", "lsli", "lsri", "asri", "slti", "sltiu" ]
type3=["beq",  "bne",   "blt",  "bge",  "bltu", "bgeu" ]
type4=["load", "store"]
type5=["jal"]

pseudo_jumps = ["beqz", "bnez", "blez", "bgez",  "bltz", "bgtz", "bgt", "ble", "bgtu", "bleu","bra" ]
type_pseudo = (["leti","push","pop","dec","inc","mov","nop",
                "not","neg","seqz","snez","sltz","sgtz", "jmp", "call", "ret"]
            +pseudo_jumps)

reg_names = [ "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15" ]
alias_names = ["zero", "pc", "lr", "sp" ]

def error(message,lnum=None):
    # most error messages complain about the current line.
    # however when resolving label addresses we show the original instruction
    if lnum == None:
        lnum = linenum
    try:
        print(f"{asmfilename}:{lnum}: {message}")
        print(f"line {lnum}: {asmlines[lnum]}")
    except:
        print(message)
        raise
    # raise Exception()
    sys.exit(1)

class MemoryWord():
    def __init__(self, value):
        self.linenum = linenum
        if isinstance(value, int):
            self.value = value
        elif isinstance(value, str):
            self.value = parse_integer_literal(value)
        else:
            error("Cannot understand integer constant: '{value}'")
        if self.value >= 2**32:
            error(f"Value does not fit on 32 bits: '{value}'")

    def encode(self):
        """return value encoded in two's complement on 32 bits"""
        return self.value & ((2**32) - 1)

class Instruction():
    def __init__(self, line):
        self.linenum = linenum
        self.code = dict() # maps bit positions to hex nibbles

        # Some instructions (cond jumps, branches, load) accept a
        # label as an argument. For these we use the addressing mode
        # PC+offset, but we can only compute the offset once all
        # labels are known. This is done via the `resolve()` method.
        self.target = None  
        self.addr = exe.cur_addr # used in resolve()

        line=line.strip()
        if " " in line:
            firstspace=line.index(" ")
            self.words = [line[:firstspace]]
            rest = line[firstspace+1:]
        else:
            self.words=[line]
            rest = None
            
        if self.words[0] not in type1+type2+type3+type4+type5+type_pseudo:
            error("Invalid instruction name '"+self.words[0]+"'")

        if rest:
            self.words += [ w.strip() for w in rest.split(",")]
            for rank,text in enumerate(self.words):
                if len(text) == 0:
                    error(f"Operand number {rank} of '{self.words[0]}' is empty")
        
    def check_args(self,expected_arg_count):
        argc = len(self.words)-1
        if   argc < expected_arg_count:
            error(f"Not enough operands for '{self.words[0]}'")
        elif argc > expected_arg_count:
            error(f"Too many operands for '{self.words[0]}'")
        return self.words[1:]

    def resolve(self):
        if self.target is None:
            return # nothing to resolve
        try:
            target_addr = exe.symbols[self.target]
        except KeyError:
            error(f"Cannot resolve symbol: '{self.target}'",self.linenum)

        offset = target_addr - self.addr

        if offset < -2**15 or offset >= 2**15:
            linenum=self.linenum
            error(f"Distance from {hex(self.addr)} to "
                  f"'{self.target}' at {hex(target_addr)} does not fit on 16-bits",self.linenum)

        self.code[0]=target_addr - self.addr

    def encode(self):
        self.resolve()
        value = 0
        if 0 in self.code:
            imm = self.code[0]
            if imm<0: imm += 2**16
            if not 0 <= imm < 2**16:
                error(f"Integer constant is larger than 16-bits: {self.code[0]}",self.linenum)
            self.code[0] = imm

        for pos in self.code:
            value |= self.code[pos] << pos
        # print(", ".join(f'{of}:{self.code[of]:x}' for of in sorted(self.code,reverse=True)))
        assert value>=0
        return value

def parse_register(text):
    """Interpret a string as a register number: zero/r0 -> 0, r1 -> 1 etc"""
    aliases= { "zero": 0, "pc": 15, "sp":13, "lr": 14 }
    if text in aliases:
        return aliases[text]
    if text not in reg_names:
        error(f"Incorrect register name '{text}'")
    return reg_names.index(text)

def parse_integer_literal(text):
    if len(text) == 0:
        error(f"Empty string not allowed here")
    if " " in text:
        error(f"No whitespace allowed in integer constant: '{text}'")
    if "--" in text:
        error(f"Duplicate sign: '{text}'")
    if "+" in text:
        error(f"Plus sign not allowed here: '{text}'")
    elif len(text)>3 and text[:3] == '-0b':
        error(f"Sign not allowed in binary constant: '{text}'")
    elif len(text)>3 and text[:3] == '-0x':
        error(f"Sign not allowed in hex constant: '{text}'")
    elif len(text)>1 and text[0] == '-':
        return - parse_integer_literal(text[1:])
    elif ( len(text)>2 and text[:2] == '0x'
           and all([letter in "1234567890abcdef" for letter in text[2:]])):
         # hexadecimal literal
        return int(text[2:],16)
    elif (len(text)>2 and text[:2] == '0b'
          and all([letter in "01" for letter in text[2:]])):
        # binary literal
        return int(text[2:],2) 
    elif all([letter in "1234567890" for letter in text]):
         # positive decimal
        return int(text,10)

    error(f"Cannot understand integer constant: '{text}'")

def parse_jump_distance(text):
    """Recognize +12, -4, etc. Choke on numbers wider than 16-bits"""
    if text[0] not in "+-":
        error("Jump offset must start with either '+' or '-'")
    distance=parse_integer_literal(text[1:])
    if distance%4 != 0:
        error("Jump distance must be a multiple of 4")
    if text[0]=='-':
        distance *= -1
    if distance < -2**15 or distance >= 2**15:
        error("Jump distance is too large")
    return distance
 
def check_generic_args(line,expected_arg_count):
    """check the number of arguments in 'line', return them as a list of strings"""
    return Instruction(line).check_args(expected_arg_count)

class Instruction_Type1(Instruction):
    def __init__(self, line):
        super().__init__(line)
        self.code[28] = 1
        self.code[24] = type1.index( self.words[0] )
        rd, rs1, rs2 = self.check_args(3)
        self.code[20] = parse_register( rd  )
        self.code[16] = parse_register( rs1 )
        self.code[12] = parse_register( rs2 )

class Instruction_Type2(Instruction):
    def __init__(self, line):
        super().__init__(line)
        self.code[28] = 2
        self.code[24] = type2.index( self.words[0] )
        rd, rs1, imm = self.check_args(3)
        self.code[20] = parse_register( rd )
        self.code[16] = parse_register( rs1 )
        value = parse_integer_literal( imm )
        if imm[:2] in ['0x','0b']: # binary or hexadecimal notation
            if value >= 2**16:
                error(f"Integer constant does not fit in 16-bits: '{imm}'")
            if imm[:2] == '0x' and len(imm)>6:
                error(f"Integer constant is too long: '{imm}'")

        else: # decimal notation is implicitely "signed"
            if not -2**15 <= value < 2**15:
                error(f"Integer constant does not fit in 16-bits: '{imm}'")
        if self.words[0] in ["lsli","lsri","asri"] and value<0:
            error(f"Shift count cannot be negative: '{imm}'")
        self.code[0] = value
        
def parse_label(text, noerror=False):
    text=text.strip()
    m = re.match('[a-zA-Z_][a-zA-Z0-9_]*$',text)
    if ( m is None or text in type1+type2+type3+type4+type_pseudo+reg_names+alias_names):
        if noerror:
            return None
        error(f"Invalid label name: '{text}'")
    return text

class Instruction_Type3(Instruction):
    def __init__(self, line):
        super().__init__(line)
        self.code[28] = 3
        self.code[24] = type3.index( self.words[0] )
        rd, rs1, destop = self.check_args(3)
        self.code[20] = parse_register( rd )
        self.code[16] = parse_register( rs1 )

        if destop[0] in "+-":
            self.code[0] = parse_jump_distance(destop)
        else:
            self.target = parse_label(destop)

class Instruction_Bra(Instruction):
    def __init__(self,line):
        super().__init__(line)
        destop = self.check_args(1)[0]
        self.code[28]=2  # type 2
        self.code[24]=0  # opcode for "addi"
        self.code[20]=15 # rd = PC
        self.code[16]=15 # rs = PC
        if destop[0] in "+-":
            self.code[0] = parse_jump_distance(destop)
        else:
            self.target = parse_label(destop)

def process_pseudo_jump(line):
    verb,rest=line.split(maxsplit=1)

    if verb == "bra":        exe.add(Instruction_Bra(line))
    elif verb[-1] == "z": # comparison with zero: let's rewrite by using "r0" explicitely
        reg,dest = check_generic_args(line, 2)
        if   verb == "beqz": exe.add(Instruction_Type3(f"beq {reg}, zero, {dest}"))
        elif verb == "bnez": exe.add(Instruction_Type3(f"bne {reg}, zero, {dest}"))
        elif verb == "blez": exe.add(Instruction_Type3(f"bge zero, {reg}, {dest}"))
        elif verb == "bgez": exe.add(Instruction_Type3(f"bge {reg}, zero, {dest}"))
        elif verb == "bltz": exe.add(Instruction_Type3(f"blt {reg}, zero, {dest}"))
        elif verb == "bgtz": exe.add(Instruction_Type3(f"blt zero, {reg}, {dest}"))
        else: error("Don't know how to rewrite this pseudo-instruction")
    else: # other cases: let's rewrite by swapping operands
        r1,r2,dest=check_generic_args(line, 3)
        if   verb == "bgt":  exe.add(Instruction_Type3(f"blt  {r2}, {r1}, {dest}"))
        elif verb == "ble":  exe.add(Instruction_Type3(f"bge  {r2}, {r1}, {dest}"))
        elif verb == "bgtu": exe.add(Instruction_Type3(f"bltu {r2}, {r1}, {dest}"))
        elif verb == "bleu": exe.add(Instruction_Type3(f"bgeu {r2}, {r1}, {dest}"))
        else: error("Don't know how to rewrite this pseudo-instruction")
    
def parse_memory_operand_reg(text):
    """Interpret text as a memory operand, return a pair (regnum, offset)"""
    # text is an "indirect address" argument e.g. [r3], [zero-1] or [pc+4]
    if text[0] != '[' or text[-1] != ']':
        error(f"Invalid syntax for memory operand '{text}'")
    text=text[1:-1].strip() # remove brackets

    if "+" not in text and "-" not in text:
        # easy case e.g. [r3] without offset
        return parse_register(text), 0

    if text.count('+') + text.count('-') > 1:
        error(f"Too many signs: '{text}'")
      
    if '+' in text:
        pos    = text.index('+')
        sign = 1
    else:
        pos = text.index('-')
        sign = -1
        
    reg    = parse_register( text[:pos].strip())
    offset = sign * parse_integer_literal( text[pos+1:].strip() ) 
    if not -2**15 <= offset < 2**15:
        error(f"Offset is too large: '{text[pos:]}'")
    return  reg , offset 

def parse_memory_operand_label(text):
    if text[0] != '[' or text[-1] != ']':
        error(f"Invalid syntax for memory operand '{text}'")
    text=text[1:-1].strip() # remove brackets

    if "+" not in text and "-" not in text:
        if not parse_label(text, noerror=True):
            return False,0
        return text,0 

    if text.count('+') + text.count('-') > 1:
        error(f"Too many signs: '{text}'")
        
    if '+' in text:
        pos  = text.index('+')
        sign = 1
    else:
        pos  = text.index('-')
        sign = -1
        
    name = text[:pos].strip()
    if not parse_label(name, noerror=True):
        return False,0
    offset = sign * parse_integer_literal( text[pos+1:].strip() )
    if not -2**15 <= offset < 2**15:
        error(f"Offset is too large: '{text[pos:]}'")
    return name,offset
    
class Instruction_Load(Instruction):
    def __init__(self, line):
        super().__init__(line)
        self.code[28] = 4 # Type4
        self.code[24] = 0
        rd, memop = self.check_args(2)
        if "[" in rd and not "[" in memop:
            error("Memory operand must be the second argument")
        self.code[20] = parse_register( rd )
        name,offset = parse_memory_operand_label(memop) # 
        if name:
            self.code[16]=15 # symbolic labels are always referenced through PC
            self.target = name
            self.offset = offset # additional offset w.r.t target
        else:
            self.code[16], self.code[0] = parse_memory_operand_reg( memop )
            
    def resolve(self):
        if self.target is None:
            return
        super().resolve()
        # sometimes `super().resolve()` will complain because the distance is
        # too large, even though adding `self.offset` would be enough to
        # correct it. In practice this will be harmless so we don't care.
        self.code[0] += self.offset
        
class Instruction_Store(Instruction):
    def __init__(self, line):
        super().__init__(line)
        self.code[28] = 4 # Type4
        self.code[24] = 1
        memop, rs = self.check_args(2)
        if "[" in rs and not "[" in memop:
            error("Memory operand must be the first argument")
        self.code[16] = parse_register( rs )

        name,offset = parse_memory_operand_label(memop) # 
        if name:
            self.code[20]=15 # symbolic labels are always referenced through PC
            self.target = name
            self.offset = offset
        else:
            self.code[20], self.code[0] = parse_memory_operand_reg( memop )

    def resolve(self):
        if self.target is None:
            return
        super().resolve()
        # sometimes `super().resolve()` will complain because the distance is
        # too large, even though adding `self.offset` would be enough to
        # correct it. In practice this will be harmless so we don't care.
        self.code[0] += self.offset

class Instruction_Jal(Instruction):
    def __init__(self,line):
        super().__init__(line)
        if len(self.words) == 3: # e.g. "jal Ri, rj" 
            rd, rs1, destop = self.check_args(2) + ["+0"]
        elif len(self.words) == 4:
            rd, rs1, destop = self.check_args(3)

        self.code[28] = 5
        self.code[24] = 0
        self.code[20] = parse_register( rd )
        self.code[16] = parse_register( rs1 )
        if destop[0] in "+-": # explicit offset e.g. "jump +0"
            self.code[0] = parse_jump_distance(destop)
        else: # normal case: destop is just a label name
            if parse_register(rs1) != 15:
                error(f"Invalid base register '{rs1}'. You should use r15.")
            self.target = parse_label( destop ) # jump destination

class Instruction_Leti_Label(Instruction):
    def __init__(self, line):
        super().__init__(line)
        self.code[28] = 2
        self.code[24] = type2.index( "addi" )
        rd, label = self.check_args(2)
        self.code[20] = parse_register( rd )
        self.code[16] = 15  # symbolic labels are always referenced through PC
        self.target = parse_label( label )

def process_leti(line):
    reg,cst = check_generic_args(line, 2)

    if cst[0] not in "1234567890-+":
        # then "cst" must be a label name
        exe.add( Instruction_Leti_Label(line))
        return

    # GS-2022-09-20-16:48 hack to avoid sign-extension shenanigans in
    # non-number hex constants e.g. RGB triplets like 0x0000FF00
    wide_hex_constant = False
    if len(cst)>6 and cst[:2] == '0x':
        wide_hex_constant = True
            
    value   = parse_integer_literal(cst)
    if not -2**31 <= value < 2**32:
        error(f"Integer constant larger than 32-bits: '{cst}'")

    if value >= 2**31: value -= 2**32 # convert to signed

    if -2**15 <= value < 2**16 and not wide_hex_constant:   # small literal (in absolute value)
        exe.add( Instruction_Type2(f"addi {reg}, zero, 0x{value%2**16:x}"))
        return

    # our number is larger (in absolute value) than 2**16.
    # we'll have to emit a sequence of several instructions
    value = value % 2**32 # convert back to unsigned
    ranks = [pos for pos in range(32) if value&(2**pos)]
    msb,lsb=max(ranks),min(ranks) # most/least significant bit positions
    if msb-lsb+1 < 16 or (msb-lsb+1 == 16 and msb==31):
        # "narrow" number: we can get it into place with only two instructions
        exe.add( Instruction_Type2(f"addi {reg}, zero, 0x{value>>lsb:x}"))
        # note: when msb==31, there *is* noise in 'reg' after the 'addi'
        # but the shift-left will push it all beyond the left end.
        exe.add( Instruction_Type2(f"lsli {reg}, {reg}, {lsb}"),pseudo=True)
        return

    # "wide" number, with more than 16 bits of actual data. We'll need 3+ instructions
    exe.add( Instruction_Type2(f"addi {reg}, zero, 0x{value>>16:x}"))
    if not value&0x8000: # no "sign bit" problem, we can load both halves verbatim
        exe.add( Instruction_Type2(f"lsli {reg}, {reg}, 16"),pseudo=True)
        exe.add( Instruction_Type2(f"addi {reg}, {reg}, 0x{value & 0xFFFF:x}"),pseudo=True)
        return

    # let's be careful and avoid any sign extension bugs
    exe.add( Instruction_Type2(f"lsli {reg}, {reg}, 4"),pseudo=True)
    exe.add( Instruction_Type2(f"addi {reg}, {reg}, 0x{(value&0xFFFF)>>12:x}"),pseudo=True)
    exe.add( Instruction_Type2(f"lsli {reg}, {reg}, 12"),pseudo=True)
    exe.add( Instruction_Type2(f"addi {reg}, {reg}, 0x{value & 0x0FFF:x}"),pseudo=True)



class Executable():
    def __init__(self):
        self.contents = dict() # maps addresses to 32-bits codewords
        self.cur_addr = 0      # next position to append an instruction to
        self.symbols  = dict() # maps identifiers to addresses

    def add(self, thing, pseudo=False):
        """Append something to the executable and advance cursor position"""
        if pseudo:
            thing.linenum=0 # so that our objdump() will print nothing
        address = self.cur_addr
        if address in self.contents:
            error(f"Internal error: duplicate address {address} in program")
        self.contents[address] = thing
        self.cur_addr     += 4
        
    def add_label(self, name):
        if name in self.symbols:
            error(f"Label '{name}' is already defined")
        self.symbols[name] = self.cur_addr

    def addrwidth(self):
        res = len("%x" % max(self.contents.keys()))
        res = 2*(1+(res-1)//2)     # an even number of digits looks prettier
        return res

    def encode(self, explicit_addresses=False):
        res = ""
        addresses = sorted(self.contents.keys())

        if addresses == []:
            return ""
        
        # when the executable is a contiguous program, contents
        # implicitely starts at zero and we don't show addresses
        #
        # However for hollow binaries (e.g. with .space/.align) we
        # don't want to spam the file with zeroes so we use a
        # different file format.
        
        explicit_addresses = ( explicit_addresses or min(addresses) > 0
                               or len(addresses) != (max(addresses)-min(addresses))/4+1
                               or addresses != list(range(min(addresses),max(addresses)+1,4)))
        
        for a in addresses:
            if explicit_addresses:
                res+= f"{a:0{self.addrwidth()}x}: "
            res +=f"{self.contents[a].encode():08x}"
            res += "\n"
        return res.strip('\n')

    def objdump(self):
        
        if self.symbols:
            labelwidth = max(len(name) for name in self.symbols)
            labelwidth = max(labelwidth, self.addrwidth()-2)
        else:
            labelwidth = 0

        res=""
        for pos,thing in self.contents.items():
            if pos in self.symbols.values():
                for name in sorted([ name for name,value in self.symbols.items() if value==pos]):
                    res+= f"<{name}>:".rjust(labelwidth+3)+"\n"

            res += f"{pos:0{self.addrwidth()}x}: ".rjust(labelwidth+4)
            bi = f"{thing.encode():08x}"
            res +=f"{bi[0:2]} {bi[2:4]} {bi[4:6]} {bi[6:8]}"
            res += " "*4
            # we remove original comments as they don't make much sense in this view
            res += asmlines[thing.linenum].split(';')[0].strip() 
            res += '\n'
        return res

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-q","--quiet", help="Write output to files but not to the screen",action="store_true")
    argparser.add_argument("asmfilename",metavar='ASMFILE',help="path to input file")
    args=argparser.parse_args()

    if not os.path.exists(args.asmfilename):
        print(f"{argparser.prog}: cannot find file '{args.asmfilename}'")
        sys.exit(1)

    if args.asmfilename[-2:] != ".s":
        print(f"{argparser.prog}: incorrect filename suffix '{args.asmfilename}' (expected .s)")
        sys.exit(1)

    global asmfilename
    asmfilename=args.asmfilename

    exefile = args.asmfilename.replace('.s','.exe')
    lstfile = args.asmfilename.replace('.s','.lst')

    # remove old files to reduce confusion in case of a syntax error
    if os.path.exists(exefile): os.unlink(exefile) 
    if os.path.exists(lstfile): os.unlink(lstfile)
    
    f=open(args.asmfilename)
    global asmlines
    asmlines=[""]+f.read().splitlines()
    global linenum
    
    exe = Executable()
    
    for linenum,line in enumerate(asmlines):

        # ignore comments
        if ';' in line:
            line = line[ :line.find(';') ]

        # fix whitespace and case
        line = line.strip().lower()
        
        # labels
        if ':' in line:
            pos    = line.find(':')
            prefix = line[:pos]
            line   = line[pos+1:]
            exe.add_label(parse_label(prefix.strip()))

        line=line.strip()
        if line == "":
            continue
        
        # at this point our line is label-free and comments-free
        verb = line.split()[0]
        rest = line[len(verb):].strip()
        #############################
        #### Base Instructions
        if   verb in type1:
            exe.add( Instruction_Type1(line) )
        elif verb in type2:
            exe.add( Instruction_Type2(line) )
        elif verb in type3: # jumps
            exe.add( Instruction_Type3(line) )
        elif verb == "load": # type4 
            exe.add( Instruction_Load(line) )
        elif verb == "store":# type4 
            exe.add( Instruction_Store(line) )
        elif verb == "jal": # type5
            exe.add( Instruction_Jal(line))
        #############################
        #### Pseudo Instructions
        elif verb == "leti":
            process_leti(line)
        elif verb == "push":# pseudo type4
            exe.add( Instruction_Type2("subi sp, sp, 4") )
            exe.add( Instruction_Store("store [sp], "+rest), pseudo=True )
        elif verb == "pop":# pseudo type4
            exe.add( Instruction_Load("load "+rest+", [sp]"))
            exe.add( Instruction_Type2("addi sp, sp, 4") , pseudo=True)
        elif verb == "inc":
            reg = parse_register(rest)
            exe.add( Instruction_Type2(f"addi r{reg}, r{reg}, 1"))
        elif verb == "dec":
            reg = parse_register(rest)
            exe.add( Instruction_Type2(f"subi r{reg}, r{reg}, 1"))
        elif verb == "mov":
            rd, rs = check_generic_args(line, 2)
            exe.add( Instruction_Type2(f"addi {rd}, {rs}, 0"))
        elif verb == "not":
            rd, rs = check_generic_args(line, 2)
            exe.add( Instruction_Type2(f"xori {rd}, {rs}, -1"))
        elif verb == "neg":
            rd, rs = check_generic_args(line, 2)
            exe.add( Instruction_Type1(f"sub {rd}, r0, {rs}"))
        elif verb == "seqz":
            rd, rs = check_generic_args(line, 2)
            exe.add( Instruction_Type2(f"sltiu {rd}, {rs}, 0"))
        elif verb == "snez":
            rd, rs = check_generic_args(line, 2)
            exe.add( Instruction_Type1(f"slt {rd}, zero, {rs}"))
        elif verb == "sltz":
            rd, rs = check_generic_args(line, 2)
            exe.add( Instruction_Type1(f"slt {rd}, {rs}, zero"))
        elif verb == "sgtz":
            rd, rs = check_generic_args(line, 2)
            exe.add( Instruction_Type1(f"slt {rd}, zero, {rs}"))
        elif verb == "nop":
            check_generic_args(line, 0)
            exe.add( Instruction_Type2(f"addi r0, r0, 0"))
        elif verb in pseudo_jumps: # some cond jumps (e.g. bgt) are pseudo-instructions
            process_pseudo_jump(line)
        elif verb == "jmp":
            destop = check_generic_args(line, 1)[0]
            exe.add( Instruction_Jal(f"jal zero, pc, {destop}"))
        elif verb == "call":
            destop = check_generic_args(line, 1)[0]
            exe.add( Instruction_Jal(f"jal lr, pc, {destop}"))
        elif verb == "ret":
            check_generic_args(line, 0)
            exe.add( Instruction_Jal("jal zero, lr, +0"))
        elif verb == ".word":
            numbers=rest.split(",")
            for n in numbers:
                n=n.strip()
                if len(n) == 0:
                    error("Missing literal value in .word directive")
                exe.add( MemoryWord( n ), pseudo=True)
        elif verb == ".space":
            size = parse_integer_literal(rest)
            if size <= 0:
                error(f"Incorrect size in .space directive: {size}")
            exe.cur_addr  += size
        elif verb == ".align":
            size = parse_integer_literal(rest)
            if size <= 0:
                error(f"Incorrect argument in .align directive: {size}")
            while exe.cur_addr % size != 0:
                exe.cur_addr  += 1
        else:
            error("unsupported syntax")

    f=open(exefile,'w')
    f.write(exe.encode()+'\n')

    f=open(lstfile,'w')
    listing=exe.objdump()
    f.write(listing+'\n')
    if not args.quiet:
        print(listing)
