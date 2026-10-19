"""Background UDP receiver. Never touches Tk; results go through a queue."""
import queue
import socket
import sys
import threading
import time

from protocol import parse_message


class PortInUseError(OSError):
    pass


def open_socket(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if sys.platform == 'win32' and hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
        # Without this, Windows may let a second program share the port silently.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        sock.bind((host, port))
    except OSError as exc:
        sock.close()
        if getattr(exc, 'winerror', None) in (10048, 10013) or exc.errno in (98, 48, 10048):
            raise PortInUseError(
                f'UDP {host}:{port} is already in use (another slide_demo window?). '
                f'Close it or start with --port N, and send with the same --port.') from exc
        raise
    sock.settimeout(0.2)
    return sock


class UdpListener:
    """Puts ('msg', Message, raw, recv_time) or ('invalid', raw, recv_time) on `out`."""

    def __init__(self, host='127.0.0.1', port=5005, out=None):
        self.sock = open_socket(host, port)
        self.address = self.sock.getsockname()
        self.out = out if out is not None else queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name='udp-listener', daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _run(self):
        while not self._stop.is_set():
            try:
                data, _ = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                # Windows reports ICMP "port unreachable" from earlier sends as
                # ConnectionResetError on UDP; also raised after close().
                if self._stop.is_set():
                    break
                continue
            now = time.monotonic()
            msg = parse_message(data)
            if msg is None:
                self.out.put(('invalid', data[:80], now))
            else:
                self.out.put(('msg', msg, data[:80], now))

    def close(self):
        self._stop.set()
        try:
            self.sock.close()
        finally:
            if self._thread.is_alive():
                self._thread.join(timeout=1.0)
