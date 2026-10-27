"""Reads the layout table files (layouts/*.json) and gets/sets fields in a record.

A layout field is {"name", "offset", "type", optional "length"}.
Types: i32, u32, f32, utf16 (fixed-size UTF-16LE text), gbk (fixed-size GBK text), bytes.
Nothing here knows about a particular file: the offsets live in the JSON tables.
"""
import json
import os
import struct
import sys


def base_dir():
    # works both as a script and inside a packaged .exe (PyInstaller unpacks data next to sys._MEIPASS)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_layout(name):
    with open(os.path.join(base_dir(), 'layouts', name), 'r', encoding='utf-8') as f:
        return Layout(json.load(f))


class Layout:
    def __init__(self, spec):
        self.spec = spec
        self.record_size = spec.get('record_size')
        self.fields = {f['name']: f for f in spec.get('fields', [])}

    def has(self, name):
        return name in self.fields

    def get(self, rec, name):
        f = self.fields[name]
        o, t = f['offset'], f['type']
        if t == 'i32':
            return struct.unpack_from('<i', rec, o)[0]
        if t == 'u32':
            return struct.unpack_from('<I', rec, o)[0]
        if t == 'f32':
            return struct.unpack_from('<f', rec, o)[0]
        if t == 'utf16':
            return bytes(rec[o:o + f['length']]).decode('utf-16le', 'replace').split('\x00')[0]
        if t == 'gbk':
            return bytes(rec[o:o + f['length']]).split(b'\x00')[0].decode('gbk', 'replace')
        if t == 'bytes':
            return bytes(rec[o:o + f['length']])
        raise ValueError('unknown field type ' + t)

    def set(self, rec, name, value):
        f = self.fields[name]
        o, t = f['offset'], f['type']
        if t == 'i32':
            struct.pack_into('<i', rec, o, int(value))
        elif t == 'u32':
            struct.pack_into('<I', rec, o, int(value))
        elif t == 'f32':
            struct.pack_into('<f', rec, o, float(value))
        elif t in ('utf16', 'gbk'):
            L = f['length']
            raw = value.encode('utf-16le' if t == 'utf16' else 'gbk')
            if len(raw) > L - (2 if t == 'utf16' else 1):
                raise ValueError('%s is too long (max %d characters)' % (name, (L // 2 - 1) if t == 'utf16' else L - 1))
            rec[o:o + L] = raw + b'\x00' * (L - len(raw))
        elif t == 'bytes':
            L = f['length']
            if len(value) != L:
                raise ValueError('%s must be exactly %d bytes' % (name, L))
            rec[o:o + L] = value
        else:
            raise ValueError('unknown field type ' + t)

    def slice(self, rec, name):
        f = self.fields[name]
        return bytes(rec[f['offset']:f['offset'] + f['length']])
