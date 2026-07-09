"""Heberge l'app Expo sur le VPS via un tunnel (ouvre dans Expo Go).

Etapes :
1. upload du projet mobile (sans node_modules)
2. npm install sur le VPS (+ @expo/ngrok pour le tunnel)
3. service systemd `neuro-expo` qui lance `expo start --tunnel` avec relance auto
4. recupere l'URL exp:// depuis les logs

Usage : python deploy/mobile_tunnel.py <SSH_PW> <EXPO_TOKEN>
Le lien est fragile (dev server) : tant que le service tourne, il est stable.
"""
from __future__ import annotations

import os
import sys
import time
import posixpath

import paramiko

HOST, PORT, USER = "213.156.135.72", 22, "root"
SSH_PW = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SSH_PW", "")
EXPO_TOKEN = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("EXPO_TOKEN", "")
REMOTE = "/root/neuro-synthetix/mobile"
LOCAL = os.path.join(os.path.dirname(__file__), "..", "mobile")

SERVICE = """[Unit]
Description=Neuro-Synthetix Expo tunnel
After=network.target

[Service]
WorkingDirectory=/root/neuro-synthetix/mobile
Environment=EXPO_TOKEN={token}
Environment=CI=1
Environment=EXPO_NO_TELEMETRY=1
ExecStart=/usr/bin/env npx expo start --tunnel --non-interactive
Restart=always
RestartSec=10
StandardOutput=append:/var/log/neuro-expo.log
StandardError=append:/var/log/neuro-expo.log

[Install]
WantedBy=multi-user.target
"""


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, SSH_PW, timeout=25, banner_timeout=25, auth_timeout=25)

    def run(cmd: str, t: int = 400) -> str:
        i, o, e = c.exec_command(cmd, timeout=t)
        out = o.read().decode(errors="replace") + e.read().decode(errors="replace")
        print(out.rstrip())
        return out

    sftp = c.open_sftp()

    def mkdir_p(p: str) -> None:
        cur = ""
        for part in p.strip("/").split("/"):
            cur += "/" + part
            try:
                sftp.stat(cur)
            except IOError:
                sftp.mkdir(cur)

    print("== 1. upload mobile ==")
    mkdir_p(REMOTE)
    for f in os.listdir(LOCAL):
        if f in ("node_modules", ".expo"):
            continue
        lp = os.path.join(LOCAL, f)
        if os.path.isfile(lp):
            sftp.put(lp, posixpath.join(REMOTE, f))
            print("  ", f)
    sftp.close()

    print("== 2. npm install (peut prendre 1-2 min) ==")
    run(f"cd {REMOTE} && npm install 2>&1 | tail -3", t=600)
    run(f"cd {REMOTE} && npm install @expo/ngrok@^4.1.0 2>&1 | tail -3", t=600)

    print("== 3. service systemd (relance auto) ==")
    with c.open_sftp() as s2, s2.open("/etc/systemd/system/neuro-expo.service", "w") as f:
        f.write(SERVICE.format(token=EXPO_TOKEN))
    run("systemctl daemon-reload && systemctl enable neuro-expo && systemctl restart neuro-expo")

    print("== 4. attente du lien tunnel (jusqu'a 90s) ==")
    url = None
    for _ in range(18):
        time.sleep(5)
        out = run("grep -oE 'exp://[a-zA-Z0-9._-]+' /var/log/neuro-expo.log 2>/dev/null | tail -1", t=30)
        m = out.strip().splitlines()
        if m and m[-1].startswith("exp://"):
            url = m[-1].strip()
            break
    print("\n==============================")
    print("LIEN EXPO GO :", url or "(pas encore visible, voir /var/log/neuro-expo.log)")
    print("==============================")
    c.close()


if __name__ == "__main__":
    main()
