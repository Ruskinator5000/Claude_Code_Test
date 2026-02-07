#!/usr/bin/env python3
"""HTTP server that serves static files and proxies chat requests to n8n."""

import http.server
import json
import os
import urllib.parse
import urllib.request

PORT = int(os.environ.get("PORT", 8000))
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/chat":
            self._handle_chat(parsed)
        else:
            super().do_GET()

    def _handle_chat(self, parsed):
        if not N8N_WEBHOOK_URL:
            self._json_response(500, {"error": "N8N_WEBHOOK_URL not configured"})
            return

        qs = urllib.parse.parse_qs(parsed.query)
        message = qs.get("message", [""])[0]
        if not message:
            self._json_response(400, {"error": "message parameter required"})
            return

        try:
            url = N8N_WEBHOOK_URL + "?message=" + urllib.parse.quote(message, safe="")
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self._json_response(502, {"error": str(e)})

    def _json_response(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())


if __name__ == "__main__":
    with http.server.HTTPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()
