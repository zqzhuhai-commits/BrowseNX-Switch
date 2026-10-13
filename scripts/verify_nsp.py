#!/usr/bin/env python3
"""Offline content/format checks only; not a Switch runtime test."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(tool, *args):
    r = subprocess.run([str(tool), '--disablekeywarns', '--suppresskeys', *map(str, args)],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError('hactool command failed (raw diagnostics intentionally suppressed)')
    # Unsigned homebrew has no Nintendo fixed-key or ACID signature.
    # Reject every other failed hash/signature verification.
    for line in (r.stdout + r.stderr).splitlines():
        if '(FAIL)' in line or '(INVALID)' in line:
            if not (line.strip().startswith('Fixed-Key Signature (FAIL):') or
                    re.match(r'^Signature \(FAIL\):\s+0+$', line.strip())):
                raise RuntimeError('Content integrity verification failed')
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nsp', type=Path)
    ap.add_argument('--nro', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--keys', type=Path, required=True)
    ap.add_argument('--hactool', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    a = ap.parse_args()
    m = json.loads(a.manifest.read_text())
    nro = a.nro.read_bytes()
    assert sha(nro) == m['input_sha256']
    b = a.nsp.read_bytes()
    assert b[:4] == b'PFS0'
    count, strsize = struct.unpack_from('<II', b, 4)
    assert count == 3
    strings = b[16 + 24 * count:16 + 24 * count + strsize]
    base = 16 + count * 24 + strsize
    payloads = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for i in range(count):
            off, size, nameoff, _ = struct.unpack_from('<QQII', b, 16 + i * 24)
            name = strings[nameoff:].split(b'\0', 1)[0].decode()
            assert re.fullmatch(r'[0-9a-f]{32}(?:\.cnmt)?\.nca', name)
            payload = b[base + off:base + off + size]
            assert len(payload) == size and sha(payload)[:32] == name[:32]
            payloads[name] = payload
            (root / name).write_bytes(payload)
        kinds = {}
        for name in payloads:
            d = root / name[:32]
            d.mkdir()
            log = run(a.hactool, '-k', a.keys, '-y', '--exefsdir', d / 'exefs',
                      '--romfsdir', d / 'romfs', '--section0dir', d / 'section0', root / name)
            kind = re.search(r'Content Type:\s+(\w+)', log).group(1)
            assert kind not in kinds
            kinds[kind] = d
        assert set(kinds) == {'Program', 'Control', 'Meta'}
        prog = kinds['Program']
        files = {p.relative_to(prog / 'romfs').as_posix(): sha(p.read_bytes())
                 for p in (prog / 'romfs').rglob('*') if p.is_file()}
        assert files == m['romfs_files']

        unc = root / 'uncompressed.nso'
        log = run(a.hactool, '-t', 'nso0', '-y', '--uncompressed', unc, prog / 'exefs/main')
        assert all(re.search(re.escape(label) + r'\s+\(GOOD\)', log)
                   for label in ('.text', '.rodata', '.rwdata'))
        u = unc.read_bytes()
        for i, seg in enumerate(m['segments']):
            fileoff, address, size, extra = struct.unpack_from('<4I', u, 16 + 16 * i)
            assert address == seg['address'] and size == seg['size']
            assert u[fileoff:fileoff + size] == nro[address:address + size]
            if i == 2:
                assert extra == m['bss_size']
        npdm = (prog / 'exefs/main.npdm').read_bytes()
        assert npdm[:4] == b'META'
        assert (npdm[12] & 7) == 7  # 64-bit, address space type 3
        assert struct.unpack_from('<I', npdm, 28)[0] == 0x400000
        aci0 = struct.unpack_from('<I', npdm, 0x70)[0]
        assert npdm[aci0:aci0 + 4] == b'ACI0'
        assert struct.unpack_from('<Q', npdm, aci0 + 16)[0] == int(m['title_id'], 16)
        control = (kinds['Control'] / 'romfs/control.nacp').read_bytes()
        assert len(control) == 0x4000
        assert control[:512].split(b'\0', 1)[0].decode() == 'NetSurf 浏览器'
        assert control[0x3060:0x3070].split(b'\0', 1)[0] == b'0.2.0-nsp1'
        assert control[0x3025] == 0
        cnmts = list((kinds['Meta'] / 'section0').glob('*.cnmt'))
        assert len(cnmts) == 1
        c = cnmts[0].read_bytes()
        assert struct.unpack_from('<Q', c)[0] == int(m['title_id'], 16) and c[12] == 0x80
        ext, records = struct.unpack_from('<HH', c, 14)
        assert records == 2
        for i in range(records):
            r = c[32 + ext + 56 * i:32 + ext + 56 * (i + 1)]
            name = r[32:48].hex() + '.nca'
            assert name in payloads and sha(payloads[name]) == r[:32].hex()
            assert int.from_bytes(r[48:54], 'little') == len(payloads[name])
        assert c[-32:] == hashlib.sha256(c[:-32]).digest()
    report = dict(nsp_sha256=sha(b), nsp_size_bytes=len(b), title_id=m['title_id'],
                  nca_count=count, romfs_files_verified=len(m['romfs_files']),
                  checks=dict(nca_content_hashes='passed', nca_filename_hashes='passed',
                              nso_segment_hashes='passed', nro_to_nso_byte_comparison='passed',
                              romfs_exact_comparison='passed', npdm='passed',
                              control_metadata='passed', cnmt_content_links='passed'),
                  nintendo_signatures='unsigned homebrew; requires compatible CFW environment',
                  hardware_tested=False, firmware_22_5_0_tested=False)
    a.report.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
