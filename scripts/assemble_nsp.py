#!/usr/bin/env python3
"""Join the repository's transport parts into one installable NSP."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = 'NetSurf-Switch-0.2.0-experimental.nsp'
EXPECTED = 'b16bbef34a80344a2880dfa70cd6569090a04ff7501f93c5a75a9d6907203a55'
out = ROOT / 'dist' / BASE
out.parent.mkdir(exist_ok=True)
parts = [ROOT / 'packages' / (BASE + f'.part{i:02d}') for i in range(1, 4)]
blob = b''.join(p.read_bytes() for p in parts)
if hashlib.sha256(blob).hexdigest() != EXPECTED:
    raise SystemExit('Package hash mismatch; assembly stopped')
if blob[:4] != b'PFS0':
    raise SystemExit('Invalid NSP container')
out.write_bytes(blob)
print(out)
