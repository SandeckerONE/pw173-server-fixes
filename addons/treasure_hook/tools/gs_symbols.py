#!/usr/bin/env python3
"""gs_symbols.py - READ-ONLY look inside the gs program file (changes nothing).

Works on 32- and 64-bit ELF files and needs only python3 (c++filt is used for
readable names when it is installed).

  python3 -I gs_symbols.py info    /opt/gamed/gs
  python3 -I gs_symbols.py find    /opt/gamed/gs 'Lottery|send_lot' [max]
  python3 -I gs_symbols.py callers /opt/gamed/gs 'Lottery_Notice1'
  python3 -I gs_symbols.py range   /opt/gamed/gs '<exact mangled name>'
  python3 -I gs_symbols.py names   /opt/gamed/gs '<regex on mangled names>'

find    : symbols whose mangled or readable name matches the regex
callers : every direct call/jump (E8/E9) to the matching function(s), with the
          function it sits in, and every pointer to it in data (vtable slots)
range   : start and end address of one symbol (for objdump --start/--stop)
names   : just the mangled names of matching functions, one per line
"""
import bisect
import re
import shutil
import struct
import subprocess
import sys

SHT_SYMTAB, SHT_DYNSYM, SHT_DYNAMIC = 2, 11, 6
SHF_ALLOC, SHF_EXECINSTR = 0x2, 0x4
STT_OBJECT, STT_FUNC = 1, 2


class Elf:
    def __init__(self, path):
        self.f = open(path, "rb")
        ident = self.f.read(16)
        if ident[:4] != b"\x7fELF":
            sys.exit(f"{path}: not an ELF file")
        self.is64 = ident[4] == 2
        self.e = "<"
        if self.is64:
            hdr = struct.unpack("<HHIQQQIHHHHHH", self.f.read(48))
        else:
            hdr = struct.unpack("<HHIIIIIHHHHHH", self.f.read(36))
        (self.type, self.machine, _, self.entry, self.phoff, self.shoff, _, _,
         self.phentsize, self.phnum, self.shentsize, self.shnum, self.shstrndx) = hdr
        self.sections = []
        for i in range(self.shnum):
            self.f.seek(self.shoff + i * self.shentsize)
            raw = self.f.read(self.shentsize)
            if self.is64:
                s = struct.unpack("<IIQQQQIIQQ", raw[:64])
            else:
                s = struct.unpack("<IIIIIIIIII", raw[:40])
            self.sections.append(dict(name_off=s[0], type=s[1], flags=s[2], addr=s[3],
                                      offset=s[4], size=s[5], link=s[6], entsize=s[9]))
        if self.shstrndx < len(self.sections):
            shs = self.read_sec(self.sections[self.shstrndx])
            for s in self.sections:
                end = shs.find(b"\0", s["name_off"])
                s["name"] = shs[s["name_off"]:end].decode("latin-1")
        self._syms = None

    def read_sec(self, s):
        self.f.seek(s["offset"])
        return self.f.read(s["size"])

    def read_at(self, addr, size):
        for s in self.sections:
            if s["flags"] & SHF_ALLOC and s["type"] != 8 and s["addr"] <= addr < s["addr"] + s["size"]:
                self.f.seek(s["offset"] + addr - s["addr"])
                return self.f.read(size)
        return b""

    def symbols(self):
        """list of (addr, size, type, name) for defined FUNC/OBJECT symbols in loaded sections"""
        if self._syms is not None:
            return self._syms
        tab = [s for s in self.sections if s["type"] == SHT_SYMTAB] or \
              [s for s in self.sections if s["type"] == SHT_DYNSYM]
        out = []
        if tab:
            st = tab[0]
            strtab = self.read_sec(self.sections[st["link"]])
            data = self.read_sec(st)
            fmt, size = ("<IBBHQQ", 24) if self.is64 else ("<IIIBBH", 16)
            for i in range(len(data) // size):
                rec = struct.unpack_from(fmt, data, i * size)
                if self.is64:
                    name, info, _, shndx, value, ssize = rec
                else:
                    name, value, ssize, info, _, shndx = rec
                typ = info & 0xF
                if typ not in (STT_FUNC, STT_OBJECT) or not value or shndx == 0 or shndx >= 0xFF00:
                    continue
                if shndx >= len(self.sections) or not self.sections[shndx]["flags"] & SHF_ALLOC:
                    continue
                end = strtab.find(b"\0", name)
                out.append((value, ssize, typ, strtab[name:end].decode("latin-1")))
        out.sort()
        self._syms = out
        return out


def demangle(names):
    if not names or not shutil.which("c++filt"):
        return list(names)
    r = subprocess.run(["c++filt"], input="\n".join(names), capture_output=True, text=True)
    lines = r.stdout.splitlines()
    return lines if len(lines) == len(names) else list(names)


def cmd_info(elf, path):
    kinds = {2: "EXEC (fixed address, not PIE)", 3: "DYN (PIE or shared library)"}
    print(f"file: {path}")
    print(f"class: {'64' if elf.is64 else '32'}-bit, type: {kinds.get(elf.type, elf.type)}, machine: {elf.machine}")
    names = {s.get('name', '?') for s in elf.sections}
    print(f"sections: {elf.shnum}; symtab: {'yes' if '.symtab' in names else 'NO'}; "
          f"debug_info: {'yes' if '.debug_info' in names else 'NO'}")
    dyn = [s for s in elf.sections if s["type"] == SHT_DYNAMIC]
    if not dyn:
        print("dynamic: NO (statically linked: LD_PRELOAD would NOT work)")
        return
    data = elf.read_sec(dyn[0])
    dynstr = elf.read_sec(elf.sections[dyn[0]["link"]])
    fmt, size = ("<qQ", 16) if elf.is64 else ("<iI", 8)
    needed = []
    for i in range(len(data) // size):
        tag, val = struct.unpack_from(fmt, data, i * size)
        if tag == 0:
            break
        if tag == 1:
            needed.append(dynstr[val:dynstr.find(b"\0", val)].decode())
    print("dynamic: yes (LD_PRELOAD can work); needs: " + ", ".join(needed))
    print(f"symbols (FUNC/OBJECT): {len(elf.symbols())}")


def cmd_find(elf, pattern, maxn=80):
    rx = re.compile(pattern)
    syms = elf.symbols()
    names = [s[3] for s in syms]
    dem = demangle(names)
    hits = [(s, d) for s, d in zip(syms, dem) if rx.search(s[3]) or rx.search(d)]
    print(f"# {len(hits)} match(es) for /{pattern}/" + (f", first {maxn} shown" if len(hits) > maxn else ""))
    for (addr, size, typ, name), d in hits[:maxn]:
        print(f"{addr:#010x} {size:7d} {'FUNC' if typ == STT_FUNC else 'OBJ '} {name}\n{'':26}{d}")


def pick_target(elf, pattern):
    funcs = [s for s in elf.symbols() if s[2] == STT_FUNC and re.search(pattern, s[3])]
    if not funcs:
        sys.exit(f"no function matches /{pattern}/")
    return funcs


def cmd_callers(elf, pattern):
    syms = elf.symbols()
    funcs = [s for s in syms if s[2] == STT_FUNC]
    starts = [s[0] for s in funcs]
    objs = [s for s in syms if s[2] == STT_OBJECT]
    ostarts = [s[0] for s in objs]
    ptr = 8 if elf.is64 else 4
    mask = 2 ** (8 * ptr) - 1
    targets = pick_target(elf, pattern)
    found = {t[0]: [] for t in targets}

    def where(table, tstarts, a):
        k = bisect.bisect_right(tstarts, a) - 1
        return table[k][3] if k >= 0 and a < table[k][0] + max(table[k][1], 1) else "?"

    for s in elf.sections:  # direct calls / tail jumps in code, one pass for all targets
        if not (s["flags"] & SHF_EXECINSTR) or s["type"] == 8:
            continue
        code = elf.read_sec(s)
        base = s["addr"]
        for m in re.finditer(b"[\xe8\xe9]", code, re.S):
            o = m.start()
            if o + 5 > len(code):
                break
            dest = (base + o + 5 + struct.unpack_from("<i", code, o + 1)[0]) & mask
            if dest in found:
                site = base + o
                inside = where(funcs, starts, site)
                kind = "call" if code[o] == 0xE8 else "jump"
                found[dest].append(f"  direct {kind} at {site:#x} in {inside}")
    for s in elf.sections:  # pointers in data (vtable slots, function tables)
        if not (s["flags"] & SHF_ALLOC) or s["flags"] & SHF_EXECINSTR or s["type"] in (4, 8, 9):
            continue  # skip relocation tables (4, 9) and .bss (8)
        data = elf.read_sec(s)
        for tgt in found:
            needle = struct.pack("<Q" if elf.is64 else "<I", tgt)
            o = data.find(needle)
            while o >= 0:
                addr = s["addr"] + o
                if addr % ptr == 0:
                    found[tgt].append(f"  pointer at {addr:#x} in {s.get('name', '?')} "
                                      f"{where(objs, ostarts, addr)}")
                o = data.find(needle, o + 1)
    for tgt, tsize, _, tname in targets:
        print(f"# target {tname} at {tgt:#x} (size {tsize})  [{demangle([tname])[0]}]")
        lines = found[tgt]
        names = [l.rsplit(" ", 1)[-1] for l in lines]
        for l, d in zip(lines, demangle(names)):
            print(f"{l}  [{d}]")
        if not lines:
            print("  (no direct calls or pointers found)")


def cmd_names(elf, pattern):
    for addr, size, typ, name in elf.symbols():
        if typ == STT_FUNC and re.search(pattern, name):
            print(name)


def cmd_range(elf, name):
    for addr, size, typ, nm in elf.symbols():
        if nm == name:
            print(f"{addr:#x} {addr + max(size, 1):#x}")
            return
    sys.exit(f"not found: {name}")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    elf = Elf(path)
    if cmd == "info":
        cmd_info(elf, path)
    elif cmd == "find":
        cmd_find(elf, sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 80)
    elif cmd == "callers":
        cmd_callers(elf, sys.argv[3])
    elif cmd == "range":
        cmd_range(elf, sys.argv[3])
    elif cmd == "names":
        cmd_names(elf, sys.argv[3])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
