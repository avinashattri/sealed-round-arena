#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BRIDGES=(br-sra-red br-sra-blue br-sra-model br-sra-audit br-sra-referee)

add()    { sudo iptables -C DOCKER-USER "$@" 2>/dev/null || sudo iptables -I DOCKER-USER "$@"; }
add_in() { sudo iptables -C INPUT "$@" 2>/dev/null || sudo iptables -I INPUT "$@"; }

for b in "${BRIDGES[@]}"; do
  add -i "$b" ! -o "$b" -j DROP
  add -o "$b" ! -i "$b" -j DROP
  add_in -i "$b" -j DROP
done

mkdir -p "$REPO_ROOT/evidence"
cat /proc/sys/kernel/random/boot_id > "$REPO_ROOT/evidence/.fw_boot_id"
echo "Firewall rules applied. Evidence boot ID recorded."
sudo iptables -S DOCKER-USER
