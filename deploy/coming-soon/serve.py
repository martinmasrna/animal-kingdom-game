# Live while the game is rebuilt: every path answers with the one page.
from http.server import BaseHTTPRequestHandler, HTTPServer
PAGE = open("index.html", "rb").read()
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE))); self.end_headers(); self.wfile.write(PAGE)
    do_HEAD = lambda self: (self.send_response(200), self.end_headers())
    def log_message(self, *a): pass
HTTPServer(("0.0.0.0", 8080), H).serve_forever()
