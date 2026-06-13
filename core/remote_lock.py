"""
core/remote_lock.py — HTTP Server for remote locking
Token-protected web panel to instantly lock PC from phone.

Security note: This server uses plain HTTP (no TLS). The auth token is
transmitted in the URL query string. This is safe ONLY on trusted local
networks (e.g., home Wi-Fi). Never expose the server port to the public
internet via port forwarding without adding TLS.
"""
import logging
import secrets
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket

from PyQt6.QtCore import pyqtSignal, QObject, Qt

log = logging.getLogger(__name__)


class RemoteLockSignals(QObject):
    lock_requested = pyqtSignal()
    server_error   = pyqtSignal(str)  # emitted when server fails to start


class LockRequestHandler(BaseHTTPRequestHandler):
    def _check_token(self) -> bool:
        query  = urlparse(self.path).query
        params = parse_qs(query)
        token  = params.get("token", [""])[0]
        # Constant-time comparison prevents timing-based token guessing.
        return secrets.compare_digest(token, self.server.auth_token)

    def do_GET(self):
        if not self._check_token():
            self.send_error(403, "Forbidden: Invalid or missing token")
            return

        # Serve lock panel only for the root path; reject anything else.
        parsed_path = urlparse(self.path).path
        if parsed_path != "/":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AppGuard Remote</title>
            <style>
                body {{ font-family: sans-serif; background: #0f0f23; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                button {{ background: #e11d48; color: white; border: none; border-radius: 50%; width: 200px; height: 200px; font-size: 24px; font-weight: bold; cursor: pointer; box-shadow: 0 0 20px rgba(225, 29, 72, 0.5); transition: 0.2s; }}
                button:active {{ transform: scale(0.95); background: #be123c; }}
                h1 {{ margin-bottom: 40px; color: #94a3b8; }}
                p.notice {{ font-size: 11px; color: #475569; margin-top: 24px; max-width: 260px; text-align: center; }}
            </style>
        </head>
        <body>
            <h1>&#x1F6E1;&#xFE0F; AppGuard</h1>
            <button onclick="lock()">LOCK</button>
            <p class="notice">&#x26A0;&#xFE0F; Plain HTTP &mdash; use on trusted networks only.</p>
            <script>
                function lock() {{
                    fetch('/lock?token={self.server.auth_token}', {{method: 'POST'}})
                    .then(r => {{
                        if(r.ok) alert('System locked successfully!');
                        else alert('Unauthorized action!');
                    }})
                    .catch(() => alert('Error occurred!'));
                }}
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        parsed_path = urlparse(self.path).path
        if parsed_path == "/lock":
            if not self._check_token():
                self.send_error(403, "Forbidden")
                return
            # Emit via a queued connection so the slot always runs on the Qt
            # main thread, not this background HTTP thread.
            self.server.signals.lock_requested.emit()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # Prevent console clutter


class RemoteLockServer(threading.Thread):
    def __init__(self, auth_token: str, port: int = 8080):
        super().__init__(daemon=True, name="RemoteLockServer")
        self.port = port
        self.server = None
        self.signals = RemoteLockSignals()
        self.auth_token = auth_token

    def run(self) -> None:
        try:
            # Bind to all interfaces so the phone can reach us over Wi-Fi.
            # See module docstring for security considerations.
            self.server = HTTPServer(("0.0.0.0", self.port), LockRequestHandler)
            self.server.signals    = self.signals
            self.server.auth_token = self.auth_token
            self.server.serve_forever()
        except OSError as e:
            msg = f"Remote lock server could not bind to port {self.port}: {e}"
            log.error(msg)
            # Signal the UI so the user knows remote lock is not active.
            self.signals.server_error.emit(msg)
        except Exception as e:
            log.error("RemoteLockServer error: %s", e, exc_info=True)
            self.signals.server_error.emit(str(e))

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_qr_code(ip: str, port: int, token: str, save_path: str) -> bool:
    """Generate and save a QR code for the remote lock URL. Returns True on success."""
    try:
        import qrcode  # type: ignore[import]
        url = f"http://{ip}:{port}/?token={token}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(save_path)
        return True
    except Exception as e:
        log.error("QR code could not be generated: %s", e, exc_info=True)
        return False
