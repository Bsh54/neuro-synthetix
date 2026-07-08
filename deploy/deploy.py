"""Déploiement Neuro-Synthetix sur le serveur via paramiko + Docker.

- Upload du backend (SFTP)
- Neo4j en conteneur (bind 127.0.0.1, non exposé publiquement)
- Backend FastAPI en conteneur (exposé sur :8100)
- Peuplement du graphe (seed)

Reste isolé : réseau Docker dédié, ne touche pas au mail/DNS de l'hôte.

Usage: python deploy/deploy.py <SSH_PASSWORD> <NEO4J_PASSWORD>
"""
from __future__ import annotations

import os
import sys
import time
import posixpath

import paramiko

HOST = "213.156.135.72"
PORT = 22
USER = "root"

SSH_PW = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SSH_PW", "")
NEO4J_PW = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("NEO4J_PW", "changeme")

REMOTE_ROOT = "/root/neuro-synthetix"
LOCAL_BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")

NET = "neuro-net"
NEO4J_NAME = "neuro-neo4j"
BACKEND_NAME = "neuro-backend"
BACKEND_PORT = 8100


def sh(client: paramiko.SSHClient, cmd: str, quiet: bool = False) -> str:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if not quiet:
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print("  [stderr]", err.rstrip())
    return out


def upload_backend(client: paramiko.SSHClient) -> None:
    sftp = client.open_sftp()

    def mkdir_p(path: str) -> None:
        parts = path.strip("/").split("/")
        cur = ""
        for p in parts:
            cur += "/" + p
            try:
                sftp.stat(cur)
            except IOError:
                sftp.mkdir(cur)

    for root, _dirs, files in os.walk(LOCAL_BACKEND):
        if "__pycache__" in root or ".venv" in root:
            continue
        rel = os.path.relpath(root, LOCAL_BACKEND).replace("\\", "/")
        remote_dir = posixpath.normpath(posixpath.join(REMOTE_ROOT, "backend", rel))
        mkdir_p(remote_dir)
        for f in files:
            if f.endswith(".pyc") or f == ".env":
                continue
            lp = os.path.join(root, f)
            rp = posixpath.join(remote_dir, f)
            sftp.put(lp, rp)
            print("  upload", rp)
    sftp.close()


def main() -> None:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=SSH_PW, timeout=20)

    print("== 1. Upload backend ==")
    upload_backend(client)

    print("== 2. Réseau Docker ==")
    sh(client, f"docker network create {NET} 2>/dev/null || echo 'réseau déjà présent'")

    print("== 3. Neo4j (conteneur, bind localhost) ==")
    sh(client, f"docker rm -f {NEO4J_NAME} 2>/dev/null || true")
    sh(client, (
        f"docker run -d --name {NEO4J_NAME} --network {NET} --restart unless-stopped "
        f"-p 127.0.0.1:7474:7474 -p 127.0.0.1:7687:7687 "
        f"-e NEO4J_AUTH=neo4j/{NEO4J_PW} "
        f"-e NEO4J_server_memory_heap_max__size=1G "
        f"-v neuro_neo4j_data:/data neo4j:5"
    ))

    print("== 4. Attente Neo4j prêt ==")
    for i in range(30):
        out = sh(client, (
            f"docker exec {NEO4J_NAME} cypher-shell -u neo4j -p {NEO4J_PW} "
            f"'RETURN 1' 2>/dev/null && echo READY || echo WAIT"
        ), quiet=True)
        if "READY" in out:
            print("  Neo4j prêt.")
            break
        time.sleep(5)
    else:
        print("  ⚠️ Neo4j n'a pas répondu à temps (voir logs).")

    print("== 5. Build backend ==")
    sh(client, f"cd {REMOTE_ROOT}/backend && docker build -t {BACKEND_NAME} . 2>&1 | tail -5")

    print("== 6. Run backend ==")
    sh(client, f"docker rm -f {BACKEND_NAME} 2>/dev/null || true")
    sh(client, (
        f"docker run -d --name {BACKEND_NAME} --network {NET} --restart unless-stopped "
        f"-p 0.0.0.0:{BACKEND_PORT}:8000 "
        f"-e NEO4J_URI=bolt://{NEO4J_NAME}:7687 "
        f"-e NEO4J_USER=neo4j -e NEO4J_PASSWORD={NEO4J_PW} "
        f"{BACKEND_NAME}"
    ))

    print("== 7. Peuplement (seed) ==")
    time.sleep(4)
    sh(client, f"docker exec {BACKEND_NAME} python -m app.seed")

    print("== 8. Vérifications ==")
    sh(client, f"curl -s http://127.0.0.1:{BACKEND_PORT}/health")
    print()
    sh(client, (
        f"curl -s -X POST http://127.0.0.1:{BACKEND_PORT}/match "
        f"-H 'Content-Type: application/json' "
        f"-d '{{\"text\":\"j ai de la fievre et je tousse et perdu du poids\"}}'"
    ))
    print("\n== FIN ==")
    print(f"API publique : http://{HOST}:{BACKEND_PORT}/health")
    client.close()


if __name__ == "__main__":
    main()
