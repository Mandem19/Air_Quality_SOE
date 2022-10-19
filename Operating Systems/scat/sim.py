#!/usr/bin/env python3

# python std lib
import argparse
import collections
import os, re, sys
import time
import random
try:
    import readline
except ImportError:
    print("warning: readline module is not installed")
    print("try this command:  python3 -m pip install pyreadline3")

# scat modules
import screen
import cpu
import utils

class Machine():
    def __init__(self):
        # GS-2017-12-07-13:55 all  of these  must be  instantiated and
        # plugged in here for the machine to be usable...
        self.screen=None
        self.mem=None
        self.cpu=None

        self.screen_was_ever_shown=False

    def step(self):
        res=self.cpu.step()
        if res:
            print(res)
        return res

    def write(self,addr,data):
        assert type(data) == int
        assert 0 <= data < 2**32
        assert addr >= 0
        if 0 <= addr < 0x10000000: # RAM
            self.mem.write(addr,data)
        elif 0xB0000000 <= addr < 0xB0004B00: # Video memory
            if not self.screen_was_ever_shown:
                self.screen.show()
                self.screen_was_ever_shown=True
            self.screen.write(addr-0xB0000000,data)
        else:
            raise cpu.SimulatedError(f"Memory error: write to invalid address 0x{self.mem.aas(addr)}")

    def read(self,addr,size):
        assert addr >= 0
        if 0 <= addr < 0x10000000: # RAM
             return self.mem.read(addr,size)
        elif 0xA0000000 <= addr < 0xA0000100: # RTC
            return self.rtc.read(addr-0xA0000000)
        elif 0xB0000000 <= addr < 0xB0004B00: # Video memory
            return self.screen.read(addr-0xB0000000,size)
        else:
            raise cpu.SimulatedError(f"Memory error: read from invalid address 0x{self.mem.aas(addr)}")

class RTC():
    def __init__(self):
        pass

    def step(self):
        pass

    def write(self,offset,data):
        pass

    def read(self,offset):
        tm = time.localtime()
        if offset == 0:
            return tm.tm_sec
        elif offset == 4:
            return tm.tm_min
        elif offset == 8:
            return tm.tm_hour
        else:
            return 0
                
class Listing():
    def __init__(self,lstfile):

        self.symbols = dict() # maps names to addresses
        self.disass = dict()  # maps addresses to line numbers

        if not os.path.exists(lstfile):
            print("warning: cound not load symbols (no .lst listing)")
            self.lines=[] # empty list here means "there is no listing"
            return

        f=open(lstfile)
        self.lines = [""] + f.read().splitlines() # add an extra empty line because line numbers count from one

        names=[] # accumulator for our under-construction names
        address=0

        for linenum,line in enumerate(self.lines):
            # label names come before their actual address so we have to
            # accumulate all names we encounter until we know where they are
            m=re.match(" *<([a-zA-Z_][a-zA-Z0-9_]*)>:$",line)
            if m:
                names.append( m.group(1) )
            m=re.match(" *([0-9a-fA-F]+)?:.*",line)
            if m:
                address = int(m.group(1), 16)
                for name in names:
                    assert name not in self.symbols
                    self.symbols[name] = address
                names=[] # flush our list

                # note that if several labels are colocated, then "disass"
                # will only know about one of them (the last one, because
                # we overwrite successive values)
                self.disass[address] = linenum

    def disassemblenear(self,addr):

        if addr not in self.disass:
            # nothing to show here
            return

        currentline = self.disass[addr]
        maxline = min(currentline +5, len(self.lines))

        closest_symbol_name = "0000" # dummy name in case there are no symbols at all
        closest_symbol_addr = 0
        for sym_name,sym_addr in self.symbols.items():
            if closest_symbol_addr <= sym_addr <= addr:
                closest_symbol_addr = sym_addr
                closest_symbol_name = sym_name

        print(f'<{closest_symbol_name}',end='')
        if closest_symbol_addr != addr:
            print(f'+{addr - closest_symbol_addr:d}',end='')
        print('>')

        for num in range(currentline,maxline):
            print("    " + self.lines[num])

    def update(self, addr, newvalue):
        if addr not in self.disass:
            return
        line_num     = self.disass[addr]
        split_column = self.lines[line_num].index(':')+2
        left         = self.lines[line_num][:split_column]
        s            = f'{newvalue:08x}'
        right        = s[0:2]+' '+s[2:4]+' '+s[4:6]+' '+s[6:8]

        self.lines[line_num] = left+right

class Memory():
    def __init__(self,exefile):
        self.mem=dict()
        f=open(exefile)
        linenum=0
        addr=0
        for line in f.readlines():
            line=line.strip()
            linenum+=1
            m=re.match("([0-9a-fA-F]+)?:? *([0-9a-fA-F]{8})$",line)
            if m is None:
                print("format error line",linenum)
                print(line)
                sys.exit(1)
            if m.groups()[0]:
                addr=int(m.groups()[0],16)
            for offset in [0,2,4,6]:
                val=m.groups()[1][offset:offset+2]
                if addr in self.mem:
                    print(f"collision error addr={addr} line {linenum}")
                    print(line)
                    sys.exit(1)
                self.mem[addr]=int(val,16)
                addr=addr+1
        # to get _deterministic_ random values in uninitialized reads
        # we seed the prng with the exe file name
        random.seed(exefile)

    def addrwidth(self):
        res = len("%x" % max(self.mem))
        res = 2*(1+(res-1)//2)     # an even number of digits looks prettier
        return res

    def aas(self,addr):
        """return a string representation of addr: hexadecimal digits, best-guessed length, right-justified"""
        return f"{addr:0{self.addrwidth()}x}"

    def read(self,addr,size):
        res=0
        while size>0:
            size -= 1
            if addr not in self.mem:
                # uninitialized memory reads as (reproducible) random values
                self.mem[addr] = random.randint(0,255)

            res += self.mem[addr] << (8*size)
            addr += 1
        return res

    def write(self, addr, data):
        assert type(data) == int
        assert 0 <= data < 2**32
        self.mem[addr] =   (data >> 24) & 0xFF
        self.mem[addr+1] = (data >> 16) & 0xFF
        self.mem[addr+2] = (data >>  8) & 0xFF
        self.mem[addr+3] = (data      ) & 0xFF
        
        # avoid showing outdated values in "info"
        lst.update(addr,data)


class UserError(Exception):
    pass

def parse_number(text):
    if re.match("0x[0-9a-fA-F]+",text): # maybe a hex address ?
        return int(text[2:], 16)
    if re.match("[1-9][0-9]*",text):    # maybe a decimal number ?
        return int(text, 10)
    if re.match("0[0-9]+",text):
        raise UserError("error: leading zeroes not allowed in decimal notation")
    if text == "0":
        return 0
    raise UserError(f"error: cannot understand number '{text}'")

def parse_location(text):
    if re.match("[a-zA-Z_][a-zA-Z0-9_]*",text): # maybe a label name ?
        if text not in lst.symbols:
            raise UserError(f"error: cannot find symbol '{text}'")
        return lst.symbols[text]

    return parse_number(text)

perf_profiler_ison = False
perf_time=0
perf_instr=0

verbose_mode_ison = True

def perf_start():
    global perf_time, perf_instr
    perf_time= time.time()
    perf_instr = 0

def perf_step():
    global perf_instr
    perf_instr += 1

def perf_stop():
    if perf_profiler_ison:
        exec_time= time.time() - perf_time
        print(f'executed {utils.eng(perf_instr)} instructions in '+utils.time2s(exec_time)
              +' i.e. '+utils.eng(perf_instr/exec_time)+' instructions per second')

# To help with formatting the help menu, we use an "ordered dict" so
# that we can maintain a distinction between a command's "real name"
# (by convention, first in the list) and and its "other names"
interactive_commands=collections.OrderedDict()

# A function decorator to help DRY when naming commands
def interactive(names):
    def decorate(cmd_func):
        assert(type(names) == list and len(names)>0)
        for name in names:
            assert name not in interactive_commands
            interactive_commands[name] = cmd_func
        return cmd_func
    return decorate

@interactive(["breakpoint","break","b"])
def cmd_breakpoint(words):
    """Pause execution at certain points in the program.

    Usage: 'breakpoint <labelname>' or 'breakpoint <0x1234>'
    Place a breakpoint at specified location (label name or numeric address)
    """
    if len(words) != 2:
        raise UserError("error: no target. usage: 'break labelname' or 'break 0x1234'")

    target = parse_location(words[1])

    if target %4 != 0:
        raise UserError(f"error: target address is not a multiple of 4: 0x{machine.mem.aas(target)}")

    if target in breakpoints:
        raise UserError(f"error: a breakpoint was already defined at address 0x{machine.mem.aas(target)}")

    else:
        breakpoints.append( target )
        print(f"new breakpoint placed at address 0x{machine.mem.aas(target)}")

@interactive(["continue","cont","run","c"])
def cmd_continue(word):
    """Resume execution.

    Execute the simulated program until either:
    - the PC register reaches a breakpoint
    - the cpu halts (defined as: loops on a single instruction)
    - the user presses Ctrl+C"""
    try:
        has_printed_control_c_message=False
        perf_start()
        while True:
            old_pc = machine.cpu.regs[15]
            res = machine.step()
            new_pc = machine.cpu.regs[15]
            perf_step()
            if new_pc in breakpoints:
                perf_stop()
                print(f"0x{machine.mem.aas(machine.cpu.regs[15])}: CPU reached a breakpoint")
                break
            if new_pc == old_pc:
                perf_stop()
                print(f"0x{machine.mem.aas(machine.cpu.regs[15])}: CPU halted")
                break
            if time.time()-perf_time > .5 and not has_printed_control_c_message:
                has_printed_control_c_message=True
                print("Running. Press Ctrl+C to interrupt...")
    except KeyboardInterrupt:
        print()
        perf_stop()
        if not verbose_mode_ison: # prevent info from being displayed twice
            cmd_info("")

@interactive(["help","h"])
def cmd_help(words):
    """Print help screen.

    Without arguments, print the list of available commands.
    With a command name, print help text about that command.
    """
    if len(words) == 1:
        print('Available commands:')
        cmd_funcs = set( interactive_commands.values() )
        realnames = set()
        for cmd_func in cmd_funcs:
            aliases  = [ name for name,_c in interactive_commands.items()
                         if  _c == cmd_func]
            realnames.add( aliases[0] )
        maxlength = max([len(name) for name in realnames])
        for name in sorted(realnames):
            doc=interactive_commands[name].__doc__
            if doc is None:
                doc=f"No help text for '{name}'"
            print("  "+name.ljust(maxlength)+": "+doc.splitlines()[0].strip())

        print("Type 'help <cmdname>' for more details about a command")
        return

    if words[1] not in interactive_commands:
        print(f"help: unknown command: '{words[1]}'.")
        print("Type 'help' with no arguments for the help menu")
        return

    cmd_func = interactive_commands[words[1]]
    aliases  = [ name for name,_c in interactive_commands.items()
                if  _c == cmd_func ]
    if len(aliases) == 1:
        print(f"Command: '{aliases[0]}'")
    else:
        print(f"Command: '{aliases[0]}' (other names: {', '.join(aliases[1:])})")
    if cmd_func.__doc__: # reas as 'None' if cmd_func has no docstring
        print(cmd_func.__doc__.strip())
    else:
        print('no help available')


@interactive(["info","i","where","w","list","l"])
def cmd_info(words):
    """Get info about program state.

    This command will print:
    - values in all CPU registers (as hexadecimal and decimal)
    - contents of memory around the address pointed to by PC
    - active breakpoints (if any)
    """
    machine.cpu.dumpregs()
    if lst.lines:
        lst.disassemblenear(machine.cpu.regs[15])
    else:
        print(f'memory view near PC:')
        cmd_memdump(['memdump',hex(machine.cpu.regs[15])])
        
    if len(breakpoints):
        if lst.lines:
            print("Active breakpoints:")
            for br in breakpoints:
                print(lst.lines[lst.disass[br]])
        else:
            print("Active breakpoints: "
                  +', '.join('0x'+machine.mem.aas(br) for br in breakpoints)
                  )

@interactive(["memdump","md","memory","mem"])
def cmd_memdump(words):
    """Show contents of memory.

    Usage: 'memdump <location>' or 'memdump <location> <length>'
    Read <length> bytes from memory starting at <location> (label name
    or numeric address) and display their values.
    """
    if len(words) == 1:
        raise UserError("error: no target address. usage: 'memdump labelname' or 'memdump 0x1234'")

    base_ad = parse_location(words[1])

    length=16
    if len(words)==3:
        length = parse_number(words[2])
        if length == 0:
            raise UserError("error: size too small")

    if len(words) > 3:
        raise UserError("error: too many arguments")

    aas=machine.mem.aas
    for line_ad in range(base_ad, base_ad+length, 4):
        print(f"{aas(line_ad)}: ",end='')
        for byte_ad in range(line_ad, min(line_ad+4,base_ad+length)):
            print(f"{machine.mem.read(byte_ad,1):02x} ",end='')
        print()

@interactive(["perf"])
def cmd_perf(words):
    """Show simulator performance.

    Usage: 'perf on' or 'perf off'
    When the profiler is enabled, the simulator measures and displays execution speed.
    """
    global perf_profiler_ison
    if len(words) == 1:
        words.append("off" if perf_profiler_ison else "on")
    if words[1] == "on":
        print("performance profiler: on")
        perf_profiler_ison = True
    elif words[1] == "off":
        print("performance profiler: off")
        perf_profiler_ison = False
    else:
        raise UserError("error: usage 'perf on' or 'perf off'")

@interactive(["quit"])
def cmd_quit(words):
    """Exit the simulator.

    Stop execution and return to the shell.
    You can also press Ctrl+D."""
    machine.screen.close()
    sys.exit(0)

@interactive(["registers","reg","regs"])
def cmd_regs(words):
    """Display contents of the CPU registers."""
    machine.cpu.dumpregs()

@interactive(["screen"])
def cmd_screen(words):
    """Display the simulated screen.

    Video memory is mapped from 0xB0000000 to 0xB0004AFF (19200 bytes).
    The screen size (in pixels) is 80 columns by 60 lines.
    Each pixel is accessible as a 32-bit word: RRGGBBxx (the last byte is ignored)
    """
    machine.screen.show()

@interactive(["step","s"])
def cmd_step(words):
    """Execute one program instruction.

    Usage: 'step' or 'step N'
    Execute just one, or N, instructions.

    Note: Press RETURN (on a blank line) after a 'step' to repeat the command.
    """
    # TODO: fix behaviour of "step N" w.r.t. breakpoints (gdb would stop, for instance)
    if len(words) == 1:
        machine.step()

    elif len(words) == 2:
        count = int(words[1])
        for i in range(count):
            machine.step()
            if machine.cpu.regs[15] in breakpoints:
                print(f"0x{machine.mem.aas(machine.cpu.regs[15])}: CPU reached a breakpoint")
                break

@interactive(["verbose","v"])
def cmd_verbose(words):
    """Always display program info.

    Usage: 'verbose on' or 'verbose off' or just 'verbose' to toggle.
    When in verbose mode, program state is displayed after each step/run.
    """
    global verbose_mode_ison
    if len(words) == 1:
        words.append("off" if verbose_mode_ison else "on")
    if words[1] == "on":
        print("verbose mode: on")
        verbose_mode_ison = True
    elif words[1] == "off":
        print("verbose mode: off")
        verbose_mode_ison = False
    else:
        raise UserError("error: usage 'verbose on' or 'verbose off'")

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument("exefile",metavar='EXEFILE',help="program to execute")
    argparser.add_argument("-q","--quiet", help="Don't start in verbose mode",action="store_true")
    args=argparser.parse_args()

    if not os.path.exists(args.exefile):
        print(f"{argparser.prog}: cannot find file '{args.exefile}'")
        sys.exit(1)

    if args.exefile[-4:] != ".exe":
        print(f"{argparser.prog}: incorrect filename suffix '{args.exefile}' (expected .exe)")
        sys.exit(1)

    # sanity check
    asmfile = args.exefile[:-4]+".s"
    if os.path.exists(asmfile) and os.path.getmtime(asmfile) > os.path.getmtime(args.exefile):
        print(f"{argparser.prog}: executable is out of date !")
        print(f"please rebuild it with the following command:")
        print(f"    python3 {sys.argv[0].replace('sim','asm')} {asmfile}")
        sys.exit(1)

    if args.quiet:
        verbose_mode_ison = False

    machine=Machine()

    machine.cpu=cpu.CPU(machine)
    machine.mem=Memory(args.exefile)
    machine.screen=screen.Screen(80,60)
    machine.rtc=RTC()

    lstfile = args.exefile.replace('.exe','.lst')
    lst     = Listing(lstfile)

    breakpoints=[]

    if verbose_mode_ison:
        cmd_info("")

    # always either: False, or a commandline to be repeated (string)
    previous_command_was_step = False
    previous_command_was_continue = False

    th = None
    cline = None
    # main debugger loop
    while True:
        try:
            cline=input('(sim) ').strip().lower()
        except EOFError: # Ctrl+D
            print()
            cline="quit"
        except KeyboardInterrupt: # Ctrl+C
            print()
            continue
        if cline=="":
            if previous_command_was_step:
                cline= previous_command_was_step
            elif previous_command_was_continue:
                cline= previous_command_was_continue
            else:
                continue

        words = cline.split()
        if words[0] not in interactive_commands:
            print("Unknown command:",words[0])
            print("Type 'help' to know about available commands")
            continue

        cmd_func = interactive_commands[words[0]]

        try:
            cmd_func(words)
        except cpu.SimulatedError as e:
            print(f"0x{machine.mem.aas(machine.cpu.regs[15])}: "+str(e))
            cmd_func = None # avoid "info" screen and command auto-repetition
        except UserError as e:
            print(e)
            cmd_func = None # avoid "info" screen and command auto-repetition
            
        previous_command_was_step     = cline if (cmd_func is cmd_step)     else False
        previous_command_was_continue = cline if (cmd_func is cmd_continue) else False
        if verbose_mode_ison and cmd_func in [ cmd_step, cmd_continue ]:
            cmd_info("")
