#!/usr/bin/env python3
"""Build vialumen-storage.bin — 3 MB LittleFS holding only /characters/vialumen-pet/
so the shared jc3248-pet app auto-discovers + boots the ViaLumen pack."""
import os
from littlefs import LittleFS

PACK_SRC = "submissions/05-vialumen/characters/vialumen-pet"
DEST_DIR = "/characters/vialumen-pet"
OUT = "docs/vialumen-storage.bin"
SIZE = 0x300000  # 3 MB partition @ 0x290000

fs = LittleFS(block_size=4096, block_count=SIZE // 4096)
fs.makedirs(DEST_DIR, exist_ok=True)
for fn in sorted(os.listdir(PACK_SRC)):
    p = os.path.join(PACK_SRC, fn)
    if not os.path.isfile(p) or not (fn.endswith(".gif") or fn == "manifest.json"):
        continue
    data = open(p, "rb").read()
    with fs.open(f"{DEST_DIR}/{fn}", "wb") as o:
        o.write(data)
    print(f"  + {DEST_DIR}/{fn}  {len(data)} bytes")

buf = bytes(fs.context.buffer)
assert len(buf) == SIZE
open(OUT, "wb").write(buf)
print(f"wrote {OUT}  {len(buf)} bytes (0x{len(buf):X})")
