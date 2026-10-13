#!/usr/bin/env bash
# Linux host-only repack of the pinned upstream libnx browser.
set -euo pipefail
cd "$(dirname "$0")"
KEYSET="${1:?Usage: ./build.sh /absolute/path/to/prod.keys}"
KEYSET="$(realpath "$KEYSET")"
mkdir -p work/tools dist
fetch_repo() {
    local url="$1" dest="$2" commit="$3"
    if [ ! -d "$dest/.git" ]; then git clone "$url" "$dest"; fi
    git -C "$dest" checkout --detach "$commit"
}
fetch_repo https://github.com/rlaphoenix/hacBrewPack.git work/hacBrewPack 745b16ecfc9ce055743067d200572204cb2aac6c
fetch_repo https://github.com/switchbrew/switch-tools.git work/switch-tools 22756068dd0ed6ff9734c59cb4f99ebd3f62555b
fetch_repo https://github.com/lz4/lz4.git work/lz4 664c914a1215f98fc8fec2a9fe8f8bc8695b9bab
git -C work/hacBrewPack apply --reverse --check ../../patches/hacbrewpack-cnmt-digest.patch 2>/dev/null || git -C work/hacBrewPack apply ../../patches/hacbrewpack-cnmt-digest.patch
cp work/hacBrewPack/config.mk.template work/hacBrewPack/config.mk
make -C work/hacBrewPack -j"$(nproc)"
gcc -O2 -Iwork/lz4/lib work/switch-tools/src/elf2nso.c work/switch-tools/src/sha256.c work/lz4/lib/lz4.c -o work/tools/elf2nso
gcc -O2 work/switch-tools/src/npdmtool.c work/switch-tools/src/cJSON.c -lm -o work/tools/npdmtool
curl -fL https://github.com/etonedemid/netsurf-switch/releases/download/v0.2.0/netsurf.nro -o work/netsurf.nro
python3 scripts/stage_nsp.py work/netsurf.nro work/stage --elf2nso work/tools/elf2nso --npdmtool work/tools/npdmtool --npdm-template work/hacBrewPack/template/npdm.json
TASK_KEYS="$(mktemp)"
trap 'rm -f "$TASK_KEYS"' EXIT
python3 scripts/minimal_keys.py "$KEYSET" "$TASK_KEYS"
work/hacBrewPack/hacbrewpack -k "$TASK_KEYS" --titleid 01f0b05e20261000 --titlename 'NetSurf 浏览器' --titlepublisher 'NetSurf Switch port' --exefsdir work/stage/exefs --romfsdir work/stage/romfs --controldir work/stage/control --nspdir dist --ncadir work/nca --tempdir work/pack-temp --backupdir work/backup --nologo
mv dist/01f0b05e20261000.nsp dist/NetSurf-Switch-0.2.0-experimental.nsp
cp work/stage/manifest.json dist/manifest.json
