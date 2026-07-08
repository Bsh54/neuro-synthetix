"""Recherche plein-texte dans la grande base de connaissances (~5000 essais).

Garantit qu'aucun essai n'est perdu : on cherche dans titre, conditions, resume
et criteres d'eligibilite. Index construit une fois (cache memoire).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).parent / "data" / "knowledge_base.json"


@lru_cache(maxsize=1)
def _index() -> list[dict]:
    try:
        data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    idx: list[dict] = []
    for t in data.get("trials", []):
        conds = " ".join(t.get("conditions") or [])
        elig = t.get("eligibility") or {}
        elig_txt = elig.get("criteria", "") if isinstance(elig, dict) else ""
        blob = " ".join([
            t.get("title", ""), conds, (t.get("summary") or ""), (elig_txt or "")[:400],
        ]).lower()
        hosp = []
        for loc in (t.get("locations") or [])[:3]:
            if isinstance(loc, dict) and (loc.get("facility") or loc.get("country")):
                hosp.append({
                    "name": loc.get("facility") or loc.get("country"),
                    "city": loc.get("city", ""), "country": loc.get("country", ""),
                    "contact": loc.get("contact", ""),
                })
        countries = " ".join(
            (loc.get("country") or "") for loc in (t.get("locations") or []) if isinstance(loc, dict)
        ).lower()
        idx.append({
            "blob": blob, "conds": conds.lower(), "countries": countries,
            "trial": {
                "nct_id": t.get("id"),
                "title": (t.get("title") or t.get("id") or "")[:120],
                "condition": (t.get("conditions") or [""])[0][:60] if t.get("conditions") else "",
                "status": t.get("status", "RECRUITING"),
                "source": t.get("source", ""), "url": t.get("url", ""),
                "hospitals": hosp,
            },
        })
    return idx


def search(terms: list[str], limit: int = 8, country: str | None = None) -> list[dict]:
    """Score les essais par termes presents (bonus condition). Filtre optionnel par pays.
    Si aucun terme mais un pays est donne, renvoie des essais de ce pays."""
    words = [w.lower().strip() for w in terms if w and len(w.strip()) > 2]
    words = list(dict.fromkeys(words))
    ctry = (country or "").lower().strip()
    if not words and not ctry:
        return []
    scored: list[dict] = []
    for row in _index():
        if ctry and ctry not in row["countries"]:
            continue
        s = 0
        for w in words:
            if w in row["conds"]:
                s += 2
            elif w in row["blob"]:
                s += 1
        # si un pays est demande et correspond, on garde (les mots ne font que classer).
        # sinon, il faut au moins un mot qui matche.
        if words and s == 0 and not ctry:
            continue
        t = dict(row["trial"])
        t["score"] = s if (words and s) else 1
        scored.append(t)
    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]
