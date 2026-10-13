#!/usr/bin/env python3
"""Stage the pinned NetSurf libnx release for a standalone NSP.

Keep all virtual addresses, relocation tables and MOD0 data unchanged.  A
synthetic ELF supplies the original NRO's three memory segments to the official
switch-tools elf2nso converter.  This applies to this libnx release, not to
arbitrary NROs that require a homebrew loader context.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

PINNED_SHA256 = 'adc407ceab4e17347230f71d13c87969767e65015fd163021d548ce9f35456a9'
TITLE_ID = '01f0b05e20261000'


def bounded(data, offset, size):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError('Section lies outside input')
    return data[offset:offset + size]


def unpack_romfs(blob, out):
    h = struct.unpack_from('<10Q', bounded(blob, 0, 80))
    if h[0] != 80:
        raise ValueError('Invalid RomFS header')
    dirs = bounded(blob, h[3], h[4])
    files = bounded(blob, h[7], h[8])
    visited_dirs, visited_files = set(), set()
    manifest = {}

    def name(raw):
        s = raw.decode('utf-8')
        if s in ('.', '..') or '/' in s or '\\' in s or '\0' in s:
            raise ValueError('Unsafe RomFS filename')
        return s

    def directory(offset, parent):
        if offset in visited_dirs:
            raise ValueError('Cyclic RomFS directory table')
        visited_dirs.add(offset)
        _, sibling, childdir, childfile, _, n = struct.unpack('<6I', bounded(dirs, offset, 24))
        dirname = name(bounded(dirs, offset + 24, n))
        path = parent / dirname if dirname else parent
        path.mkdir(parents=True, exist_ok=True)
        f = childfile
        while f != 0xffffffff:
            if f in visited_files:
                raise ValueError('Cyclic RomFS file table')
            visited_files.add(f)
            _, nxt, dataoff, size, _, n = struct.unpack('<IIQQII', bounded(files, f, 32))
            filename = name(bounded(files, f + 32, n))
            if not filename:
                raise ValueError('Empty RomFS filename')
            payload = bounded(blob, h[9] + dataoff, size)
            dst = path / filename
            dst.write_bytes(payload)
            manifest[dst.relative_to(out).as_posix()] = hashlib.sha256(payload).hexdigest()
            f = nxt
        d = childdir
        while d != 0xffffffff:
            d = directory(d, path)
        return sibling

    directory(0, out)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nro', type=Path)
    ap.add_argument('stage', type=Path)
    ap.add_argument('--elf2nso', type=Path, required=True)
    ap.add_argument('--npdmtool', type=Path, required=True)
    ap.add_argument('--npdm-template', type=Path, required=True)
    args = ap.parse_args()
    b = args.nro.read_bytes()
    digest = hashlib.sha256(b).hexdigest()
    if digest != PINNED_SHA256:
        raise ValueError('Expected the pinned NetSurf Switch v0.2.0 binary')
    if b[16:20] != b'NRO0':
        raise ValueError('Invalid NRO')
    nro_size = struct.unpack_from('<I', b, 24)[0]
    segments = [struct.unpack_from('<II', b, 32 + 8 * i) for i in range(3)]
    bss = struct.unpack_from('<I', b, 56)[0]
    mod0 = struct.unpack_from('<I', b, 4)[0]
    if bounded(b, mod0, 4) != b'MOD0' or segments[0][0] != 0:
        raise ValueError('Unsupported startup layout')
    if struct.unpack_from('<I', b, 0)[0] != 0x14000020:
        raise ValueError('Expected libnx startup branch to offset 0x80')
    previous_end = 0
    for off, size in segments:
        if off != previous_end or off % 4096 or size % 4096:
            raise ValueError('Expected contiguous page-aligned NRO segments')
        bounded(b, off, size)
        previous_end = off + size
    if previous_end != nro_size:
        raise ValueError('Unexpected NRO segment size')

    stage = args.stage.resolve()
    for dirname in ('exefs', 'control', 'romfs'):
        (stage / dirname).mkdir(parents=True, exist_ok=True)
    # ELF64/AArch64, ET_DYN, three PT_LOAD entries, one GNU build-id note.
    note = struct.pack('<III', 4, 32, 3) + b'GNU\0' + b[64:96]
    note_off = 64 + 3 * 56
    shoff = (note_off + len(note) + 7) & ~7
    payload_off = (shoff + 2 * 64 + 4095) & ~4095
    ident = b'\x7fELF' + bytes([2, 1, 1, 0]) + bytes(8)
    elf = bytearray(payload_off)
    elf[:64] = struct.pack('<16sHHIQQQIHHHHHH', ident, 3, 183, 1, 0, 64, shoff, 0,
                           64, 56, 3, 64, 2, 0)
    for i, (off, size) in enumerate(segments):
        struct.pack_into('<IIQQQQQQ', elf, 64 + i * 56,
                         1, (5, 4, 6)[i], payload_off + off, off, off,
                         size, size + (bss if i == 2 else 0), 4096)
    elf[note_off:note_off + len(note)] = note
    struct.pack_into('<IIQQQQIIQQ', elf, shoff + 64,
                     0, 7, 0, 0, note_off, len(note), 0, 0, 4, 0)
    elf += bounded(b, 0, nro_size)
    elf_path = stage / 'netsurf-segments.elf'
    elf_path.write_bytes(elf)
    subprocess.run([str(args.elf2nso.resolve()), str(elf_path), str(stage / 'exefs/main')], check=True)

    a = bounded(b, nro_size, 56)
    if a[:4] != b'ASET':
        raise ValueError('Missing NRO resources')
    assets = [struct.unpack_from('<QQ', a, 8 + i * 16) for i in range(3)]
    icon, nacp, romfs = [bounded(b, nro_size + off, size) for off, size in assets]
    if len(nacp) != 0x4000:
        raise ValueError('Invalid NACP size')
    n = bytearray(nacp)
    # No mandatory user selection, and no automatic gameplay recording.
    n[0x3025] = 0
    n[0x3026] = 0
    n[0x3035] = 0
    n[0x3060:0x3070] = b'0.2.0-nsp1\0'.ljust(16, b'\0')
    (stage / 'control/control.nacp').write_bytes(n)
    # All language slots use the same bundled upstream icon.
    languages = ('AmericanEnglish', 'BritishEnglish', 'Japanese', 'French', 'German',
                 'LatinAmericanSpanish', 'Spanish', 'Italian', 'Dutch', 'CanadianFrench',
                 'Portuguese', 'Russian', 'Korean', 'TraditionalChinese', 'SimplifiedChinese',
                 'BrazilianPortuguese')
    for lang in languages:
        (stage / 'control' / ('icon_' + lang + '.dat')).write_bytes(icon)
    manifest = unpack_romfs(romfs, stage / 'romfs')
    if 'res/ca-bundle.pem' not in manifest or not any('font' in p.lower() or p.endswith('.ttf') for p in manifest):
        raise ValueError('Missing TLS or font assets')

    npdm = json.loads(args.npdm_template.read_text())
    npdm.update(name='NetSurfBrowser', program_id='0x' + TITLE_ID,
                program_id_range_min='0x0100000000000000',
                program_id_range_max='0x01ffffffffffffff',
                main_thread_stack_size='0x400000', address_space_type=3,
                system_resource_size='0x0', version='0x0', signature_key_generation=0,
                optimize_memory_allocation=False, disable_device_address_space_merge=False,
                enable_alias_region_extra_size=False, prevent_code_reads=False)
    for old_name in ('title_id', 'title_id_range_min', 'title_id_range_max', 'process_category'):
        npdm.pop(old_name, None)
    for capability in npdm['kernel_capabilities']:
        if capability['type'] == 'debug_flags':
            capability['value'] = {'allow_debug': True, 'force_debug': False, 'force_debug_prod': False}
    npdm_path = stage / 'npdm.json'
    npdm_path.write_text(json.dumps(npdm, indent=2))
    subprocess.run([str(args.npdmtool.resolve()), str(npdm_path), str(stage / 'exefs/main.npdm')], check=True)
    result = dict(upstream='https://github.com/etonedemid/netsurf-switch',
                  tag='v0.2.0', commit='29d910fc28e6e0c816eea4a86bae4e40f2ac699d',
                  input_sha256=digest, title_id=TITLE_ID,
                  hardware_tested=False, standalone=True,
                  segments=[dict(address=off, size=size) for off, size in segments],
                  bss_size=bss, romfs_files=manifest)
    (stage / 'manifest.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'staged': True, 'romfs_files': len(manifest), 'title_id': TITLE_ID}))


if __name__ == '__main__':
    main()
