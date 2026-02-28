import os
import json
import http.server
import socketserver
import sys

ROOT = os.path.dirname(__file__)
WEB_DIR = os.path.join(ROOT, "web")
DATA_PATH = os.path.join(WEB_DIR, "data.jsonl")
RAG_PATH = os.path.join(WEB_DIR, "rag.jsonl")
INDEX_PATH = os.path.join(WEB_DIR, "index.html")
LOC_NAME = os.environ.get("FRONTEND_LOCATION")

class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, ctype="text/plain", body=b""):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        if body:
            self.wfile.write(body)
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(INDEX_PATH, "rb") as f:
                    self._send(200, "text/html; charset=utf-8", f.read())
            except FileNotFoundError:
                self._send(404)
        elif self.path == "/api/latest":
            try:
                last = None
                with open(DATA_PATH, "rb") as f:
                    for line in f:
                        if line.strip():
                            last = line
                if not last and os.path.exists(RAG_PATH):
                    with open(RAG_PATH, "rb") as f:
                        for line in f:
                            if line.strip():
                                last = line
                if last:
                    self._send(200, "application/json", last)
                else:
                    self._send(204)
            except FileNotFoundError:
                self._send(404)
        elif self.path == "/api/latest-rag":
            try:
                last = None
                with open(RAG_PATH, "rb") as f:
                    for line in f:
                        if line.strip():
                            last = line
                if last:
                    self._send(200, "application/json", last)
                else:
                    self._send(204)
            except FileNotFoundError:
                self._send(404)
        elif self.path == "/api/location":
            if LOC_NAME:
                self._send(200, "application/json", json.dumps({"name": LOC_NAME}).encode())
            else:
                self._send(204)
        else:
            self._send(404)

def main():
    os.makedirs(WEB_DIR, exist_ok=True)
    start = int(os.environ.get("FRONTEND_PORT", "8001"))
    for p in range(start, start + 20):
        try:
            with socketserver.TCPServer(("", p), Handler) as httpd:
                print(f"http://localhost:{p}/")
                httpd.serve_forever()
        except OSError:
            continue
    print("no free port")
    sys.exit(1)

if __name__ == "__main__":
    main()
