from __future__ import annotations

import http.client
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist" / "inventario-kardex-frontend" / "browser"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 4200


class FrontendProxyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_request()
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_request()
            return
        self.send_error(404, "Not found")

    def do_PUT(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_request()
            return
        self.send_error(404, "Not found")

    def do_PATCH(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_request()
            return
        self.send_error(404, "Not found")

    def do_DELETE(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_request()
            return
        self.send_error(404, "Not found")

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_request()
            return
        super().do_OPTIONS()

    def translate_path(self, path: str) -> str:
        translated = super().translate_path(path)
        target = Path(translated)
        if target.exists():
            return str(target)
        if "." not in Path(urlsplit(path).path).name:
            return str(DIST_DIR / "index.html")
        return str(target)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _proxy_request(self) -> None:
        parsed = urlsplit(self.path)
        body = None
        content_length = self.headers.get("Content-Length")
        if content_length:
            body = self.rfile.read(int(content_length))

        connection = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=30)
        try:
            headers = {key: value for key, value in self.headers.items() if key.lower() != "host"}
            connection.request(
                self.command,
                self.path,
                body=body,
                headers=headers,
            )
            response = connection.getresponse()
            response_body = response.read()

            self.send_response(response.status, response.reason)
            excluded_headers = {"transfer-encoding", "connection", "content-encoding"}
            for key, value in response.getheaders():
                if key.lower() not in excluded_headers:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response_body)
        finally:
            connection.close()


def main() -> None:
    if not DIST_DIR.exists():
        raise SystemExit(
            f"No se encontro el build del frontend en {DIST_DIR}. Ejecuta 'npm run build' primero."
        )

    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), FrontendProxyHandler)
    print(f"Frontend sirviendo en http://{LISTEN_HOST}:{LISTEN_PORT}")
    print(f"Proxy API hacia http://{BACKEND_HOST}:{BACKEND_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
