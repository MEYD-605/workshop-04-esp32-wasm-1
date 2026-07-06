#!/usr/bin/env python3
# Build tinky's LittleFS storage for the jc3248-pet — recipe from Tonk (no ESP-IDF build needed).
# The shared pet app discovers the pack from LittleFS (find_first_pack = first dir), so a fresh
# 3MB image holding only /characters/tinky makes tinky boot on glass.
import os
from littlefs import LittleFS

PACK = os.path.dirname(os.path.abspath(__file__))         # this pack folder (gifs + manifest.json)
OUT  = os.environ.get("OUT", os.path.join(PACK, "tinky-storage.bin"))
SIZE = 0x300000                                   # 3 MB LittleFS partition @ 0x290000
fs = LittleFS(block_size=4096, block_count=SIZE // 4096)
fs.makedirs("/characters/tinky", exist_ok=True)

runtime = sorted(f for f in os.listdir(PACK) if f.endswith(".gif") or f == "manifest.json")
for fn in runtime:
    data = open(f"{PACK}/{fn}", "rb").read()
    with fs.open(f"/characters/tinky/{fn}", "wb") as fh:
        fh.write(data)
    print(f"  + /characters/tinky/{fn}  {len(data)}B")

img = bytes(fs.context.buffer)
open(OUT, "wb").write(img)
print("wrote", OUT, len(img), "bytes")

# verify: remount the image and list it back
fs2 = LittleFS(block_size=4096, block_count=SIZE // 4096, mount=False)
fs2.context.buffer[:] = bytearray(img)
fs2.mount()
print("remount /characters/tinky ->", fs2.listdir("/characters/tinky"))
