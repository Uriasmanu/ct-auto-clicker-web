import argparse
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

START = time.time()
AFTER = 30.0

PAGE = """<html><body>
<div class="status">{status}</div>
<button {disabled} onclick="location.href='/ok'">Comprar</button>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ok":
            body = "<html><body><p>Pedido confirmado</p></body></html>"
        else:
            ready = time.time() - START >= AFTER
            body = PAGE.format(
                status="Disponivel" if ready else "Esgotado",
                disabled="" if ready else "disabled",
            )
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--after", type=float, default=30.0)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    AFTER = args.after
    print(f"Servindo em http://localhost:{args.port}/ (botão habilita em {AFTER:.0f}s)")
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
