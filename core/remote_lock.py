"""
core/remote_lock.py — Uzaktan kilitleme için HTTP Sunucusu
Telefonla bilgisayarı anında kilitlemek için token korumalı web paneli.
"""
import threading
import json
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket
from PyQt6.QtCore import pyqtSignal, QObject


class RemoteLockSignals(QObject):
    lock_requested = pyqtSignal()


class LockRequestHandler(BaseHTTPRequestHandler):
    def _check_token(self) -> bool:
        query = urlparse(self.path).query
        params = parse_qs(query)
        token = params.get("token", [""])[0]
        return token == self.server.auth_token

    def do_GET(self):
        if not self._check_token():
            self.send_error(403, "Forbidden: Invalid or missing token")
            return

        if self.path.startswith('/'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
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
                </style>
            </head>
            <body>
                <h1>🛡️ AppGuard</h1>
                <button onclick="lock()">KİLİTLE</button>
                <script>
                    function lock() {{
                        fetch('/lock?token={self.server.auth_token}', {{method: 'POST'}})
                        .then(r => {{
                            if(r.ok) alert('Sistem başarıyla kilitlendi!');
                            else alert('Yetkisiz işlem!');
                        }})
                        .catch(() => alert('Hata oluştu!'));
                    }}
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith('/lock'):
            if not self._check_token():
                self.send_error(403, "Forbidden")
                return

            self.server.signals.lock_requested.emit()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # Konsol kirliliğini önle


class RemoteLockServer(threading.Thread):
    def __init__(self, auth_token: str, port=8080):
        super().__init__(daemon=True, name="RemoteLockServer")
        self.port = port
        self.server = None
        self.signals = RemoteLockSignals()
        self.auth_token = auth_token

    def run(self):
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), LockRequestHandler)
            self.server.signals = self.signals
            self.server.auth_token = self.auth_token
            self.server.serve_forever()
        except Exception as e:
            print(f"RemoteLockServer Hatası: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def generate_qr_code(ip: str, port: int, token: str, save_path: str):
    try:
        import qrcode
        url = f"http://{ip}:{port}/?token={token}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(save_path)
    except Exception as e:
        print(f"QR kodu üretilemedi: {e}")
