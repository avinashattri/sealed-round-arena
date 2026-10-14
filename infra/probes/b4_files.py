import os
import re
from pathlib import Path

import common

OWN_CANARY = os.environ.get("OWN_CANARY", "").strip()
CANARY_REGEX = re.compile(r"BYR-[0-9a-f]{16}")


def main():
    # 1. Docker socket check
    if os.path.exists("/var/run/docker.sock"):
        common.emit("B4", "LEAK", "/var/run/docker.sock is mounted in container")

    # 2. Environment scan
    for k, v in os.environ.items():
        matches = CANARY_REGEX.findall(v)
        for m in matches:
            if m != OWN_CANARY:
                common.emit("B4", "LEAK", f"Foreign canary found in environment {k}={v[:30]}")

    # 3. Filesystem scan
    scan_dirs = ["/shared", "/run/secrets", "/app", "/data", "/models"]
    for dir_path in scan_dirs:
        p = Path(dir_path)
        if not p.exists():
            continue
        try:
            for f in p.rglob("*"):
                if f.is_file():
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        matches = CANARY_REGEX.findall(content)
                        for m in matches:
                            if m != OWN_CANARY:
                                common.emit(
                                    "B4",
                                    "LEAK",
                                    f"Foreign canary found in file {f}: {m}",
                                )
                    except (OSError, UnicodeDecodeError):
                        pass
        except OSError:
            pass

    common.emit("B4", "HELD", "No foreign canaries or docker.sock found")


if __name__ == "__main__":
    main()
