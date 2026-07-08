"""Charge les VRAIES données ClinicalTrials.gov dans Neo4j (à lancer par l'utilisateur).

Étapes : upload ingest.py -> rebuild image -> supprime UNIQUEMENT les noeuds
de démo (NCT0DEMO*) -> restart backend -> lance l'ingestion réelle.

Usage :  python deploy/load_real_data.py <SSH_PW> <NEO4J_PW>
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


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, SSH_PW, timeout=25, banner_timeout=25, auth_timeout=25)

    def run(cmd: str, t: int = 240) -> str:
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

    print("== upload backend (dont ingest.py) ==")
    for root, _d, files in os.walk(LOCAL):
        if "__pycache__" in root or ".venv" in root:
            continue
        rel = os.path.relpath(root, LOCAL).replace("\\", "/")
        rdir = posixpath.normpath(posixpath.join(REMOTE, rel))
        mkdir_p(rdir)
        for f in files:
            if f.endswith(".pyc") or f == ".env":
                continue
            sftp.put(os.path.join(root, f), posixpath.join(rdir, f))
    sftp.close()
    print("  ok")

    print("== rebuild ==")
    run(f"cd {REMOTE} && docker build -t neuro-backend . 2>&1 | tail -2")

    print("== suppression des noeuds de demo uniquement ==")
    run(
        f"docker exec neuro-neo4j cypher-shell -u neo4j -p {NEO4J_PW} "
        f"\"MATCH (t:Trial) WHERE t.nct_id STARTS WITH 'NCT0DEMO' DETACH DELETE t\" 2>&1 | tail -1"
    )

    print("== restart backend ==")
    run("docker rm -f neuro-backend 2>/dev/null; echo ok")
    run(
        "docker run -d --name neuro-backend --network neuro-net --restart unless-stopped "
        "-p 0.0.0.0:8100:8000 -e NEO4J_URI=bolt://neuro-neo4j:7687 "
        f"-e NEO4J_USER=neo4j -e NEO4J_PASSWORD={NEO4J_PW} neuro-backend"
    )
    time.sleep(4)

    print("== INGESTION REELLE (ClinicalTrials.gov) ==")
    run("docker exec neuro-backend python -m app.ingest", t=300)

    print("\n== verif ==")
    run("curl -s -m 15 -X POST http://127.0.0.1:8100/match -H 'Content-Type: application/json' "
        "-d '{\"text\":\"fever cough weight loss\"}' | head -c 500")
    c.close()
    print("\n\nOK -> https://neuro.shadrakbessanh.me")


if __name__ == "__main__":
    main()
