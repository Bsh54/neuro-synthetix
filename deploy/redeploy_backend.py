"""Re-déploie SEULEMENT le backend (upload code+frontend, rebuild, restart).
Ne touche pas à Neo4j ni au tunnel. Neo4j garde ses données.

Usage:  python deploy/redeploy_backend.py <SSH_PW> <NEO4J_PW>
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

    def run(cmd: str, t: int = 180) -> str:
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

    print("== upload backend + frontend ==")
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
            print("  ", posixpath.join(rdir, f))
    sftp.close()

    # lire les cles supplementaires du .env local (Sarvam, traduction)
    extra_env = ""
    env_path = os.path.join(LOCAL, ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            line = line.strip()
            if line.startswith(("SARVAM_API_KEY=", "TRANSLATE_API_URL=", "TRANSLATE_API_KEY=", "DEEPSEEK_API_KEY=")):
                k, v = line.split("=", 1)
                extra_env += f" -e {k}='{v}'"

    print("== rebuild + restart ==")
    run(f"cd {REMOTE} && docker build -t neuro-backend . 2>&1 | tail -3")
    run("docker rm -f neuro-backend 2>/dev/null; echo removed")
    run(
        "docker run -d --name neuro-backend --network neuro-net --restart unless-stopped "
        "-p 0.0.0.0:8100:8000 -e NEO4J_URI=bolt://neuro-neo4j:7687 "
        f"-e NEO4J_USER=neo4j -e NEO4J_PASSWORD={NEO4J_PW}{extra_env} neuro-backend"
    )
    time.sleep(4)
    run("curl -s -m 10 -o /dev/null -w 'interne / -> HTTP %{http_code}\\n' http://127.0.0.1:8100/")
    c.close()
    print("\nOK. Teste : https://neuro.shadrakbessanh.me")


if __name__ == "__main__":
    main()
