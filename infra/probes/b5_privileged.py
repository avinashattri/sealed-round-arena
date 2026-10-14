import ctypes
import os
import socket

import common


def test_raw_socket() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        s.close()
        return True
    except (PermissionError, OSError):
        return False


def test_rootfs_write() -> bool:
    target = "/probe_write_test"
    try:
        with open(target, "w") as f:
            f.write("test")
        try:
            os.remove(target)
        except OSError:
            pass
        return True
    except (PermissionError, OSError):
        return False


def test_mount() -> bool:
    try:
        libc = ctypes.CDLL("libc.so.6")
        # mount("none", "/mnt", "tmpfs", 0, None)
        ret = libc.mount(b"none", b"/mnt", b"tmpfs", 0, None)
        return ret == 0
    except (AttributeError, OSError):
        return False


def main():
    if test_raw_socket():
        common.emit("B5", "LEAK", "Raw socket created (CAP_NET_RAW not dropped)")
    elif test_rootfs_write():
        common.emit("B5", "LEAK", "Wrote to root filesystem (read_only false)")
    elif test_mount():
        common.emit("B5", "LEAK", "Mounted filesystem (CAP_SYS_ADMIN not dropped)")
    else:
        common.emit(
            "B5",
            "HELD",
            "Raw socket, rootfs write, and mount operations strictly blocked",
        )


if __name__ == "__main__":
    main()
