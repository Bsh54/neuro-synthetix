"""Crée un tunnel cloudflared DÉDIÉ pour Neuro-Synthetix.

N'affecte PAS les tunnels existants (shadrakbessanh.me, catalystmd) :
tunnel séparé, config séparée, process séparé.

Route : neuro.shadrakbessanh.me -> http://localhost:8100
"""
from __future__ import annotations

import os
import sys
import time
import paramiko

HOST, PORT, USER = "213.156.135.72", 22, "root"
PW = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SSH_PW", "")

TUNNEL = "neuro-synthetix"
HOSTNAME = "neuro.shadrakbessanh.me"
LOCAL_SVC = "http://localhost:8100"
CFG_DIR = "/root/neuro-cloudflared"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, PW, timeout=25, banner_timeout=25, auth_timeout=25)

    def run(cmd: str, t: int = 120) -> str:
        i, o, e = c.exec_command(cmd, timeout=t)
        out = o.read().decode(errors="replace") + e.read().decode(errors="replace")
        print(out.rstrip())
        return out

    print("== 0. Stop quick tunnel parasite ==")
    run("pkill -f 'tunnel --url http://localhost:8100' 2>/dev/null; echo done")

    print("== 1. Créer le tunnel dédié (idempotent) ==")
    run(f"mkdir -p {CFG_DIR}")
    existing = run(f"cloudflared tunnel list 2>/dev/null | grep -w {TUNNEL} || echo NONE")
    if "NONE" in existing:
        run(f"cloudflared tunnel create {TUNNEL}")
    else:
        print("  tunnel déjà existant, on réutilise.")

    # Récupérer l'UUID + chemin du fichier de credentials
    uuid = run(
        f"cloudflared tunnel list 2>/dev/null | awk '$2==\"{TUNNEL}\"{{print $1}}' | head -1"
    ).strip().splitlines()[-1].strip()
    print("  UUID:", uuid)

    print("== 2. Écrire la config dédiée ==")
    config = (
        f"tunnel: {TUNNEL}\n"
        f"credentials-file: /root/.cloudflared/{uuid}.json\n"
        f"ingress:\n"
        f"  - hostname: {HOSTNAME}\n"
        f"    service: {LOCAL_SVC}\n"
        f"  - service: http_status:404\n"
    )
    sftp = c.open_sftp()
    with sftp.open(f"{CFG_DIR}/config.yml", "w") as f:
        f.write(config)
    sftp.close()
    run(f"cat {CFG_DIR}/config.yml")

    print("== 3. Route DNS ==")
    run(f"cloudflared tunnel route dns {TUNNEL} {HOSTNAME} 2>&1 || echo 'route déjà existante'")

    print("== 4. Lancer le tunnel dédié en arrière-plan ==")
    run("pkill -f 'neuro-cloudflared/config.yml' 2>/dev/null; echo ok")
    run(
        f"nohup cloudflared tunnel --config {CFG_DIR}/config.yml --no-autoupdate "
        f"run {TUNNEL} > /var/log/cf-neuro-tunnel.log 2>&1 & echo started"
    )

    print("== 5. Attente connexion ==")
    for _ in range(12):
        time.sleep(5)
        log = run("tail -3 /var/log/cf-neuro-tunnel.log 2>/dev/null", t=30)
        if "Registered tunnel connection" in log or "Connection " in log:
            break

    print("== 6. Vérif interne ==")
    run("curl -s -m 10 http://127.0.0.1:8100/health; echo")
    c.close()
    print(f"\n== FIN ==\nPublic (après propagation DNS ~30s) : https://{HOSTNAME}/health")


if __name__ == "__main__":
    main()
