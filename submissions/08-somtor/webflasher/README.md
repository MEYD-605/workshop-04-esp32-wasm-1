# สมต่อ 🐝 Web Flasher

Flash สมต่อ desk-pet จาก browser (Chrome/Edge) — ไม่ต้อง esptool/ssh.
ใช้ [esp-web-tools](https://github.com/esphome/esp-web-tools)@9.4.3 (Web Serial).

## ใช้งาน

self-contained — bins อยู่ใน `firmware/` แล้ว. แค่เสิร์ฟผ่าน HTTPS หรือ localhost:

```bash
python3 -m http.server 8080      # ในโฟลเดอร์นี้
```

เปิด Chrome → `http://localhost:8080/` → เสียบบอร์ด JC3248 → กด **"เชื่อมต่อบอร์ด แล้ว flash สมต่อ"**.

## Manifest (ESP32-S3, 4 parts)

| offset | part |
|--------|------|
| `0x0` | firmware/bootloader.bin |
| `0x8000` | firmware/partition-table.bin |
| `0x10000` | firmware/firmware.bin (generic — opendir scan `/littlefs/characters/`) |
| `0x290000` | firmware/somtor-storage.bin (3MB littlefs) |

> สำหรับ flasher กลางของ workshop ดู `docs/flasher.html` (pack `docs/packs/somtor.json`).
