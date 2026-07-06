#!/usr/bin/env python3
"""Sync Atom workboard/queue + CodexBar quota metadata to ESP32 status file."""
from __future__ import annotations
import json, os, sqlite3, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

DB = Path(os.getenv("ATOM_NATIVE_DB", "/home/axezii/atom-native/data/atom-native.sqlite"))
SET_STATUS = Path("/home/axezii/atom/scripts/atom-esp32-set-status.sh")
CODEXBAR = os.getenv("CODEXBAR_BIN", "/home/axezii/.local/bin/codexbar")
CACHE = Path("/home/axezii/atom/tmp/atom_esp32_quota_cache.json")
ERP_FEED = Path("/home/axezii/.openclaw/workspace/codexbar_erp.json")
WORK_CACHE = Path("/home/axezii/atom/tmp/atom_esp32_work_state.json")

def counts():
    out = {"running": 0, "pending": 0, "failed": 0, "done": 0}
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=3)
    try:
        cur = con.execute("SELECT lower(status), count(*) FROM work_queue GROUP BY lower(status)")
        for status, n in cur.fetchall():
            if status in ("running", "processing", "claimed", "in_progress"):
                out["running"] += int(n)
            elif status in ("pending", "queued", "held_quota"):
                out["pending"] += int(n)
            elif status == "failed":
                out["failed"] += int(n)
            elif status == "done":
                out["done"] += int(n)
    finally:
        con.close()
    return out

def parse_reset_seconds(value):
    if not value:
        return -1
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return max(0, int((dt - datetime.now(timezone.utc)).total_seconds()))
    except Exception:
        return -1

def run_codexbar(provider, source, timeout=25):
    try:
        p = subprocess.run(
            [CODEXBAR, "usage", "--provider", provider, "--source", source, "--format", "json", "--no-color"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False,
            env={**os.environ, "PATH": "/home/axezii/.local/bin:/home/axezii/.nvm/versions/node/v22.23.0/bin:/home/axezii/.nvm/versions/node/v22.22.0/bin:" + os.environ.get("PATH", "")},
        )
        if p.returncode != 0:
            return None, (p.stderr or p.stdout or f"exit {p.returncode}").strip()[:180]
        data = json.loads(p.stdout)
        if not isinstance(data, list) or not data:
            return None, "empty payload"
        if "error" in data[0]:
            return None, json.dumps(data[0]["error"], ensure_ascii=False)[:180]
        return data[0], ""
    except Exception as e:
        return None, repr(e)[:180]

def used_percent(payload, window="primary"):
    try:
        v = (payload.get("usage") or {}).get(window) or {}
        return int(round(float(v.get("usedPercent"))))
    except Exception:
        return -1

def reset_seconds(payload, window="primary"):
    v = (payload.get("usage") or {}).get(window) or {}
    return parse_reset_seconds(v.get("resetsAt"))

def remaining_percent(payload, window="primary"):
    used = used_percent(payload, window)
    if used < 0:
        return -1
    return max(0, min(100, 100 - used))

def load_quota_cache():
    cache = {}
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8")).get("quota", {})
    except Exception:
        cache = {}
    # Seed/repair from ERP feed, which already keeps last-good Claude values.
    try:
        erp = json.loads(ERP_FEED.read_text(encoding="utf-8"))
        providers = erp.get("providers") or {}
        mapped = {
            "pct5h": int((providers.get("codex", {}).get("primary") or {}).get("remainPercent", -1)),
            "reset5h": -1,
            "pct7d": int((providers.get("codex", {}).get("secondary") or {}).get("remainPercent", -1)),
            "reset7d": -1,
            "grok": int((providers.get("grok", {}).get("primary") or {}).get("remainPercent", -1)),
            "resetGrok": -1,
            "claude": int((providers.get("claude", {}).get("primary") or {}).get("remainPercent", -1)),
            "cwk": int((providers.get("claude", {}).get("secondary") or {}).get("remainPercent", -1)),
            "resetClaude": -1,
            "resetCwk": -1,
        }
        # Keep existing reset seconds if present; ERP feed reset is absolute timestamp, local codexbar run will refresh seconds.
        for k, v in mapped.items():
            if k not in cache or int(cache.get(k, -1)) < 0:
                cache[k] = v
    except Exception:
        pass
    return cache

def save_quota_cache(result):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    previous = load_quota_cache()
    keep = {}
    for k, v in result.items():
        if k == "errors":
            continue
        if isinstance(v, int) and v < 0 and isinstance(previous.get(k), int) and previous[k] >= 0:
            keep[k] = previous[k]
        else:
            keep[k] = v
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"updatedAt": datetime.now(timezone.utc).isoformat(), "quota": keep}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CACHE)

def fill_from_cache(result, cache, keys):
    for k in keys:
        if result.get(k, -1) < 0 and isinstance(cache.get(k), int):
            result[k] = cache[k]

def quota():
    # Background-safe sources first; if a provider flickers, keep last known good values.
    cache = load_quota_cache()
    result = {
        "pct5h": -1, "reset5h": -1, "pct7d": -1, "reset7d": -1,
        "grok": -1, "claude": -1, "cwk": -1,
        "resetGrok": -1, "resetClaude": -1, "resetCwk": -1,
        "errors": [],
    }
    codex, err = run_codexbar("codex", "oauth")
    if codex:
        r5 = remaining_percent(codex, "primary"); r7 = remaining_percent(codex, "secondary")
        result["pct5h"] = r5 if r5 >= 0 else -1
        result["pct7d"] = r7 if r7 >= 0 else -1
        result["reset5h"] = reset_seconds(codex, "primary")
        result["reset7d"] = reset_seconds(codex, "secondary")
    else:
        result["errors"].append("codex:" + err)
        fill_from_cache(result, cache, ["pct5h", "reset5h", "pct7d", "reset7d"])
    # Grok/Claude reset times: only set if the source actually reports resetsAt (fmt_reset
    # on the firmware side already renders "--" for -1 — never guess a fake reset time here).
    grok, err = run_codexbar("grok", "web", timeout=20)
    if grok:
        result["grok"] = remaining_percent(grok, "primary")
        result["resetGrok"] = reset_seconds(grok, "primary")
    else:
        result["errors"].append("grok:" + err)
        fill_from_cache(result, cache, ["grok", "resetGrok"])
    claude, err = run_codexbar("claude", "oauth", timeout=20)
    if claude:
        result["claude"] = remaining_percent(claude, "primary")
        result["cwk"] = remaining_percent(claude, "secondary")
        result["resetClaude"] = reset_seconds(claude, "primary")
        result["resetCwk"] = reset_seconds(claude, "secondary")
    else:
        result["errors"].append("claude:" + err)
        fill_from_cache(result, cache, ["claude", "cwk", "resetClaude", "resetCwk"])
    save_quota_cache(result)
    return result

def load_work_cache():
    try:
        return json.loads(WORK_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_work_cache(q):
    WORK_CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = WORK_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"updatedAt": datetime.now(timezone.utc).isoformat(), "queue": q}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(WORK_CACHE)

def runtime_event(q, qu):
    prev = (load_work_cache().get("queue") or {})
    event = {"forceState": "", "forceMs": 0, "page": "pin", "ticker": ""}
    errors = qu.get("errors") or []
    if errors:
        event["forceState"] = "dizzy"
        event["forceMs"] = 5000
        event["ticker"] = ("ERR " + errors[0])[:70]
    else:
        try:
            prev_running = int(prev.get("running", 0))
            prev_done = int(prev.get("done", 0))
        except Exception:
            prev_running = prev_done = 0
        if prev_running > 0 and q.get("running", 0) == 0 and q.get("done", 0) >= prev_done:
            event["forceState"] = "celebrate"
            event["forceMs"] = 4500
            event["ticker"] = "job complete"
    return event

def main():
    q = counts()
    qu = quota()
    event = runtime_event(q, qu)
    if q["running"] > 0:
        state = "busy"
    elif q["pending"] > 0:
        state = "attention"
    else:
        state = "idle"
    msg = event.get("ticker") or f"WB run {q['running']} wait {q['pending']} fail {q['failed']}"
    cmd = [
        str(SET_STATUS), state, msg, "0",
        str(qu["pct5h"]), str(qu["reset5h"]), str(qu["pct7d"]), str(qu["reset7d"]),
        str(qu["grok"]), str(qu["claude"]), str(qu["cwk"]), event.get("page", ""),
        str(qu["resetGrok"]), str(qu["resetClaude"]), str(qu["resetCwk"]),
        event.get("forceState", ""), str(event.get("forceMs", 0)),
    ]
    subprocess.run(cmd, check=True)
    save_work_cache(q)
    summary = {"state": state, "queue": q, "quota": qu, "event": event, "sent": cmd[1:]}
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()
