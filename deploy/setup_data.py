"""Recharge les donnees (24 conditions) dans Neo4j + installe la MAJ auto toutes les 12h.

- upload backend -> rebuild -> ingest (CT.gov, ~480 essais) -> rebuild KB
- ecrit /root/neuro-refresh.sh et l'ajoute au crontab (toutes les 12h)

Usage : python deploy/setup_data.py <SSH_PW> <NEO4J_PW>
"""
from __future__ import annotations

import os
import sys
import time
import posixpath

import paramiko

HOST, PORT, USER = "213.156.135.72", 22, "root"
SSH_PW = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SSH_PW", "")
NEO4J_PW = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("NEO4J_PW", "")
REMOTE = "/root/neuro-synthetix/backend"
LOCAL = os.path.join(os.path.dirname(__file__), "..", "backend")

REFRESH = """#!/bin/bash
# Neuro-Synthetix : rafraichit les donnees d'essais cliniques (auto, 12h)
set -e
LOG=/var/log/neuro-refresh.log
echo "[`date -u +%FT%TZ`] refresh start" >> $LOG
docker exec neuro-backend python -m app.ingest >> $LOG 2>&1 || echo "ingest failed" >> $LOG
docker exec neuro-backend python -m app.kb_builder >> $LOG 2>&1 || echo "kb failed" >> $LOG
echo "[`date -u +%FT%TZ`] refresh done" >> $LOG
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

    print("== upload backend ==")
    for root, _d, files in os.walk(LOCAL):
        if "__pycache__" in root or ".venv" in root:
            continue
        # ne pas re-uploader le gros knowledge_base.json (genere sur le serveur)
        rel = os.path.relpath(root, LOCAL).replace("\\", "/")
        rdir = posixpath.normpath(posixpath.join(REMOTE, rel))
        mkdir_p(rdir)
        for f in files:
            if f.endswith(".pyc") or f == ".env" or f == "knowledge_base.json":
                continue
            sftp.put(os.path.join(root, f), posixpath.join(rdir, f))

    # refresh script
    with sftp.open("/root/neuro-refresh.sh", "w") as f:
        f.write(REFRESH)
    sftp.close()
    run("chmod +x /root/neuro-refresh.sh")

    print("== rebuild + restart ==")
    run(f"cd {REMOTE} && docker build -t neuro-backend . 2>&1 | tail -2")
    run("docker rm -f neuro-backend 2>/dev/null; echo ok")
    run("docker run -d --name neuro-backend --network neuro-net --restart unless-stopped "
        "-p 0.0.0.0:8100:8000 -e NEO4J_URI=bolt://neuro-neo4j:7687 "
        f"-e NEO4J_USER=neo4j -e NEO4J_PASSWORD={NEO4J_PW} neuro-backend")
    time.sleep(4)

    print("== ingest (24 conditions, CT.gov) ==")
    run("docker exec neuro-backend python -m app.ingest", t=600)

    print("== knowledge base (multi-sources) ==")
    run("docker exec neuro-backend python -m app.kb_builder", t=600)

    print("== install cron 12h ==")
    # retire toute ancienne ligne neuro-refresh puis ajoute la nouvelle
    run("( crontab -l 2>/dev/null | grep -v neuro-refresh.sh ; echo '0 */12 * * * /root/neuro-refresh.sh' ) | crontab -")
    run("crontab -l | grep neuro-refresh")

    print("== verif count ==")
    run("docker exec neuro-neo4j cypher-shell -u neo4j -p " + NEO4J_PW +
        " 'MATCH (t:Trial) RETURN count(t) AS trials' 2>&1 | tail -3")
    c.close()
    print("\nOK")


if __name__ == "__main__":
    main()
