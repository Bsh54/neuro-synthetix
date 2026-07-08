"""Etape 1 du RAG : RETRIEVAL.

Ramene un jeu de candidats reels et bien classes depuis la grande base
(~5000 essais). Ranking : condition exacte > condition partielle > mot dans
conditions > mot dans le texte. Filtre optionnel par pays. Uniquement des essais
exploitables. Les candidats portent les champs d'eligibilite (age/sexe) pour
l'etape de re-rank par l'IA.

Index construit une fois (cache memoire).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).parent / "data" / "knowledge_base.json"

# poids de scoring
W_COND_EXACT = 6      # la condition demandee == une condition de l'essai
W_COND_PARTIAL = 3    # inclusion partielle de la condition
W_COND_IN_BLOB = 1
W_TERM_IN_COND = 2    # un symptome/mot present dans les conditions
W_TERM_IN_BLOB = 1    # present dans le texte (titre/resume/eligibilite)

# robustesse : variantes de noms de pays -> forme presente dans les donnees (anglais)
COUNTRY_ALIASES = {
    "usa": "united states", "us": "united states", "u.s.": "united states",
    "u.s.a.": "united states", "america": "united states", "etats-unis": "united states",
    "etats unis": "united states", "uk": "united kingdom", "u.k.": "united kingdom",
    "britain": "united kingdom", "england": "united kingdom", "great britain": "united kingdom",
    "royaume-uni": "united kingdom", "angleterre": "united kingdom",
    "uae": "united arab emirates", "emirates": "united arab emirates",
    "inde": "india", "allemagne": "germany", "espagne": "spain", "italie": "italy",
    "chine": "china", "japon": "japan", "bresil": "brazil", "coree": "korea",
    "south korea": "korea", "coree du sud": "korea", "russie": "russian federation",
    "russia": "russian federation", "pays-bas": "netherlands", "hollande": "netherlands",
    "belgique": "belgium", "suisse": "switzerland", "autriche": "austria",
    "grece": "greece", "turquie": "turkey", "egypte": "egypt", "afrique du sud": "south africa",
    "benin": "benin", "senegal": "senegal", "cote d'ivoire": "cote d'ivoire",
}


def _norm_country(c: str) -> str:
    c = (c or "").lower().strip()
    return COUNTRY_ALIASES.get(c, c)


def _hospitals(locs: list) -> list[dict]:
    out = []
    for loc in (locs or [])[:3]:
        if isinstance(loc, dict) and (loc.get("facility") or loc.get("country")):
            out.append({
                "name": loc.get("facility") or loc.get("country"),
                "city": loc.get("city", ""), "country": loc.get("country", ""),
                "contact": loc.get("contact", ""),
            })
    return out


@lru_cache(maxsize=1)
def _index() -> list[dict]:
    try:
        data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    idx: list[dict] = []
    for t in data.get("trials", []):
        conds = t.get("conditions") or []
        conds_l = [c.lower().strip() for c in conds if c]
        elig = t.get("eligibility") or {}
        elig = elig if isinstance(elig, dict) else {}
        blob = " ".join([
            t.get("title", ""), " ".join(conds), (t.get("summary") or ""),
            (elig.get("criteria", "") or "")[:400],
        ]).lower()
        countries = " ".join(
            (loc.get("country") or "") for loc in (t.get("locations") or []) if isinstance(loc, dict)
        ).lower()
        hosp = _hospitals(t.get("locations"))
        idx.append({
            "blob": blob,
            "conds_l": conds_l,
            "conds_set": set(conds_l),
            "countries": countries,
            "cand": {
                "nct_id": t.get("id"),
                "title": (t.get("title") or t.get("id") or "")[:140],
                "conditions": conds[:4],
                "condition": conds[0][:60] if conds else "",
                "status": t.get("status", "RECRUITING"),
                "source": t.get("source", ""),
                "url": t.get("url", ""),
                "hospitals": hosp,
                "country": (hosp[0]["country"] if hosp else ""),
                "min_age": elig.get("min_age", ""),
                "max_age": elig.get("max_age", ""),
                "sex": elig.get("sex", ""),
            },
        })
    return idx


def retrieve(terms: list[str], condition: str | None = None,
             country: str | None = None, limit: int = 25) -> list[dict]:
    """Retourne jusqu'a `limit` candidats reels tries par pertinence.

    terms      : symptomes / mots-cles (anglais).
    condition  : condition/maladie visee (anglais), optionnel.
    country    : filtre pays (nom en anglais), optionnel.
    """
    words = [w.lower().strip() for w in (terms or []) if w and len(w.strip()) > 2]
    words = list(dict.fromkeys(words))
    cond_l = (condition or "").lower().strip()
    ctry = _norm_country(country)

    if not words and not cond_l and not ctry:
        return []

    scored: list[dict] = []
    for row in _index():
        if ctry and ctry not in row["countries"]:
            continue
        s = 0
        if cond_l:
            if cond_l in row["conds_set"]:
                s += W_COND_EXACT
            elif any(cond_l in c or c in cond_l for c in row["conds_l"]):
                s += W_COND_PARTIAL
            elif cond_l in row["blob"]:
                s += W_COND_IN_BLOB
        for w in words:
            if any(w in c for c in row["conds_l"]):
                s += W_TERM_IN_COND
            elif w in row["blob"]:
                s += W_TERM_IN_BLOB
        # si un pays est demande, un match pays suffit (les mots ne font que classer).
        # sinon il faut au moins un signal (condition ou mot).
        if s == 0 and not ctry:
            continue
        cand = dict(row["cand"])
        cand["score"] = s if s else 1
        scored.append(cand)

    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]


def compact_for_llm(cands: list[dict]) -> list[dict]:
    """Version minimale des candidats a donner au modele pour le re-rank."""
    out = []
    for c in cands:
        elig = []
        if c.get("sex") and c["sex"].upper() not in ("ALL", "", "BOTH"):
            elig.append(c["sex"])
        if c.get("min_age"):
            elig.append("min " + str(c["min_age"]))
        if c.get("max_age"):
            elig.append("max " + str(c["max_age"]))
        out.append({
            "id": c.get("nct_id"),
            "title": c.get("title", ""),
            "conditions": c.get("conditions", []),
            "country": c.get("country", ""),
            "eligibility": ", ".join(elig),
        })
    return out
