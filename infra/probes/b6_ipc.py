from pathlib import Path

import common


def main():
    # 1. Check PID visibility: count /proc/[0-9]*
    proc_pids = [p for p in Path("/proc").iterdir() if p.name.isdigit()]
    pid_count = len(proc_pids)

    # 2. Check /dev/shm
    shm_files = list(Path("/dev/shm").iterdir()) if Path("/dev/shm").exists() else []

    if pid_count > 10:
        common.emit(
            "B6",
            "LEAK",
            f"Process visibility leak: {pid_count} processes visible (>10 threshold)",
        )
    elif len(shm_files) > 0:
        common.emit(
            "B6",
            "LEAK",
            f"IPC visibility leak: foreign files present in /dev/shm: {[f.name for f in shm_files]}",
        )
    else:
        common.emit(
            "B6",
            "HELD",
            f"PID and IPC isolation verified ({pid_count} processes, /dev/shm clean)",
        )


if __name__ == "__main__":
    main()
