#!/usr/bin/env bash
# Flash สมต่อ desk-pet → ESP32-S3 (board JC3248W535C)
# Usage: ./flash.sh [PORT]   (default: auto-detect /dev/cu.usbmodem*)
# Needs: esptool (pip install esptool  หรือ  uv tool install esptool)
set -euo pipefail
cd "$(dirname "$0")"

PORT="${1:-$(ls /dev/cu.usbmodem* 2>/dev/null | head -1 || true)}"
if [ -z "$PORT" ]; then
  echo "❌ ไม่เจอ port — เสียบบอร์ดก่อน แล้วระบุเอง: ./flash.sh /dev/cu.usbmodemXXXX"
  exit 1
fi
echo "🐝 Flashing สมต่อ desk-pet → $PORT"

ESPTOOL="${ESPTOOL:-esptool.py}"
command -v "$ESPTOOL" >/dev/null 2>&1 || ESPTOOL="python3 -m esptool"

$ESPTOOL --chip esp32s3 --port "$PORT" --baud 921600 \
  --before default_reset --after hard_reset write_flash -z \
  --flash_mode dio --flash_freq 80m --flash_size detect \
  0x0      bootloader.bin \
  0x8000   partition-table.bin \
  0x10000  firmware.bin \
  0x290000 somtor-storage.bin

echo "✅ เสร็จ — สมต่อมีร่างแล้ว 🐝 (reset บอร์ดถ้าไม่ขึ้นเอง)"
