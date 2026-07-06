from littlefs import LittleFS
import os

ROOT = os.path.dirname(__file__)
PACK_ID = "sombo"
PACK = os.path.join(ROOT, "characters", PACK_ID)

# ESP-IDF LittleFS geometry: block 4096, 3 MB partition -> 768 blocks.
fs = LittleFS(block_size=4096, block_count=0x300000 // 4096)
fs.makedirs(f"/characters/{PACK_ID}", exist_ok=True)

for fn in sorted(os.listdir(PACK)):
    src = os.path.join(PACK, fn)
    if not os.path.isfile(src):
        continue
    if not (fn.endswith(".gif") or fn == "manifest.json"):
        continue
    with open(src, "rb") as f:
        data = f.read()
    with fs.open(f"/characters/{PACK_ID}/{fn}", "wb") as w:
        w.write(data)
    print(f"  + characters/{PACK_ID}/{fn} ({len(data)}B)")

img = bytes(fs.context.buffer)
out = os.path.join(ROOT, "sombo-storage.bin")
with open(out, "wb") as f:
    f.write(img)
print("sombo-storage.bin:", len(img), "bytes")
