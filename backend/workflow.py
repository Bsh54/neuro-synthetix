"""Render Workflow — pipeline de donnees durable de Neuro-Synthetix.

Ce service tourne sur Render (pas sur le VPS). Il reconstruit la base de
connaissances a partir des registres publics (ClinicalTrials.gov, CTIS, ISRCTN),
la livre au serveur de prod (VPS) et declenche un rechargement des caches.

C'est un job planifie (toutes les 12h) : le cold start de Render est sans impact,
car ce n'est pas un serveur web mais un batch qui se reveille, travaille, s'eteint.

Variables d'environnement attendues (dans le dashboard Render) :
  SSH_HOST, SSH_USER, SSH_PW          -> livraison SFTP vers le VPS
  RELOAD_URL                          -> ex. https://neuro.shadrakbessanh.me/reload
  RELOAD_TOKEN                        -> doit correspondre a RELOAD_TOKEN du backend
  REMOTE_KB_PATH                      -> chemin cible sur le VPS (volume monte)

Entree : `python workflow.py`  (appelle app.start()).
"""
from __future__ import annotations

import json
import os
import tempfile

import httpx

try:
    from render_sdk import Workflows, Retry
except Exception:  # permet le lint/local sans le SDK
    Workflows = None
    Retry = None

from app import kb_builder

CONTAINER = os.environ.get("BACKEND_CONTAINER", "neuro-backend")
IN_CONTAINER_KB = "/app/app/data/knowledge_base.json"


def _deliver(local_path: str) -> str:
    """Livre la base au VPS : SFTP -> docker cp dans le conteneur -> /reload.
    N'exige aucun changement d'infra sur la prod. Best-effort."""
    host = os.environ.get("SSH_HOST")
    user = os.environ.get("SSH_USER", "root")
    pw = os.environ.get("SSH_PW")
    if not host or not pw:
        return "no VPS credentials, build only"
    import paramiko
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, 22, user, pw, timeout=25)
    remote_tmp = "/tmp/ns_kb_new.json"
    sftp = c.open_sftp()
    sftp.put(local_path, remote_tmp)
    sftp.close()
    # copier dans le conteneur en cours d'execution
    i, o, e = c.exec_command(f"docker cp {remote_tmp} {CONTAINER}:{IN_CONTAINER_KB}")
    o.read()
    e.read()
    c.close()
    # recharger les caches du backend
    url = os.environ.get("RELOAD_URL")
    if url:
        try:
            httpx.post(url, params={"token": os.environ.get("RELOAD_TOKEN", "")}, timeout=30)
        except Exception:
            pass
    return "delivered via docker cp + reload"


if Workflows is not None:
    app = Workflows()

    @app.task(
        name="refresh_knowledge_base",
        timeout_seconds=1200,
        retry=Retry(max_retries=2, wait_duration_ms=5000, backoff_scaling=2.0),
    )
    def refresh_knowledge_base() -> dict:
        """Reconstruit la base (multi-sources) et la livre a la prod."""
        kb = kb_builder.build()  # ClinicalTrials.gov + CTIS + ISRCTN (+ Inde)
        tmp = os.path.join(tempfile.gettempdir(), "knowledge_base.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(kb, f, ensure_ascii=False)
        status = _deliver(tmp)
        return {
            "trial_count": kb.get("trial_count"),
            "sources": kb.get("sources"),
            "delivery": status,
        }

    app.start()
