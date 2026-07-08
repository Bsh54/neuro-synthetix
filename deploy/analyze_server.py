"""Analyse du serveur via SSH (paramiko). Identifiants passés en argv/env."""
from __future__ import annotations

import sys
import paramiko

HOST = "213.156.135.72"
PORT = 22
USER = "root"
import os
PW = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SSH_PW", "")

CMD = r'''
echo "=== OS ==="; cat /etc/os-release 2>/dev/null | grep -E "^(PRETTY_NAME|VERSION_ID)="; uname -r
echo "=== CPU ==="; nproc; grep -m1 "model name" /proc/cpuinfo | cut -d: -f2
echo "=== RAM ==="; free -h | head -2
echo "=== DISK ==="; df -h / | tail -1
echo "=== TOOLS ==="
for t in docker docker-compose python3 pip3 node npm git nginx neo4j java curl; do
  printf "%-14s" "$t:"
  if command -v $t >/dev/null 2>&1; then $t --version 2>/dev/null | head -1; else echo ABSENT; fi
done
echo "=== DOCKER PS ==="; docker ps 2>/dev/null || echo "docker off/absent"
echo "=== PORTS ==="; (ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | head -20
echo DONE
'''


def main() -> None:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PW, timeout=20)
    stdin, stdout, stderr = client.exec_command(CMD, timeout=60)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out)
    if err.strip():
        print("--- STDERR ---")
        print(err)
    client.close()


if __name__ == "__main__":
    main()
