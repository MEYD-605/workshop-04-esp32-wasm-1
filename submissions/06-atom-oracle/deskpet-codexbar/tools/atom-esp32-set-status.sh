#!/usr/bin/env bash
set -euo pipefail
STATE=${1:-idle}
MSG=${2:-}
TOKENS=${3:-0}
PCT5H=${4:--1}
RESET5H=${5:--1}
PCT7D=${6:--1}
RESET7D=${7:--1}
GROK=${8:--1}
CLAUDE=${9:--1}
CWK=${10:--1}
PAGE=${11:-}
RESET_GROK=${12:--1}
RESET_CLAUDE=${13:--1}
RESET_CWK=${14:--1}
REMOTE=${ATOM_ESP32_REMOTE:-axeziiezakk@axeziiezakk-main}
python3 - <<'PY' "$STATE" "$MSG" "$TOKENS" "$PCT5H" "$RESET5H" "$PCT7D" "$RESET7D" "$GROK" "$CLAUDE" "$CWK" "$PAGE" "$REMOTE" "$RESET_GROK" "$RESET_CLAUDE" "$RESET_CWK"
import base64, json, subprocess, sys
_, state, msg, tokens, pct5h, reset5h, pct7d, reset7d, grok, claude, cwk, page, remote, reset_grok, reset_claude, reset_cwk = sys.argv
state = state.strip().lower()
if state == "busy":
    payload = {"total": 1, "running": 1, "waiting": 0}
elif state == "attention":
    payload = {"total": 1, "running": 0, "waiting": 1}
elif state == "sleep":
    payload = {"total": 0, "running": 0, "waiting": 0}
else:
    payload = {"total": 1, "running": 0, "waiting": 0}
payload["tokens"] = int(tokens or 0)
payload["msg"] = (msg or f"Atom {state}").replace("`", "").replace("|", "/").replace("\n", " ")[:90]
payload["pct5h"] = int(pct5h or -1)
payload["reset5h"] = int(reset5h or -1)
payload["pct7d"] = int(pct7d or -1)
payload["reset7d"] = int(reset7d or -1)
payload["grok"] = int(grok or -1)
payload["claude"] = int(claude or -1)
payload["cwk"] = int(cwk or -1)
payload["resetGrok"] = int(reset_grok or -1)
payload["resetClaude"] = int(reset_claude or -1)
payload["resetCwk"] = int(reset_cwk or -1)
if page != "":
    payload["page"] = page
raw = json.dumps(payload, ensure_ascii=False)
ps = r'''
$ErrorActionPreference = 'Stop'
$path = 'C:\Users\axeziiezakk\atom-native-status.json'
$tmp = "$path.tmp"
$json = @'
__JSON__
'@
[System.IO.File]::WriteAllText($tmp, $json, [System.Text.UTF8Encoding]::new($false))
Move-Item -Force $tmp $path
Write-Output "STATUS_FILE $json"
'''.replace('__JSON__', raw)
b64 = base64.b64encode(ps.encode('utf-16le')).decode()
subprocess.run(['ssh', remote, 'powershell', '-NoProfile', '-EncodedCommand', b64], check=True)
PY
