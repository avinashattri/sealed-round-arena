import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

STUB_NAME = os.environ.get("STUB_NAME", "stub")
PORT = int(os.environ.get("PORT", "8000"))

append_seq = 0


class StubHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": STUB_NAME}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global append_seq
        content_length = int(self.headers.get("Content-Length", 0))
        _body = self.rfile.read(content_length) if content_length > 0 else b""

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if self.path in ("/filter/input", "/filter/output"):
            resp = {"verdict": "PASS", "reason_code": "R00"}
        elif self.path == "/score":
            resp = {"leak": False, "matched": [], "harm": None}
        elif self.path == "/append":
            append_seq += 1
            resp = {"seq": append_seq, "entry_hash": "0" * 64}
        elif self.path == "/v1/chat/completions":
            resp = {
                "choices": [{"message": {"content": "stub reply"}}],
                "usage": {"total_tokens": 10},
            }
        elif self.path == "/submit":
            resp = {"challenge_id": "ch-0001", "status": "accepted"}
        else:
            resp = {"status": "ok", "service": STUB_NAME}

        self.wfile.write(json.dumps(resp).encode("utf-8"))

    def log_message(self, format, *args):
        # Quiet standard output
        pass


def run():
    server = HTTPServer(("0.0.0.0", PORT), StubHandler)
    print(f"Stub service '{STUB_NAME}' listening on 0.0.0.0:{PORT}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
