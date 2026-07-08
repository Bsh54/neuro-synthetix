"""Couche Neo4j : schéma, ingestion et matching des essais cliniques.

Modèle de graphe :
    (:Symptom)-[:INDICATES]->(:Condition)-[:STUDIED_BY]->(:Trial)-[:LOCATED_AT]->(:Hospital)

Le matching part des mots-clés (symptômes) fournis par le patient et remonte
jusqu'aux essais + hôpitaux, avec un score = nombre de symptômes correspondants.
"""
from __future__ import annotations

from functools import lru_cache

from neo4j import GraphDatabase, Driver

from .config import settings


@lru_cache(maxsize=1)
def get_driver() -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def close_driver() -> None:
    if get_driver.cache_info().currsize:
        get_driver().close()
        get_driver.cache_clear()


def init_constraints() -> None:
    """Crée les contraintes d'unicité (idempotent)."""
    stmts = [
        "CREATE CONSTRAINT symptom_name IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT condition_name IF NOT EXISTS FOR (c:Condition) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT trial_id IF NOT EXISTS FOR (t:Trial) REQUIRE t.nct_id IS UNIQUE",
        "CREATE CONSTRAINT hospital_name IF NOT EXISTS FOR (h:Hospital) REQUIRE h.name IS UNIQUE",
    ]
    with get_driver().session() as ses:
        for q in stmts:
            ses.run(q)


def ping() -> bool:
    """Retourne True si Neo4j répond."""
    try:
        with get_driver().session() as ses:
            ses.run("RETURN 1").single()
        return True
    except Exception:
        return False


# -- Matching ---------------------------------------------------------------

MATCH_QUERY = """
UNWIND $keywords AS kw
MATCH (s:Symptom)
WHERE toLower(s.name) CONTAINS toLower(kw)
MATCH (s)-[:INDICATES]->(c:Condition)-[:STUDIED_BY]->(t:Trial)
OPTIONAL MATCH (t)-[:LOCATED_AT]->(h:Hospital)
WITH t, c, collect(DISTINCT s.name) AS matched_symptoms,
     collect(DISTINCT {name: h.name, city: h.city, country: h.country, lat: h.lat, lon: h.lon, contact: h.contact}) AS hospitals
RETURN t.nct_id AS nct_id, t.title AS title, t.status AS status,
       c.name AS condition, matched_symptoms,
       size(matched_symptoms) AS score, hospitals
ORDER BY score DESC
LIMIT $limit
"""


def match_trials(keywords: list[str], limit: int = 5) -> list[dict]:
    """Retourne les essais correspondant aux mots-clés, triés par score."""
    if not keywords:
        return []
    with get_driver().session() as ses:
        rows = ses.run(MATCH_QUERY, keywords=keywords, limit=limit)
        return [r.data() for r in rows]


def build_graph_payload(trials: list[dict], patient_label: str = "Patient") -> dict:
    """Transforme les essais en {nodes, edges} pour la visualisation 'toile d'araignée'."""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(node_id: str, label: str, kind: str) -> None:
        nodes.setdefault(node_id, {"id": node_id, "label": label, "kind": kind})

    add_node("patient", patient_label, "patient")

    for t in trials:
        cond_id = f"condition:{t['condition']}"
        trial_id = f"trial:{t['nct_id']}"
        add_node(cond_id, t["condition"], "condition")
        add_node(trial_id, t.get("title") or t["nct_id"], "trial")

        for sym in t.get("matched_symptoms", []):
            sym_id = f"symptom:{sym}"
            add_node(sym_id, sym, "symptom")
            edges.append({"source": "patient", "target": sym_id, "label": "ressent"})
            edges.append({"source": sym_id, "target": cond_id, "label": "indique"})

        edges.append({"source": cond_id, "target": trial_id, "label": "étudié par"})

        for h in t.get("hospitals", []):
            if not h or not h.get("name"):
                continue
            hosp_id = f"hospital:{h['name']}"
            add_node(hosp_id, h["name"], "hospital")
            edges.append({"source": trial_id, "target": hosp_id, "label": "situé à"})

    return {"nodes": list(nodes.values()), "edges": edges}
