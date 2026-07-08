"""Peuple Neo4j avec un jeu de démo minimal (Tuberculose, Delhi).

Usage :  python -m app.seed
Les données sont volontairement petites et vérifiables pour la démo.
On remplacera/complétera par un import ClinicalTrials.gov (ingest.py) ensuite.
"""
from __future__ import annotations

from . import graph

SEED = {
    "conditions": [
        {
            "name": "Tuberculosis",
            "symptoms": ["fever", "cough", "weight loss", "night sweats", "bone pain"],
            "trials": [
                {
                    "nct_id": "NCT0DEMO001",
                    "title": "Nouveau traitement court de la tuberculose pulmonaire",
                    "status": "Recruiting",
                    "hospital": {
                        "name": "AIIMS Delhi",
                        "city": "New Delhi",
                        "lat": 28.5672,
                        "lon": 77.2100,
                        "contact": "Dr. Sharma - trials@aiims.example",
                    },
                }
            ],
        },
        {
            "name": "Migraine",
            "symptoms": ["headache", "dizziness", "fatigue"],
            "trials": [
                {
                    "nct_id": "NCT0DEMO002",
                    "title": "Essai sur la prévention de la migraine chronique",
                    "status": "Recruiting",
                    "hospital": {
                        "name": "Apollo Hospital Delhi",
                        "city": "New Delhi",
                        "lat": 28.5410,
                        "lon": 77.2830,
                        "contact": "Dr. Rao - neuro@apollo.example",
                    },
                }
            ],
        },
    ]
}

UPSERT = """
MERGE (c:Condition {name: $condition})
WITH c
UNWIND $symptoms AS sym
  MERGE (s:Symptom {name: sym})
  MERGE (s)-[:INDICATES]->(c)
WITH c
UNWIND $trials AS tr
  MERGE (t:Trial {nct_id: tr.nct_id})
    SET t.title = tr.title, t.status = tr.status
  MERGE (c)-[:STUDIED_BY]->(t)
  MERGE (h:Hospital {name: tr.hospital.name})
    SET h.city = tr.hospital.city, h.lat = tr.hospital.lat,
        h.lon = tr.hospital.lon, h.contact = tr.hospital.contact
  MERGE (t)-[:LOCATED_AT]->(h)
"""


def run() -> None:
    graph.init_constraints()
    with graph.get_driver().session() as ses:
        for cond in SEED["conditions"]:
            ses.run(
                UPSERT,
                condition=cond["name"],
                symptoms=cond["symptoms"],
                trials=cond["trials"],
            )
    print("Seed terminé :", len(SEED["conditions"]), "conditions insérées.")


if __name__ == "__main__":
    run()
