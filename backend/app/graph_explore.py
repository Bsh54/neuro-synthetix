"""Drill-down dans la base de connaissances : Pays -> Etablissement -> Essais.

Indexe knowledge_base.json une fois (cache) et sert l'exploration :
  query()                      -> liste des pays (avec compte)
  query(country)               -> etablissements de ce pays (ou essais si aucun)
  query(country, facility)     -> essais de cet etablissement
"""
from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).parent / "data" / "knowledge_base.json"


def _mini(t: dict, city: str = "", contact: str = "") -> dict:
    conds = t.get("conditions") or []
    return {
        "id": t.get("id"),
        "title": (t.get("title") or t.get("id") or "")[:120],
        "condition": (conds[0] if conds else "")[:60],
        "source": t.get("source", ""),
        "url": t.get("url", ""),
        "city": city, "contact": contact,
    }


@lru_cache(maxsize=1)
def _index() -> dict:
    try:
        data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    idx: dict = defaultdict(lambda: {"count": 0, "facilities": defaultdict(list), "nofac": []})
    for t in data.get("trials", []):
        locs = t.get("locations") or []
        if not locs:
            continue
        seen_country = set()
        for loc in locs:
            if not isinstance(loc, dict):
                continue
            country = (loc.get("country") or "").strip()
            if not country:
                continue
            fac = (loc.get("facility") or "").strip()
            city = (loc.get("city") or "").strip()
            contact = (loc.get("contact") or "").strip()
            node = idx[country]
            if country not in seen_country:
                node["count"] += 1
                seen_country.add(country)
            if fac:
                node["facilities"][fac].append(_mini(t, city, contact))
            else:
                node["nofac"].append(_mini(t, city, contact))
    return idx


_STOP = {"", "healthy", "healthy volunteers", "none", "not applicable", "n/a"}


@lru_cache(maxsize=1)
def _cond_index() -> dict:
    """Index patient-centre : condition -> pays -> essais (avec hopital)."""
    try:
        data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    idx: dict = defaultdict(lambda: {"count": 0, "countries": defaultdict(list)})
    for t in data.get("trials", []):
        conds = []
        for c in (t.get("conditions") or []):
            cn = (c or "").strip()[:55]
            if cn and cn.lower() not in _STOP and len(cn) > 2:
                conds.append(cn)
        if not conds:
            continue
        # regrouper les lieux par pays (avec 1er hopital/contact)
        by_country: dict[str, dict] = {}
        for loc in (t.get("locations") or []):
            if not isinstance(loc, dict):
                continue
            country = (loc.get("country") or "").strip()
            if not country:
                continue
            by_country.setdefault(country, {
                "hospital": (loc.get("facility") or "").strip(),
                "city": (loc.get("city") or "").strip(),
                "contact": (loc.get("contact") or "").strip(),
            })
        if not by_country:
            continue
        for cond in set(conds):
            node = idx[cond]
            node["count"] += 1
            for country, info in by_country.items():
                node["countries"][country].append({
                    "id": t.get("id"), "title": (t.get("title") or t.get("id") or "")[:120],
                    "condition": cond, "source": t.get("source", ""), "url": t.get("url", ""),
                    "hospital": info["hospital"], "city": info["city"], "contact": info["contact"],
                })
    return idx


def flow(condition: str | None = None, country: str | None = None) -> dict:
    """Exploration patient-centree : condition -> pays -> essais."""
    idx = _cond_index()
    if not condition:
        items = sorted(({"name": k, "count": v["count"]} for k, v in idx.items()),
                       key=lambda x: -x["count"])
        return {"level": "condition", "items": items[:40]}
    node = idx.get(condition)
    if not node:
        return {"level": "country", "parent": condition, "items": []}
    if not country:
        items = sorted(({"name": k, "count": len(v)} for k, v in node["countries"].items()),
                       key=lambda x: -x["count"])
        return {"level": "country", "parent": condition, "items": items[:40]}
    trials = node["countries"].get(country, [])
    seen, uniq = set(), []
    for t in trials:
        if t["id"] not in seen:
            seen.add(t["id"]); uniq.append(t)
    return {"level": "trial", "parent": country, "items": uniq[:80]}


def query(country: str | None = None, facility: str | None = None) -> dict:
    idx = _index()
    if not country:
        items = sorted(({"name": k, "count": v["count"]} for k, v in idx.items()),
                       key=lambda x: -x["count"])
        return {"level": "country", "items": items[:60]}

    node = idx.get(country)
    if not node:
        return {"level": "facility", "parent": country, "items": []}

    if not facility:
        facs = sorted(({"name": f, "count": len(tr)} for f, tr in node["facilities"].items()),
                      key=lambda x: -x["count"])
        if facs:
            return {"level": "facility", "parent": country, "items": facs[:60]}
        # pas d'etablissement nomme -> renvoyer directement les essais
        return {"level": "trial", "parent": country, "items": node["nofac"][:60]}

    trials = node["facilities"].get(facility, [])
    # dedupe par id
    seen, uniq = set(), []
    for t in trials:
        if t["id"] not in seen:
            seen.add(t["id"]); uniq.append(t)
    return {"level": "trial", "parent": facility, "items": uniq[:80]}
