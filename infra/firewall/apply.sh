#!/usr/bin/env bash
set -euo pipefail

BRIDGES=(br-sra-red br-sra-blue br-sra-model br-sra-audit br-sra-referee)

add()    { sudo iptables -C DOCKER-USER "$@" 2>/dev/null || sudo iptables -I DOCKER-USER "$@"; }
add_in() { sudo iptables -C INPUT "$@" 2>/dev/null || sudo iptables -I INPUT "$@"; }

for b in "${BRIDGES[@]}"; do
  add -i "$b" ! -o "$b" -j DROP     # Drop egress traffic leaving arena networks
  add -o "$b" ! -i "$b" -j DROP     # Drop ingress traffic from external zones
  add_in -i "$b" -j DROP            # Block container access to host services
done

sudo iptables -S DOCKER-USER
