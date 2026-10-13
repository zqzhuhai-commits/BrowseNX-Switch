#!/usr/bin/env python3
"""Select only the two packaging keys; never print their values."""
import re
import sys
from pathlib import Path

required = {'header_key': 64, 'key_area_key_application_00': 32}
keys = {}
for line in Path(sys.argv[1]).read_text(encoding='utf-8-sig').splitlines():
    if '=' not in line:
        continue
    k, v = (s.strip() for s in line.split('=', 1))
    if k in required:
        if not re.fullmatch('[0-9a-fA-F]{' + str(required[k]) + '}', v):
            raise SystemExit('Invalid required key: ' + k)
        keys[k] = v
if keys.keys() != required.keys():
    raise SystemExit('Missing packaging keys')
p = Path(sys.argv[2])
p.touch(mode=0o600)
p.chmod(0o600)
p.write_text(''.join(k + ' = ' + v + '\n' for k, v in keys.items()))
