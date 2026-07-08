"""Collecteur MASSIF de donnees d'essais cliniques -> base de connaissances IA.

Objectif : aspirer le plus de donnees reelles possibles, de plusieurs sources,
SANS se limiter a une liste de conditions. La future IA se servira de ce corpus
brut pour poser de meilleures questions et proposer des programmes.

Sources :
  - ClinicalTrials.gov (API v2)        -> collecte en masse (pagination)  [fiable]
  - ISRCTN (UK/international)           -> collecte en masse               [fiable]
  - CTRI (Inde)                         -> scraping best-effort            [fragile]
  - EU Clinical Trials Register        -> scraping best-effort            [fragile]

Ecrit app/data/knowledge_base.json.  Usage : python -m app.kb_builder
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

CT_API = "https://clinicaltrials.gov/api/v2/studies"
ISRCTN_API = "https://www.isrctn.com/api/query/format/default"
CTIS_API = "https://euclinicaltrials.eu/ctis-public-api/search"

OUT = Path(__file__).parent / "data" / "knowledge_base.json"

MAX_CT = 2500      # nombre max d'essais ClinicalTrials.gov a aspirer
MAX_CTIS = 1500    # nombre max d'essais CTIS (EU)
MAX_ISRCTN = 400
UA = {"User-Agent": "Mozilla/5.0 (NeuroSynthetix data collector)"}

CT_FIELDS = ",".join([
    "protocolSection.identificationModule.nctId",
    "protocolSection.identificationModule.briefTitle",
    "protocolSection.conditionsModule.conditions",
    "protocolSection.statusModule.overallStatus",
    "protocolSection.descriptionModule.briefSummary",
    "protocolSection.eligibilityModule.eligibilityCriteria",
    "protocolSection.eligibilityModule.sex",
    "protocolSection.eligibilityModule.minimumAge",
    "protocolSection.eligibilityModule.maximumAge",
    "protocolSection.eligibilityModule.healthyVolunteers",
    "protocolSection.contactsLocationsModule.locations",
])


def _locations(ps: dict) -> list[dict]:
    out = []
    for loc in ps.get("contactsLocationsModule", {}).get("locations", []) or []:
        if not loc.get("facility"):
            continue
        contact = ""
        for ct in loc.get("contacts", []) or []:
            if ct.get("email") or ct.get("phone"):
                contact = " ".join(filter(None, [ct.get("name"), ct.get("email"), ct.get("phone")]))
                break
        gp = loc.get("geoPoint", {})
        out.append({
            "facility": loc["facility"], "city": loc.get("city", ""),
            "state": loc.get("state", ""), "country": loc.get("country", ""),
            "lat": gp.get("lat"), "lon": gp.get("lon"), "contact": contact,
        })
    return out


def fetch_ct_bulk(max_trials: int = MAX_CT, page: int = 100, locn: str | None = None,
                  source_label: str = "ClinicalTrials.gov") -> list[dict]:
    """Aspire en masse les essais RECRUTANT de ClinicalTrials.gov (pagination).
    Si locn est fourni (ex. 'India'), ne prend que les essais localises la-bas."""
    out: list[dict] = []
    token = None
    with httpx.Client(timeout=60, headers=UA) as cl:
        while len(out) < max_trials:
            params = {"filter.overallStatus": "RECRUITING", "pageSize": str(page), "fields": CT_FIELDS}
            if locn:
                params["query.locn"] = locn
            if token:
                params["pageToken"] = token
            r = cl.get(CT_API, params=params)
            r.raise_for_status()
            data = r.json()
            for s in data.get("studies", []):
                ps = s.get("protocolSection", {})
                ident = ps.get("identificationModule", {})
                elig = ps.get("eligibilityModule", {})
                nct = ident.get("nctId")
                if not nct:
                    continue
                out.append({
                    "source": source_label, "id": nct,
                    "url": f"https://clinicaltrials.gov/study/{nct}",
                    "title": ident.get("briefTitle", nct),
                    "status": ps.get("statusModule", {}).get("overallStatus", "RECRUITING"),
                    "conditions": ps.get("conditionsModule", {}).get("conditions", []),
                    "summary": (ps.get("descriptionModule", {}) or {}).get("briefSummary", "")[:600],
                    "eligibility": {
                        "criteria": (elig.get("eligibilityCriteria", "") or "")[:1200],
                        "sex": elig.get("sex", ""), "min_age": elig.get("minimumAge", ""),
                        "max_age": elig.get("maximumAge", ""),
                        "healthy_volunteers": elig.get("healthyVolunteers", None),
                    },
                    "locations": _locations(ps),
                })
            token = data.get("nextPageToken")
            print(f"    CT.gov collected: {len(out)}")
            if not token:
                break
    return out[:max_trials]


ISRCTN_TERMS = [
    "cancer", "diabetes", "heart", "infection", "lung", "kidney", "liver",
    "brain", "blood", "bone", "skin", "mental health", "virus", "pain",
    "children", "women", "asthma", "stroke", "obesity", "vaccine",
]


def fetch_isrctn_bulk(per_term: int = 40) -> list[dict]:
    """Aspire ISRCTN sur un large panel de termes (q= est obligatoire)."""
    seen: set[str] = set()
    out: list[dict] = []
    with httpx.Client(timeout=60, headers=UA) as cl:
        for term in ISRCTN_TERMS:
            try:
                r = cl.get(ISRCTN_API, params={"q": term, "limit": str(per_term)})
                r.raise_for_status()
            except Exception:
                continue
            for m in re.finditer(r"<fullTrial>(.*?)</fullTrial>", r.text, re.S):
                block = m.group(1)
                tid = re.search(r"<isrctn[^>]*>(\d+)</isrctn>", block)
                if not tid or tid.group(1) in seen:
                    continue
                seen.add(tid.group(1))
                title = re.search(r"<scientificTitle>(.*?)</scientificTitle>", block, re.S)
                cond = re.search(r"<condition>(.*?)</condition>", block, re.S)
                out.append({
                    "source": "ISRCTN", "id": f"ISRCTN{tid.group(1)}",
                    "url": f"https://www.isrctn.com/ISRCTN{tid.group(1)}",
                    "title": (title.group(1).strip() if title else f"ISRCTN{tid.group(1)}")[:300],
                    "status": "RECRUITING",
                    "conditions": [cond.group(1).strip()] if cond else [],
                    "summary": "", "eligibility": {}, "locations": [],
                })
    return out


def scrape_ctri(max_pages: int = 3) -> list[dict]:
    """CTRI Inde : scraping best-effort. Renvoie [] si bloque/indisponible."""
    out: list[dict] = []
    try:
        with httpx.Client(timeout=40, headers=UA, follow_redirects=True) as cl:
            r = cl.get("https://ctri.nic.in/Clinicaltrials/login.php")
            if r.status_code != 200:
                return out
            # CTRI n'a pas d'API ; on extrait les numeros CTRI visibles si presents
            for m in re.finditer(r"(CTRI/\d{4}/\d{2}/\d{6})", r.text):
                out.append({
                    "source": "CTRI", "id": m.group(1),
                    "url": "https://ctri.nic.in/", "title": m.group(1),
                    "status": "UNKNOWN", "conditions": [], "summary": "",
                    "eligibility": {}, "locations": [{"country": "India"}],
                })
    except Exception:
        return []
    # dedupe
    seen = set(); uniq = []
    for t in out:
        if t["id"] not in seen:
            seen.add(t["id"]); uniq.append(t)
    return uniq


def fetch_ctis_bulk(max_trials: int = MAX_CTIS, page_size: int = 100) -> list[dict]:
    """CTIS (EU) : vraie API publique JSON, aspiration en masse par pagination."""
    out: list[dict] = []
    with httpx.Client(timeout=60, headers=UA) as cl:
        page = 1
        while len(out) < max_trials:
            body = {"pagination": {"page": page, "size": page_size}, "searchCriteria": {}}
            r = cl.post(CTIS_API, json=body)
            r.raise_for_status()
            data = r.json()
            rows = data.get("data", [])
            if not rows:
                break
            for t in rows:
                num = t.get("ctNumber")
                if not num:
                    continue
                countries = [c.split(":")[0] for c in (t.get("trialCountries") or [])]
                cond = t.get("conditions") or ""
                out.append({
                    "source": "CTIS-EU", "id": num,
                    "url": f"https://euclinicaltrials.eu/ctis-public/view/{num}",
                    "title": (t.get("ctTitle") or t.get("shortTitle") or num)[:300],
                    "status": str(t.get("ctStatus", "")),
                    "conditions": [cond] if isinstance(cond, str) and cond else (cond or []),
                    "summary": "",
                    "phase": t.get("trialPhase", ""),
                    "sponsor": t.get("sponsor", ""),
                    "eligibility": {},
                    "locations": [{"country": c} for c in countries],
                })
            print(f"    CTIS collected: {len(out)}")
            if not data.get("pagination", {}).get("nextPage"):
                break
            page += 1
    return out[:max_trials]


def build() -> dict:
    trials: list[dict] = []
    sources: dict[str, int] = {}

    def fetch_ct_india():
        return fetch_ct_bulk(max_trials=600, locn="India",
                             source_label="ClinicalTrials.gov (India)")

    for name, fn in [
        ("ClinicalTrials.gov", fetch_ct_bulk),
        ("ClinicalTrials.gov (India)", fetch_ct_india),
        ("CTIS-EU", fetch_ctis_bulk),
        ("ISRCTN", fetch_isrctn_bulk),
        ("CTRI", scrape_ctri),
    ]:
        try:
            got = fn()
            trials.extend(got)
            sources[name] = len(got)
            print(f"  {name}: {len(got)} trials")
        except Exception as e:  # noqa: BLE001
            sources[name] = 0
            print(f"  {name}: skipped ({e})")

    return {
        "version": 3,
        "generated_for": "Neuro-Synthetix AI assistant knowledge base",
        "sources": sources,
        "trial_count": len(trials),
        "trials": trials,
    }


def run() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    kb = build()
    OUT.write_text(json.dumps(kb, ensure_ascii=False), encoding="utf-8")
    size_mb = OUT.stat().st_size / 1e6
    print(f"Knowledge base : {OUT}  ({kb['trial_count']} essais, {size_mb:.1f} Mo)")
    print(f"Sources: {kb['sources']}")


if __name__ == "__main__":
    run()
