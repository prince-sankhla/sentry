from __future__ import annotations

import socket
import ssl
import time
from urllib.parse import urlparse

from . import fast_stream_robust as _base


class SocketMjpegReader:
    """DroidCam MJPEG reader that avoids urllib read-size blocking."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.parsed = urlparse(source)
        if self.parsed.scheme not in {"http", "https"} or not self.parsed.hostname:
            raise ValueError(f"Unsupported camera URL: {source}")
        self.sock: socket.socket | ssl.SSLSocket | None = None
        self.buffer = bytearray()
        self.closed = False
        self.opened_at = 0.0
        self.open()

    def open(self) -> bool:
        if self.closed:
            return False
        self.close_socket()
        try:
            port = self.parsed.port or (443 if self.parsed.scheme == "https" else 80)
            sock = socket.create_connection((self.parsed.hostname, port), timeout=5.0)
            if self.parsed.scheme == "https":
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=self.parsed.hostname)
            sock.settimeout(2.0)
            path = self.parsed.path or "/"
            if self.parsed.query:
                path += "?" + self.parsed.query
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {self.parsed.hostname}:{port}\r\n"
                "Accept: multipart/x-mixed-replace,image/jpeg,*/*\r\n"
                "Cache-Control: no-cache\r\n"
                "Pragma: no-cache\r\n"
                "Connection: keep-alive\r\n"
                "User-Agent: SENTRY-FIELD/1.0\r\n\r\n"
            ).encode("ascii", errors="ignore")
            sock.sendall(request)
            header = bytearray()
            while b"\r\n\r\n" not in header and len(header) < 65536:
                part = sock.recv(4096)
                if not part:
                    raise ConnectionError("Camera closed before HTTP headers")
                header.extend(part)
            marker = header.find(b"\r\n\r\n")
            if marker < 0:
                raise ConnectionError("Invalid camera HTTP headers")
            status_line = header.split(b"\r\n", 1)[0].decode("latin1", errors="replace")
            if " 200 " not in status_line:
                raise ConnectionError(status_line)
            content_type = header.decode("latin1", errors="replace").lower()
            if "multipart" not in content_type and "image/jpeg" not in content_type:
                raise ConnectionError("Camera did not return an MJPEG/JPEG stream")
            self.sock = sock
            self.sock.settimeout(0.5)
            self.buffer = bytearray(header[marker + 4 :])
            self.opened_at = time.monotonic()
            return True
        except Exception:
            self.close_socket()
            return False

    def close_socket(self) -> None:
        sock = self.sock
        self.sock = None
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    def read(self):
        import cv2
        import numpy as np

        while not self.closed:
            if self.sock is None and not self.open():
                time.sleep(0.15)
                continue

            while True:
                start = self.buffer.find(b"\xff\xd8")
                if start >= 0:
                    if start:
                        del self.buffer[:start]
                    end = self.buffer.find(b"\xff\xd9", 2)
                    if end >= 0:
                        payload = bytes(self.buffer[: end + 2])
                        del self.buffer[: end + 2]
                        frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            return True, frame
                if len(self.buffer) > 4_000_000:
                    del self.buffer[:-1_000_000]
                try:
                    chunk = self.sock.recv(65536) if self.sock is not None else b""
                except socket.timeout:
                    continue
                except OSError:
                    self.close_socket()
                    break
                if not chunk:
                    self.close_socket()
                    break
                self.buffer.extend(chunk)
        return False, None

    def close(self) -> None:
        self.closed = True
        self.close_socket()


# Patch the existing robust stream to use a non-blocking socket reader.
_base.MjpegReader = SocketMjpegReader
stream = _base.stream
