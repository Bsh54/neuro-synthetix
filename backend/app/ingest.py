"""Ingestion de VRAIS essais cliniques depuis ClinicalTrials.gov (API v2).

- Les essais, hôpitaux, contacts et coordonnées GPS sont réels (API publique).
- Le lien Symptôme -> Condition est une table médicale curée (orientation,
  pas diagnostic). Les symptômes canoniques correspondent au lexique de extract.py.

Usage :  python -m app.ingest
"""
from __future__ import annotations

import httpx

from . import graph
from .conditions import CONDITION_SYMPTOMS

API = "https://clinicaltrials.gov/api/v2/studies"

FIELDS = ",".join([
    "protocolSection.identificationModule.nctId",
    "protocolSection.identificationModule.briefTitle",
    "protocolSection.conditionsModule.conditions",
    "protocolSection.statusModule.overallStatus",
    "protocolSection.contactsLocationsModule.locations",
])

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
  WITH c, t, tr
  UNWIND tr.hospitals AS h
    MERGE (hp:Hospital {name: h.name})
      SET hp.city = h.city, hp.country = h.country,
          hp.lat = h.lat, hp.lon = h.lon, hp.contact = h.contact
    MERGE (t)-[:LOCATED_AT]->(hp)
"""


def _fetch(condition: str, page_size: int = 15) -> list[dict]:
    params = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING",
        "pageSize": str(page_size),
        "fields": FIELDS,
    }
    r = httpx.get(API, params=params, timeout=30)
    r.raise_for_status()
    studies = r.json().get("studies", [])
    trials: list[dict] = []
    for s in studies:
        ps = s.get("protocolSection", {})
        ident = ps.get("identificationModule", {})
        nct = ident.get("nctId")
        if not nct:
            continue
        locs = ps.get("contactsLocationsModule", {}).get("locations", []) or []
        hospitals = []
        for loc in locs:
            if not loc.get("facility") or "geoPoint" not in loc:
                continue
            contact = ""
            for ct in loc.get("contacts", []):
                if ct.get("email") or ct.get("phone"):
                    contact = " ".join(filter(None, [ct.get("name"), ct.get("email"), ct.get("phone")]))
                    break
            gp = loc["geoPoint"]
            hospitals.append({
                "name": loc["facility"],
                "city": loc.get("city", ""),
                "country": loc.get("country", ""),
                "lat": gp.get("lat"), "lon": gp.get("lon"),
                "contact": contact,
            })
            if len(hospitals) >= 3:
                break
        if not hospitals:
            continue
        trials.append({
            "nct_id": nct,
            "title": ident.get("briefTitle", nct),
            "status": ps.get("statusModule", {}).get("overallStatus", "RECRUITING"),
            "hospitals": hospitals,
        })
    return trials


def run() -> None:
    graph.init_constraints()
    total = 0
    with graph.get_driver().session() as ses:
        for condition, symptoms in CONDITION_SYMPTOMS.items():
            trials = _fetch(condition)
            if not trials:
                print(f"  {condition}: aucun essai avec localisation, ignoré.")
                continue
            ses.run(UPSERT, condition=condition, symptoms=symptoms, trials=trials)
            total += len(trials)
            print(f"  {condition}: {len(trials)} essais réels insérés.")
    print(f"Ingestion terminée : {total} essais réels au total.")


if __name__ == "__main__":
    run()
