import os
import logging
import subprocess
import urllib.parse
from pathlib import Path

# Simple API to bridge Browser and Script
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "punz_dashboard_server.log"
HOST = os.environ.get("PUNZ_DASHBOARD_HOST", "100.114.28.102")
PORT = int(os.environ.get("PUNZ_DASHBOARD_PORT", "18080"))
ALLOWED_FILES = {
    "/": "punz_dashboard.html",
    "/punz_dashboard.html": "punz_dashboard.html",
    "/punz_data.json": "punz_data.json",
    "/codexbar_erp.json": "codexbar_erp.json",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/update'):
            # Parse month from query string
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            month = params.get('month', ['June-2026'])[0]

            if not month.replace("-", "").isalnum():
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "invalid month"}')
                return

            # Execute calculation for that specific month
            result = subprocess.run(
                ["python3", str(BASE_DIR / "ot_workflow.py"), month],
                cwd=BASE_DIR,
                env={**os.environ, "GOG_SECRET_BACKEND": "file"},
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logging.error(
                    "ot update failed month=%s returncode=%s stdout=%s stderr=%s",
                    month,
                    result.returncode,
                    result.stdout.strip(),
                    result.stderr.strip(),
                )
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "update failed"}')
                return

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            logging.info("ot update ok month=%s", month)
        else:
            request_path = urllib.parse.urlparse(self.path).path
            filename = ALLOWED_FILES.get(request_path)
            if not filename:
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'not found')
                return

            self.path = "/" + filename
            super().do_GET()

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    server = HTTPServer((HOST, PORT), CustomHandler)
    logging.info("Dashboard server running on %s:%s", HOST, PORT)
    server.serve_forever()
