from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import json

from . import graph, sarvam, translate as tr, deepseek, retrieval
from .extract import extract_keywords


def _merge_trials(neo: list, kb: list, limit: int = 8) -> list:
    """Fusionne Neo4j (graphe + hopitaux) et grande base (couverture), sans doublon."""
    out, seen = [], set()
    for t in (neo or []) + (kb or []):
        nid = t.get("nct_id")
        if nid and nid in seen:
            continue
        if nid:
            seen.add(nid)
        out.append(t)
        if len(out) >= limit:
            break
    return out

app = FastAPI(title="Neuro-Synthetix API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DISCLAIMER = (
    "This is not a medical diagnosis. These results are indicative only. "
    "See a doctor to confirm your eligibility for a clinical trial."
)


@app.on_event("startup")
def _startup() -> None:
    try:
        graph.init_constraints()
    except Exception:
        pass


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def landing() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/app")
def app_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/proof")
def proof_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "proof.html")


@app.get("/stats")
def stats() -> dict:
    from . import stats as _s
    return _s.compute()


@app.get("/locations")
def locations() -> dict:
    from . import stats as _s
    return _s.locations()


@app.get("/site")
def site(name: str = "", city: str = "") -> dict:
    from . import stats as _s
    return _s.site_trials(name, city)




@app.get("/health")
def health() -> dict:
    return {"status": "ok", "neo4j": graph.ping()}


@app.post("/reload")
def reload_data(token: str = "") -> dict:
    """Vide les caches memoire pour recharger la base de connaissances fraiche.
    Appele par le Render Workflow apres avoir livre le nouveau knowledge_base.json."""
    from .config import settings as _s
    if _s.reload_token and token != _s.reload_token:
        return {"reloaded": False, "error": "invalid token"}
    from . import retrieval, kb_search, stats
    for mod in (retrieval, kb_search):
        try:
            mod._index.cache_clear()
        except Exception:
            pass
    for fn in ("_load", "compute", "locations", "_site_index", "_cond_index"):
        try:
            getattr(stats, fn).cache_clear()
        except Exception:
            pass
    return {"reloaded": True}


class MatchRequest(BaseModel):
    text: str
    limit: int = 5
    lang: str = "en"


@app.post("/match")
async def match(req: MatchRequest) -> dict:
    """Texte libre (n'importe quelle langue) -> essais + graphe.
    Si lang != en, on traduit d'abord en anglais pour mieux comprendre."""
    text_en = req.text
    translated = None
    if req.lang and req.lang != "en":
        translated = await tr.translate(req.text, req.lang, "en")
        if translated:
            text_en = translated
    # on extrait sur l'original ET sur la traduction (union), pour robustesse
    keywords = extract_keywords(req.text)
    if translated:
        for k in extract_keywords(text_en):
            if k not in keywords:
                keywords.append(k)
    trials = graph.match_trials(keywords, limit=req.limit)
    payload = graph.build_graph_payload(trials)
    return {
        "keywords": keywords,
        "trials": trials,
        "graph": payload,
        "translated_input": translated,
        "disclaimer": DISCLAIMER,
    }


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    history: list[ChatMessage] = []
    message: str
    lang: str = "en"


@app.post("/chat")
async def chat_ep(req: ChatRequest) -> dict:
    """Conversation IA (DeepSeek) : une question a la fois, puis recherche d'essais.
    Le patient parle dans sa langue ; on raisonne/repond en anglais puis on retraduit."""
    lang = req.lang or "en"
    use_tr = (lang == "hi")   # la traduction ne sert QUE pour le hindi

    # 1) entree patient -> anglais UNIQUEMENT si hindi
    user_model = req.message
    if use_tr:
        t = await tr.translate(req.message, "hi", "en")
        if t:
            user_model = t

    # 2) DeepSeek (tool calling) : repond directement en fr/en ; anglais pour hindi
    parts = []
    if lang == "fr":
        parts.append("Always write your reply to the patient in French.")
    # apres plusieurs echanges sans recherche -> devenir proactif
    user_turns = sum(1 for m in req.history if m.role == "user")
    if user_turns >= 4:
        parts.append(
            "You have already asked several questions without running a search. "
            "Stop asking broad open questions. Instead, be proactive: propose specific "
            "symptoms or conditions the patient might have, as simple yes or no questions "
            "(for example: do you also suffer from this, or from that?). "
            "As soon as the patient confirms anything concrete, call the search_clinical_trials tool. "
            "Do not keep the patient waiting with endless questions."
        )
    directive = " ".join(parts) or None
    msgs = [{"role": m.role, "content": m.content} for m in req.history[-10:]]
    msgs.append({"role": "user", "content": user_model})
    m1 = await deepseek.complete(msgs, tools=deepseek.TOOLS, lang_directive=directive)
    if m1 is None:
        return {"reply": None, "error": "llm_unavailable", "user_en": req.message}

    trials = graph_payload = None
    keywords: list[str] = []
    tool_calls = m1.get("tool_calls") or []

    if tool_calls:
        # 3) le modele declenche la recherche -> Neo4j (graphe) + grande base (couverture)
        tc = tool_calls[0]
        try:
            args = json.loads(tc["function"]["arguments"] or "{}")
        except Exception:
            args = {}
        symptoms = [str(s) for s in (args.get("symptoms") or [])]
        condition = args.get("condition") or ""
        location = (args.get("location") or "").strip()
        keywords = extract_keywords(" ".join(symptoms + [condition, user_model]))

        # RETRIEVAL (etape 1) : candidats du pays demande + candidats globaux (alternatives)
        cands = retrieval.retrieve(
            terms=symptoms + keywords, condition=condition,
            country=location or None, limit=20,
        )
        if location:
            glob = retrieval.retrieve(terms=symptoms + keywords, condition=condition,
                                      country=None, limit=12)
            seen = {c["nct_id"] for c in cands}
            cands += [c for c in glob if c["nct_id"] not in seen]
            cands = cands[:26]
        # Neo4j : pour le graphe (relations symptome->condition->essai->hopital)
        neo = graph.match_trials(keywords, limit=6)
        if location and neo:
            loc_l = location.lower()
            neo = [t for t in neo if any(
                loc_l in (h.get("country", "") + " " + h.get("city", "")).lower()
                for h in (t.get("hospitals") or []))] or neo
        graph_payload = graph.build_graph_payload(neo) if neo else None

        # RE-RANK IA (etape 2 + eligibilite) : choisit les pertinents + raison, filtre age/sexe
        patient = {"age": args.get("age"), "sex": args.get("sex")}
        req_text = user_model + (f" (location: {location})" if location else "")
        rr = await deepseek.rerank(req_text, retrieval.compact_for_llm(cands[:25]),
                                   patient=patient, lang_directive=directive)
        by_id = {c["nct_id"]: c for c in cands}
        chosen = []
        for p in (rr or {}).get("picks", [])[:5]:
            c = by_id.get(p.get("id"))
            if c:
                cc = dict(c)
                cc["reason"] = deepseek.clean(p.get("reason") or "")
                chosen.append(cc)

        if chosen:
            # Analyse d'eligibilite par critere + confiance sur les essais retenus (2e passage cible)
            try:
                elig = await deepseek.eligibility(req_text, patient, chosen, lang_directive=directive)
            except Exception:
                elig = {}
            for cc in chosen:
                e = elig.get(cc.get("nct_id")) or {}
                if e.get("criteria"):
                    cc["criteria_match"] = e["criteria"]
                if e.get("confidence") is not None:
                    cc["confidence"] = e["confidence"]
            trials = chosen
            visible = deepseek.clean((rr or {}).get("intro") or "")
        elif rr is not None and not (rr or {}).get("picks"):
            # le modele a juge qu'aucun candidat n'est pertinent : on est honnete
            trials = None
            visible = deepseek.clean((rr or {}).get("intro") or "") or \
                "I could not find a trial that clearly fits. It is best to see a doctor who can guide you."
        else:
            # repli si le re-rank echoue : meilleurs candidats bruts
            trials = _merge_trials(neo, cands, limit=6) or None
            visible = "Here are some trials that may be relevant. Please see a doctor to confirm."
    else:
        visible = deepseek.clean(m1.get("content") or "")

    # 5) reponse -> hindi seulement si besoin
    reply_display = visible
    if use_tr and visible:
        t2 = await tr.translate(visible, "en", "hi")
        if t2:
            reply_display = deepseek.clean(t2)

    return {
        "reply": reply_display,        # a afficher / a lire
        "reply_en": visible,           # contexte historique (fr ou en)
        "user_en": user_model,         # contexte historique
        "keywords": keywords,
        "trials": trials,
        "graph": graph_payload,
        "searched": bool(tool_calls),
        "disclaimer": DISCLAIMER,
    }


class TTSRequest(BaseModel):
    text: str
    lang: str = "hi"


@app.post("/tts")
async def tts(req: TTSRequest) -> dict:
    """Synthese vocale Sarvam. Retourne {audio: base64|null, format:'wav'}."""
    audio = await sarvam.text_to_speech(req.text, req.lang)
    return {"audio": audio, "format": "wav"}


@app.post("/stt")
async def stt(file: UploadFile = File(...), lang: str = "hi") -> dict:
    """Transcription Sarvam (audio -> texte, langue d'origine)."""
    data = await file.read()
    text = await sarvam.speech_to_text(data, lang=lang, filename=file.filename or "audio.webm")
    return {"text": text}


class TranslateRequest(BaseModel):
    text: str
    source: str
    target: str


@app.post("/translate")
async def translate_ep(req: TranslateRequest) -> dict:
    out = await tr.translate(req.text, req.source, req.target)
    return {"text": out}
