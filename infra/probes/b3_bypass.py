import os
import socket

import common

CONTROL = os.environ.get("CONTROL", "broker:8000")
TARGETS = os.environ.get("TARGETS", "blue:9000,model:8080,audit:7000,oracle:7100")


def check_tcp(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (OSError, TimeoutError):
        return False


def main():
    # 1. Positive control
    c_parts = CONTROL.split(":")
    c_host, c_port = c_parts[0], int(c_parts[1])
    if not check_tcp(c_host, c_port):
        common.emit("B3", "ERROR", f"control unreachable: {CONTROL} probe invalid")

    # 2. Check targets
    target_list = [t.strip() for t in TARGETS.split(",") if t.strip()]
    for target in target_list:
        t_parts = target.split(":")
        t_host, t_port = t_parts[0], int(t_parts[1])

        # Test by name
        if check_tcp(t_host, t_port):
            common.emit("B3", "LEAK", f"Bypassed broker: reached {target} directly by name")

        # Test by IP if name resolves
        try:
            ip = socket.gethostbyname(t_host)
            if ip != t_host and check_tcp(ip, t_port):
                common.emit("B3", "LEAK", f"Bypassed broker: reached {target} directly by IP {ip}")
        except OSError:
            pass

    common.emit("B3", "HELD", "Direct connections to all zone targets blocked")


if __name__ == "__main__":
    main()
