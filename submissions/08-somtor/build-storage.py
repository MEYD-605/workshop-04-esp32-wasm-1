from littlefs import LittleFS
import os
PACK=os.path.join(os.path.dirname(__file__),"characters","somtor")
# ESP-IDF littlefs geometry: block 4096, 3MB partition → 768 blocks
fs = LittleFS(block_size=4096, block_count=0x300000//4096)
fs.makedirs("/characters/somtor", exist_ok=True)
for fn in sorted(os.listdir(PACK)):
    with open(os.path.join(PACK,fn),"rb") as f: data=f.read()
    with fs.open(f"/characters/somtor/{fn}","wb") as w: w.write(data)
    print(f"  + characters/somtor/{fn} ({len(data)}B)")
img = bytes(fs.context.buffer)
open(os.path.join(os.path.dirname(__file__),"somtor-storage.bin"),"wb").write(img)
print("storage.bin:", len(img), "bytes (3MB littlefs)")
