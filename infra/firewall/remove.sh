#!/usr/bin/env bash
set -euo pipefail

BRIDGES=(br-sra-red br-sra-blue br-sra-model br-sra-audit br-sra-referee)

del()    { sudo iptables -D DOCKER-USER "$@" 2>/dev/null || true; }
del_in() { sudo iptables -D INPUT "$@" 2>/dev/null || true; }

for b in "${BRIDGES[@]}"; do
  del -i "$b" ! -o "$b" -j DROP
  del -o "$b" ! -i "$b" -j DROP
  del_in -i "$b" -j DROP
done
