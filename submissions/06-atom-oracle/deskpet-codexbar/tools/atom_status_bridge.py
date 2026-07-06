import json, pathlib, time, traceback
import serial
STATUS = pathlib.Path(r"C:\Users\axeziiezakk\atom-native-status.json")
LOG = pathlib.Path(r"C:\Users\axeziiezakk\atom-native-status-bridge.log")
PORT = "COM3"
BAUD = 115200
INTERVAL = 60.0

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")

def to_int(data, key, default):
    try:
        return int(data.get(key, default))
    except Exception:
        return default

def read_status():
    try:
        data = json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    msg = str(data.get("msg", "Atom idle")).replace("\n", " ").replace("|", "/")[:90]
    return {
        "total": to_int(data, "total", 1),
        "running": to_int(data, "running", 0),
        "waiting": to_int(data, "waiting", 0),
        "tokens": to_int(data, "tokens", 0),
        "msg": msg,
        "pct5h": to_int(data, "pct5h", -1),
        "reset5h": to_int(data, "reset5h", -1),
        "pct7d": to_int(data, "pct7d", -1),
        "reset7d": to_int(data, "reset7d", -1),
        "grok": to_int(data, "grok", -1),
        "claude": to_int(data, "claude", -1),
        "cwk": to_int(data, "cwk", -1),
        "resetGrok": to_int(data, "resetGrok", -1),
        "resetClaude": to_int(data, "resetClaude", -1),
        "resetCwk": to_int(data, "resetCwk", -1),
        "page": data.get("page"),
        "forceState": data.get("forceState"),
        "forceMs": to_int(data, "forceMs", 0),
    }

def drain(ser, seconds=1.2):
    deadline = time.time() + seconds
    while time.time() < deadline:
        raw = ser.readline()
        if raw:
            text = raw.decode("utf-8", errors="replace").strip()
            if text:
                log("RX " + text[:220])

def main():
    log("bridge starting")
    while True:
        try:
            with serial.Serial(PORT, BAUD, timeout=0.25) as ser:
                log(f"opened {PORT}")
                time.sleep(3.0)
                last_page = None
                while True:
                    st = read_status()
                    page = st.get("page")
                    if page is not None and page != last_page:
                        pline = f"PAGE|{page}\n"
                        ser.write(pline.encode("utf-8", errors="replace")); ser.flush()
                        log("TX " + pline.strip())
                        drain(ser, 0.8)
                        last_page = page
                    force_state = st.get("forceState")
                    if force_state:
                        fline = f"STATE|{force_state}|{st.get('forceMs') or 3500}\n"
                        ser.write(fline.encode("utf-8", errors="replace")); ser.flush()
                        log("TX " + fline.strip())
                        drain(ser, 0.8)
                    line = (
                        f"STATUS|{st['total']}|{st['running']}|{st['waiting']}|{st['tokens']}|{st['msg']}|"
                        f"{st['pct5h']}|{st['reset5h']}|{st['pct7d']}|{st['reset7d']}|"
                        f"{st['grok']}|{st['claude']}|{st['cwk']}|"
                        f"{st['resetGrok']}|{st['resetClaude']}|{st['resetCwk']}\n"
                    )
                    ser.write(line.encode("utf-8", errors="replace"))
                    ser.flush()
                    log("TX " + line.strip())
                    drain(ser, 1.2)
                    time.sleep(INTERVAL)
        except Exception as exc:
            log("ERROR " + repr(exc))
            log(traceback.format_exc().replace("\n", " | ")[:1200])
            time.sleep(5.0)

if __name__ == "__main__":
    main()
