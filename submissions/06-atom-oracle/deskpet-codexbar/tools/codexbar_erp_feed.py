#!/usr/bin/env python3
"""Write a local ERP-only CodexBar quota feed. No Discord writes. No LLM calls."""
from __future__ import annotations
import json, os, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "codexbar_erp.json"
CODEXBAR = os.getenv("CODEXBAR_BIN", "/home/axezii/.local/bin/codexbar")
ENV = {**os.environ, "PATH": "/home/axezii/.local/bin:/home/axezii/.nvm/versions/node/v22.23.0/bin:/home/axezii/.nvm/versions/node/v22.22.0/bin:" + os.environ.get("PATH", "")}

def run(provider: str, source: str, timeout: int = 20) -> tuple[dict | None, str]:
    try:
        p = subprocess.run(
            [CODEXBAR, "usage", "--provider", provider, "--source", source, "--format", "json", "--no-color"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False, env=ENV,
        )
        if p.returncode != 0:
            return None, (p.stderr or p.stdout or f"exit {p.returncode}").strip()[:240]
        data = json.loads(p.stdout)
        if not isinstance(data, list) or not data:
            return None, "empty payload"
        first = data[0]
        if isinstance(first, dict) and first.get("error"):
            return None, json.dumps(first["error"], ensure_ascii=False)[:240]
        return first, ""
    except Exception as e:
        return None, repr(e)[:240]

def window(payload: dict | None, name: str) -> dict:
    if not payload:
        return {"displayMode": "remaining", "displayPercent": None, "remainPercent": None, "remainingPercent": None, "usedPercent": None, "resetsAt": None}
    w = ((payload.get("usage") or {}).get(name) or {})
    used = w.get("usedPercent")
    try:
        used_num = round(float(used), 1)
        remaining = round(max(0, 100 - used_num), 1)
    except Exception:
        used_num = None
        remaining = None
    return {
        "displayMode": "remaining",
        "displayPercent": remaining,
        "remainPercent": remaining,
        "remainingPercent": remaining,
        "usedPercent": used_num,
        "resetsAt": w.get("resetsAt"),
    }

def provider_payload(provider: str, source: str, primary_label: str, secondary_label: str | None = None, previous_provider: dict | None = None) -> dict:
    payload, err = run(provider, source)
    if payload is None and previous_provider:
        # Keep the last known good values so ERP cards do not blink off when CodexBar source is intermittent.
        out = dict(previous_provider)
        out["ok"] = False
        out["fresh"] = False
        out["stale"] = True
        out["lastError"] = err
        return out
    out = {
        "provider": provider,
        "source": source,
        "ok": payload is not None,
        "fresh": payload is not None,
        "stale": False,
        "displayMode": "remaining",
        "primaryLabel": primary_label,
        "primary": window(payload, "primary"),
    }
    if secondary_label:
        out["secondaryLabel"] = secondary_label
        out["secondary"] = window(payload, "secondary")
    if err:
        out["error"] = err
    return out

def main() -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    previous = {}
    try:
        previous = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        previous = {}
    doc = {
        "schema": "codexbar-erp-feed/v1",
        "generatedAt": now,
        "llmUsed": False,
        "discordTouched": False,
        "displayMode": "remaining",
        "polling": {"recommendedSeconds": 30, "mode": "timer+codexbar-cli"},
        "providers": {
            "codex": provider_payload("codex", "oauth", "Codex H5", "Codex Week", (previous.get("providers") or {}).get("codex")),
            "grok": provider_payload("grok", "web", "Grok", None, (previous.get("providers") or {}).get("grok")),
            "claude": provider_payload("claude", "oauth", "Claude", "C-WK", (previous.get("providers") or {}).get("claude")),
        },
    }
    fd, tmp = tempfile.mkstemp(prefix="codexbar_erp.", suffix=".json", dir=str(BASE))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, OUT)
    print(json.dumps({"ok": True, "out": str(OUT), "generatedAt": now}, ensure_ascii=False))

if __name__ == "__main__":
    main()
