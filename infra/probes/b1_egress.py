import os
import socket
import threading

import common

EGRESS_TARGET = os.environ.get("EGRESS_TARGET", "1.1.1.1:443")


def check_tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (OSError, TimeoutError):
        return False


def check_dns(domain: str = "example.com", timeout: float = 3.0) -> bool:
    result = [False]

    def _lookup():
        try:
            socket.gethostbyname(domain)
            result[0] = True
        except OSError:
            pass

    t = threading.Thread(target=_lookup)
    t.daemon = True
    t.start()
    t.join(timeout)
    return result[0]


def main():
    parts = EGRESS_TARGET.split(":")
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 80

    tcp_ok = check_tcp(host, port)
    dns_ok = check_dns("example.com")

    if tcp_ok:
        common.emit("B1", "LEAK", f"Egress TCP connected directly to {EGRESS_TARGET}")
    elif dns_ok:
        common.emit("B1", "LEAK", "Egress DNS lookup succeeded for example.com")
    else:
        common.emit(
            "B1",
            "HELD",
            f"Egress blocked: TCP to {EGRESS_TARGET} refused/timed out and DNS failed",
        )


if __name__ == "__main__":
    main()
