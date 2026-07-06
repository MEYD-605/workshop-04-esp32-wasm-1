#!/usr/bin/env bash
# Remote-flash สมต่อ desk-pet ผ่าน Tailscale → MacBook Air (ที่เสียบบอร์ด)
# ใช้ตอนต่อพกบอร์ด+Air ออกนอกบ้าน: SomTor (MBP) ssh เข้า Air แล้ว flash ให้
#
# Prereq บน Air (ต่อทำ): System Settings → General → Sharing → Remote Login ON
#                        + `tailscale up`  + เสียบบอร์ด JC3248 (native USB)
# Prereq บน Air: esptool  (ถ้าไม่มี script จะ pip ติดตั้งให้ใน venv ชั่วคราว)
#
# Usage: ./remote-flash.sh <air-tailscale-host> [air-user] [PORT]
#   ./remote-flash.sh air-tor                 # user = $USER, port = auto
#   ./remote-flash.sh air-tor tor             # ระบุ user
#   ./remote-flash.sh air-tor tor /dev/cu.usbmodem1101
set -euo pipefail
cd "$(dirname "$0")"

HOST="${1:?ใส่ tailscale hostname ของ Air: ./remote-flash.sh <host> [user] [port]}"
USER_AIR="${2:-$USER}"
PORT="${3:-}"
DEST="$USER_AIR@$HOST"
REMOTE_DIR="/tmp/somtor-flash-kit"

echo "🐝 Remote-flash สมต่อ → $DEST"

# 0) reachable?
ssh -o ConnectTimeout=8 -o BatchMode=yes "$DEST" 'echo ok' >/dev/null 2>&1 \
  || { echo "❌ ssh เข้า $DEST ไม่ได้ — เช็ค Remote Login + tailscale up + hostname"; exit 1; }

# 1) ship the kit
echo "📦 scp flash-kit → $DEST:$REMOTE_DIR"
ssh "$DEST" "mkdir -p $REMOTE_DIR"
scp -q bootloader.bin partition-table.bin firmware.bin somtor-storage.bin "$DEST:$REMOTE_DIR/"

# 2) detect port ถ้าไม่ได้ระบุ
if [ -z "$PORT" ]; then
  PORT="$(ssh "$DEST" 'ls /dev/cu.usbmodem* 2>/dev/null | head -1' || true)"
  [ -z "$PORT" ] && { echo "❌ Air ไม่เจอ /dev/cu.usbmodem* — เสียบบอร์ดทาง native USB ก่อน"; exit 1; }
fi
echo "🔌 port บน Air: $PORT"

# 3) flash บน Air (เผื่อไม่มี esptool → ใช้ uvx ชั่วคราว)
echo "⚡ write_flash ..."
# NOTE: ใช้ if/elif (ไม่ใช่ subshell ( )) เพราะ ESP= ใน ( ) ไม่ persist ออกมา;
#       และใช้ `eval \$ESP` เพราะ zsh ไม่ word-split \$ESP แบบ bash (จะหา command
#       ชื่อ "python3 -m esptool" ทั้งก้อน → not found). eval ปลอดภัยทั้ง bash+zsh.
ssh "$DEST" "export PATH=\"\$HOME/.local/bin:\$PATH\"; cd $REMOTE_DIR && \
  if command -v esptool.py >/dev/null 2>&1; then ESP='esptool.py'; \
  elif python3 -m esptool version >/dev/null 2>&1; then ESP='python3 -m esptool'; \
  elif command -v uvx >/dev/null 2>&1; then ESP='uvx --from esptool esptool.py'; \
  else echo '⤵️  esptool ไม่มีบน Air → ติดตั้งผ่าน pip3 --user'; \
       pip3 install --user --quiet esptool && ESP='python3 -m esptool' \
       || { echo '❌ ติดตั้ง esptool ไม่ได้'; exit 1; }; fi; \
  echo \"using \$ESP\"; \
  eval \$ESP --chip esp32s3 --port '$PORT' --baud 921600 \
    --before default_reset --after hard_reset write_flash -z \
    --flash_mode dio --flash_freq 80m --flash_size detect \
    0x0 bootloader.bin 0x8000 partition-table.bin \
    0x10000 firmware.bin 0x290000 somtor-storage.bin"

echo "✅ เสร็จ — สมต่อมีร่างบนจอ Air แล้ว 🐝  (reset บอร์ดถ้าไม่ขึ้นเอง)"
