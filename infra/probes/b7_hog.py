import multiprocessing
import sys
import time


def burn_cpu(duration: float):
    end_time = time.time() + duration
    while time.time() < end_time:
        _ = 999999 * 999999


def main():
    duration = 20.0
    print(f"Starting resource hog for {duration} seconds...", file=sys.stderr)

    # 1. Memory allocation attempt up to limit
    chunks = []
    try:
        for _ in range(20):  # Try allocating 20 * 50MB = 1GB
            chunks.append(bytearray(50 * 1024 * 1024))
    except (MemoryError, OSError):
        print("Memory allocation capped by cgroup limits", file=sys.stderr)

    # 2. CPU burn
    procs = []
    for _ in range(multiprocessing.cpu_count()):
        p = multiprocessing.Process(target=burn_cpu, args=(duration,))
        p.start()
        procs.append(p)

    for p in procs:
        p.join()

    print("Hog completed.", file=sys.stderr)


if __name__ == "__main__":
    main()
