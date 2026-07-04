# Atom DeskPet CodexBar HUD snapshot

This folder is the source snapshot for Atom Oracle's JC3248 ESP32 desk-pet / CodexBar HUD iteration.
It is intentionally kept separate from the original `platformio/` wasm3 submission so the workshop artifact remains reviewable.

## What this adds

- Pet state page driven by Atom workboard queue state:
  - `idle.gif` when no work is running or waiting
  - `busy.gif` when `running > 0`
  - `attention.gif` when `waiting > 0`
  - `sleep.gif` when no task/session is open
- CodexBar HUD page for quota visibility:
  - Codex H5
  - Codex Week
  - Grok
  - Claude
  - C-WK
- Remaining-percent semantics for HUD bars (`pct = remaining`, drawn left-to-right).
- Reset-time fields for Grok / Claude / C-WK.
- Gesture/page handling for pet page ↔ CodexBar HUD page.
- 60-second host sync cadence and 75-second firmware freshness timeout.

## Host-side tools

`tools/atom-esp32-workboard-sync.py` reads Atom's queue DB and CodexBar CLI output, then writes the status payload to the Windows bridge JSON.

`tools/atom-esp32-set-status.sh` writes the JSON payload to the Windows host over SSH.

`tools/codexbar_erp_feed.py` produces an ERP-only JSON feed with no Discord write and no LLM call.

`tools/dashboard_server.py` serves the ERP dashboard JSON endpoints, including `codexbar_erp.json`.

## Runtime contract

The host sends compact serial payloads containing queue state, token count, remaining quota percentages, reset seconds, and optional page selection. The firmware parser is backward-compatible with older payloads.

## Verification snapshot

The live build/flash was verified on `COM3` before this snapshot was prepared. See `../docs/CODEXBAR-HUD-PROOF.md` for the serial/build evidence captured during the Discord run.
