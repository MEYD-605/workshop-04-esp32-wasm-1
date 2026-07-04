# CodexBar HUD proof snapshot

Date: 2026-07-04/05 Asia/Bangkok

## Firmware build / flash evidence

```text
RAM: 36.8%
Flash: 56.7%
[SUCCESS] upload COM3
Hash of data verified
```

## Remaining-percent status evidence

```text
TX STATUS|...|65|...|51|...|87|86|98|...
RX [bridge] usage pct5h=65 pct7d=51 grok=87 claude=86 cwk=98
RX [bridge] serial status applied
```

## 60-second cadence evidence

```text
23:21:29 TX STATUS ... |65|...|51|...|87|86|98|...
23:22:30 TX STATUS ... |65|...|51|...|87|86|98|...
```

## ERP feed contract

```text
schema: codexbar-erp-feed/v1
llmUsed: false
discordTouched: false
displayMode: remaining
```

## Notes

- The firmware source here is a source snapshot of the JC3248 desk-pet firmware used in the live flash.
- The original wasm3 PlatformIO submission remains untouched.
- The ERP feed and ESP sync are script-driven and do not spend LLM quota.
