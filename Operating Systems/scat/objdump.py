#!/usr/bin/env python3

import argparse
import os
import sys

import asm



def nibble(value, pos):
    assert pos%4 == 0
    return (value >> pos) & 0xF

argparser = argparse.ArgumentParser()
argparser.add_argument("exefile",metavar='EXEFILE',help="path to the executable file")
args=argparser.parse_args()
if not os.path.exists(args.exefile):
    print(argparser.prog+": cannot find file '"+args.exefile+"'")
    sys.exit(1)
if not args.exefile[-4:] == ".exe":
    print(argparser.prog+": incorrect filename '"+args.exefile+"'")
    sys.exit(1)

lines=open(args.exefile).read().splitlines()

if (    any([ ':' in line     for line in lines])
    and any([ ':' not in line for line in lines])):
    print(f"{args.exefile}: incorrect format.")
    print("Either all must have an address field, or none of them")
    sys.exit(1)

explicit_addresses = ':' in lines[0] # truth value

memory=dict()
addr=0
for line in lines:
    if explicit_addresses:
        addr,line= line.split(':')
        addr=int(addr, 16)
    if addr in memory:
        print(f'Error: duplicate address: {hex(addr)}')
        sys.exit(1)
    memory[addr]=int(line, 16)
    addr += 4

addrwidth= len("%x" % max(memory.keys()))
addrwidth = 2*(1+(addrwidth-1)//2)     # an even number of digits looks prettier



mnemonics = {
    1: asm.type1,
    2: asm.type2,
    3: asm.type3,
    4: asm.type4,
    5: asm.type5}

# magic number to recognize push/pop patterns
push_subi=0x21dd0004
pop_addi =0x20dd0004

def pprint(text):
    text = text.replace('r0','zero')
    text = text.replace('r15','pc')
    text = text.replace('r14','lr')
    text = text.replace('r13','sp')

    print(text)

# First pass: try and discover symbols
symbols=set()
for addr,word in memory.items():
    ty  = nibble(word,28)
    op  = nibble(word,24)
    try:
        verb=f'{mnemonics[ty][op]}' # just as a test
    except KeyError: 
        continue # not a valid instruction, nothing to do
    rd  = nibble(word,20)
    rs  = nibble(word,16)
    imm = word & 0xFFFF
    if imm >= 2**15: imm-=2**16
    if ty==2 and op==0 and rs==15 and rd==15: # branch always
        symbols.add(addr+imm)
    if ty==3:                      # cond. jump
        symbols.add(addr+imm)
    if ty==4 and op==0 and rs==15: # PC-relative load 
        symbols.add(addr+imm)
    if ty==4 and op==1 and rd==15: # PC-relative store
        symbols.add(addr+imm)
    if ty==5 and rs == 15:         # PC-relative jal (call, jmp)
        symbols.add(addr+imm)


labelwidth=0
if symbols:
    labelwidth=4

# Second pass: perform disassembly proper
for addr,word in memory.items():
    ty  = nibble(word,28)
    op  = nibble(word,24)
    rd  = nibble(word,20)
    rs  = nibble(word,16)
    imm = word & 0xFFFF
    if imm >= 2**15: imm-=2**16

    if addr in symbols:
        print(f'<{addr:04x}>')
    
    bi = f'{word:08x}'
    print(labelwidth*' '+f'{addr:0{addrwidth}x}: {bi[0:2]} {bi[2:4]} {bi[4:6]} {bi[6:8]}'+4*' ',end = '')

    try:
        verb=f'{mnemonics[ty][op]:5s}'
    except KeyError: # not a valid instruction, nothing to show
        comment=''
        if word > 2**31:
            comment = f' or {word-2**32}'
        print(f'; 0x{word:08x} = {word}'+comment)
        continue
    
    if ty == 1:
        # reg-reg ALU
        rs2=nibble(word,12)
        pprint(f'{verb} r{rd}, r{rs}, r{rs2}')
    elif ty==2:
        # reg-imm ALU
        if rd == 15 and rs == 15: # branch always
            pprint(f'bra {imm} ; <{addr+imm:0{labelwidth}x}>')
        else:
            pprint(f'{verb} r{rd}, r{rs}, {imm}')
    elif ty==3:
        # conditional jumps
        imm=f'{imm:+d} ; <{addr+imm:0{labelwidth}x}>'
        pprint(f'{verb} r{rd}, r{rs}, {imm}')
    elif ty==4:
        # memory
        comment=""
        if op == 0: # Load
            if rs==15: comment=f' ; <{addr+imm:0{labelwidth}x}>'
            if rs==13 and imm==0 and memory[addr+4]==pop_addi: comment=f' ; pop r{rd}'
            pprint(f'{verb} r{rd}, [r{rs}{imm:+d}]'+comment)
        else: # Store
            if rd==13 and imm==0 and addr>=4 and memory[addr-4]==push_subi: comment=f' ; push r{rs}'
            if rd==15: comment=f' ; <{addr+imm:0{labelwidth}x}>'
            pprint(f'{verb} [r{rd}{imm:+d}], r{rs}'+comment)
    elif ty==5:
        # Jump-And-Link
        if rd==0 and rs==14 and imm==0:
            print('ret')
        elif rd == 14 and rs == 15:
            print(f'call {imm:+d} ; <{addr+imm:0{labelwidth}x}>')
        elif rd == 0 and rs == 15:
            print(f'jmp {imm:+d} ; <{addr+imm:0{labelwidth}x}>')
        else:
            comment=""
            if rs == 15: comment=f' ; <{addr+imm:0{labelwidth}x}>'
            pprint(f'{verb} r{rd}, r{rs}, {imm:+d}'+comment)

