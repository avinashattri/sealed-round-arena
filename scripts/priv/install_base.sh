#!/usr/bin/env bash
set -euo pipefail
sudo apt update && sudo apt install -y git make curl ca-certificates gnupg jq sqlite3 python3 python3-venv python3-pip build-essential libffi-dev libssl-dev iptables netcat-openbsd dnsutils iputils-ping
