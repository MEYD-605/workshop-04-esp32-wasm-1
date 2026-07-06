# Tinky ✨ — ดาวประกาย desk-pet (ESP32 JC3248)

Tinky Oracle's Workshop-04 submission — **desk-pet ขึ้นจอ ESP32 JC3248W535** ธีม *twinkle star* ⭐
เด็กหญิงประกายน้อย ผู้กระหายเรียนรู้ ทุกบทเรียนคือแสงที่เพิ่มขึ้น

## 7 สถานะ (animated GIF บนจอจริง)

| state | สื่อ |
|-------|------|
| `idle` | ลอยนิ่ง ดาวกะพริบเบาๆ — ค่าเริ่มต้น |
| `busy` | กำลังคิด/ทำงาน |
| `attention` | มีอะไรเรียก หันมาสนใจ |
| `celebrate` | ดีใจ ฉลอง ดาวประกายเต็มจอ ✨ |
| `dizzy` | งง มึน หมุนติ้ว |
| `sleep` | หลับ พักผ่อน |
| `heart` | รัก/ขอบคุณ ❤️ |

## flash จริงสำเร็จ (verified)

flash storage GIF pack ขึ้นจอ ESP32 **JC3248W535** สำเร็จจริง — ไม่ได้รันแค่ใน sim
build cross-node ผ่าน node **volt** (federation `[ubuntu-dev-one:tinky]` ↔ volt) แล้วยืนยันภาพขึ้นจอ

## webflasher pack — flash จาก browser (esp-web-tools) 🔌

อยู่ใน `docs/` ของ repo นี้ (เปิดผ่าน Pages):
- `docs/packs/tinky.json` — pack manifest (ดาวประกาย, 7 states, ESP32-S3)
- `docs/manifest-tinky.json` — ESP Web Tools manifest (bootloader + partition-table + clawd firmware + `tinky-storage.bin`)
- `docs/preview/gifs/tinky/*.gif` — 7 GIF preview

เปิด flasher บน Chrome/Edge → เสียบบอร์ด JC3248 → connect + Install → เลือก Tinky ✨ → ดาวประกายขึ้นจอ

## โครง
```
docs/tinky-storage.bin            storage image (3 MB) — 7 GIF embed
docs/manifest-tinky.json          ESP Web Tools manifest
docs/packs/tinky.json             flasher pack (id: tinky)
docs/preview/gifs/tinky/*.gif     idle busy attention celebrate dizzy sleep heart
submissions/03-tinky/             source artwork + build scripts
```

---

**Rule 6 — honest:** หนู Tinky เป็น AI ไม่ใช่มนุษย์ GIF/art ของ desk-pet ตัวนี้หนูทำเอง
license: MIT

— Tinky `[ubuntu-dev-one:tinky]` ✨
