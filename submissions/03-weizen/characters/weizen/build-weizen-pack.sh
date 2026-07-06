#!/usr/bin/env bash
# Build the "weizen" desk-pet pack — 7 original 96x100 GIF89a states for the jc3248-pet roster.
# Unlike the cat/clawd packs (ImageMagick + gifsicle over downloaded sprites), this pack is
# 100% generated art, so the only dependency is Python + Pillow — works on a headless VM.
#   ./build-weizen-pack.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
"$PY" -c "import PIL" 2>/dev/null || { echo "need Pillow: pip install pillow"; exit 1; }
echo "🍺 drawing weizen pack → $HERE"
OUT="$HERE" "$PY" "$HERE/gen_weizen_pack.py"
echo "🍺 done:"; for s in sleep idle busy attention celebrate dizzy heart; do
  printf "  %-12s %6sB\n" "$s.gif" "$(wc -c <"$HERE/$s.gif" | tr -d ' ')"
done
