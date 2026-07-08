"""Agrege la base de connaissances (knowledge_base.json) pour la page Atlas.

Charge le fichier une fois (cache memoire) et calcule des repartitions :
par source, par condition, par pays. Sert la visualisation /explore.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).parent / "data" / "knowledge_base.json"

_STOP = {"", "healthy", "healthy volunteers", "none", "not applicable", "n/a"}


def _norm(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s[:60]


@lru_cache(maxsize=1)
def _load() -> dict:
    try:
        data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"trials": [], "sources": {}}
    return data


@lru_cache(maxsize=1)
def _site_index() -> dict:
    """Index (nom_labo, ville) -> essais qui y recrutent."""
    data = _load()
    idx: dict = defaultdict(list)
    for t in data.get("trials", []):
        summ = {
            "nct_id": t.get("id"),
            "title": (t.get("title") or t.get("id") or "")[:110],
            "condition": ((t.get("conditions") or [""])[0] or "")[:50] if t.get("conditions") else "",
            "status": t.get("status", "RECRUITING"),
            "url": t.get("url", ""),
        }
        seen_site = set()
        for loc in (t.get("locations") or []):
            if not isinstance(loc, dict):
                continue
            key = ((loc.get("facility") or "").strip().lower(), (loc.get("city") or "").strip().lower())
            if key == ("", "") or key in seen_site:
                continue
            seen_site.add(key)
            idx[key].append(summ)
    return idx


def site_trials(name: str, city: str, limit: int = 12) -> dict:
    idx = _site_index()
    rows = idx.get(((name or "").strip().lower(), (city or "").strip().lower()), [])
    seen, out = set(), []
    for r in rows:
        if r["nct_id"] in seen:
            continue
        seen.add(r["nct_id"])
        out.append(r)
        if len(out) >= limit:
            break
    return {"name": name, "city": city, "count": len(out), "trials": out}


@lru_cache(maxsize=1)
def locations() -> dict:
    """Tous les sites de recherche geolocalises de la base (lat/lon)."""
    data = _load()
    seen: set = set()
    pts: list[dict] = []
    for t in data.get("trials", []):
        for loc in (t.get("locations") or []):
            if not isinstance(loc, dict):
                continue
            lat, lon = loc.get("lat"), loc.get("lon")
            if lat is None or lon is None:
                continue
            key = (round(float(lat), 3), round(float(lon), 3), loc.get("facility", ""))
            if key in seen:
                continue
            seen.add(key)
            pts.append({
                "lat": float(lat), "lon": float(lon),
                "name": (loc.get("facility") or "")[:80],
                "city": loc.get("city", ""), "country": loc.get("country", ""),
            })
    return {"count": len(pts), "points": pts}


@lru_cache(maxsize=1)
def compute() -> dict:
    data = _load()
    trials = data.get("trials", [])
    sources = Counter()
    conditions = Counter()
    countries = Counter()

    for t in trials:
        sources[t.get("source", "?")] += 1
        for c in (t.get("conditions") or []):
            cn = _norm(c)
            if cn.lower() not in _STOP and len(cn) > 2:
                conditions[cn] += 1
        for loc in (t.get("locations") or []):
            cy = _norm(loc.get("country", "")) if isinstance(loc, dict) else ""
            if cy:
                countries[cy] += 1

    return {
        "total": len(trials),
        "sources": [{"name": k, "count": v} for k, v in sources.most_common()],
        "n_sources": len(sources),
        "top_conditions": [{"name": k, "count": v} for k, v in conditions.most_common(14)],
        "n_conditions": len(conditions),
        "top_countries": [{"name": k, "count": v} for k, v in countries.most_common(14)],
        "n_countries": len(countries),
    }
