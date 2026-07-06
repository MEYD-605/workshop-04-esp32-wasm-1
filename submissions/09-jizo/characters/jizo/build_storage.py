#!/usr/bin/env python3
# Build jizo's 3MB LittleFS storage for the shared jc3248-pet (recipe from Tonk/Weizen, no ESP-IDF).
import os
from littlefs import LittleFS
PACK=os.path.dirname(os.path.abspath(__file__))
OUT=os.environ.get("OUT",os.path.join(PACK,"jizo-storage.bin"))
SIZE=0x300000
fs=LittleFS(block_size=4096,block_count=SIZE//4096)
fs.makedirs("/characters/jizo",exist_ok=True)
for fn in sorted(f for f in os.listdir(PACK) if f.endswith(".gif")):
    data=open(f"{PACK}/{fn}","rb").read()
    with fs.open(f"/characters/jizo/{fn}","wb") as fh: fh.write(data)
    print(f"  + /characters/jizo/{fn} {len(data)}B")
img=bytes(fs.context.buffer); open(OUT,"wb").write(img); print("wrote",OUT,len(img),"bytes")
fs2=LittleFS(block_size=4096,block_count=SIZE//4096,mount=False); fs2.context.buffer[:]=bytearray(img); fs2.mount()
print("remount ->",fs2.listdir("/characters/jizo"))
