import socket

import common

METADATA_IP = "169.254.169.254"
METADATA_PORT = 80


def main():
    try:
        s = socket.create_connection((METADATA_IP, METADATA_PORT), timeout=2.0)
        s.close()
        common.emit(
            "B2",
            "LEAK",
            "SIMULATION: connected directly to metadata IP 169.254.169.254:80",
        )
    except (OSError, TimeoutError):
        common.emit(
            "B2",
            "HELD",
            "SIMULATION: no route/connect to link-local metadata IP 169.254.169.254:80",
        )


if __name__ == "__main__":
    main()
