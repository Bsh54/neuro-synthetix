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

# Messages de repli localises (rerank indisponible / rien de pertinent)
_FALLBACK = {
    "en": "Here are some trials that may be relevant. Please see a doctor to confirm.",
    "fr": "Voici quelques essais qui pourraient etre pertinents. Parlez-en a un medecin pour confirmer.",
    "hi": "यहाँ कुछ ट्रायल हैं जो प्रासंगिक हो सकते हैं। कृपया पुष्टि के लिए डॉक्टर से मिलें।",
}
_NOFIT = {
    "en": "I could not find a trial that clearly fits. It is best to see a doctor who can guide you.",
    "fr": "Je n'ai pas trouve d'essai clairement adapte. Le mieux est de voir un medecin qui pourra vous orienter.",
    "hi": "मुझे स्पष्ट रूप से उपयुक्त ट्रायल नहीं मिला। किसी डॉक्टर से मिलना सबसे अच्छा रहेगा जो आपका मार्गदर्शन कर सके।",
}


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
    need_tr = lang in ("fr", "hi")   # anglais interne pour tous : on traduit fr ET hi

    # 1) ENTREE -> anglais (pour toute langue non anglaise). Le pipeline entier est en anglais.
    user_en = req.message
    if need_tr:
        t = await tr.translate(req.message, lang, "en")
        if t:
            user_en = t

    # 2) Conversation en ANGLAIS uniquement (tool calling fiable, aucun melange de langues).
    #    L'historique recu est deja en anglais (on renvoie user_en / reply_en cote anglais).
    parts = []
    user_turns = sum(1 for m in req.history if m.role == "user")
    if user_turns >= 3:
        parts.append(
            "You have already asked questions without searching. Stop asking open questions. "
            "Propose concrete possibilities as simple yes/no questions, and as soon as the patient "
            "confirms anything, call the search_clinical_trials tool. Do not keep them waiting."
        )
    directive = " ".join(parts) or None
    msgs = [{"role": m.role, "content": m.content} for m in req.history[-10:]]
    msgs.append({"role": "user", "content": user_en})
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
        # Filet de securite (general, sans biais) : si l'appel arrive sans condition ni symptome
        # (le modele n'a passe qu'un age/lieu), on deduit condition/symptomes en anglais depuis
        # TOUTE la conversation (deja en anglais). Garantit le report du contexte.
        if not condition and not symptoms:
            convo_en = " ".join([m.content for m in req.history if m.content] + [user_en])
            ex = await deepseek.extract_terms(convo_en)
            condition = ex.get("condition") or condition
            symptoms = ex.get("symptoms") or symptoms
            location = location or ex.get("location") or ""
        keywords = extract_keywords(" ".join(symptoms + [condition, user_en]))

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

        # RE-RANK IA (etape 2 + eligibilite) EN ANGLAIS : pertinents + raison, filtre age/sexe.
        # req_text porte la condition/symptomes accumules pour que le rerank ait le contexte.
        patient = {"age": args.get("age"), "sex": args.get("sex")}
        ask = " ".join([condition] + symptoms).strip() or user_en
        req_text = ask + (f" (location: {location})" if location else "")
        rr = await deepseek.rerank(req_text, retrieval.compact_for_llm(cands[:25]),
                                   patient=patient, lang_directive=None)
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
                elig = await deepseek.eligibility(req_text, patient, chosen, lang_directive=None)
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
            # le modele a juge qu'aucun candidat n'est pertinent : on est honnete (anglais, traduit ensuite)
            trials = None
            visible = deepseek.clean((rr or {}).get("intro") or "") or _NOFIT["en"]
        else:
            # repli si le re-rank echoue : meilleurs candidats bruts (message anglais, traduit ensuite)
            trials = _merge_trials(neo, cands, limit=6) or None
            visible = _FALLBACK["en"] if trials else _NOFIT["en"]
    else:
        visible = deepseek.clean(m1.get("content") or "")

    # Contexte d'historique : toujours en ANGLAIS. Pour une recherche, on note la condition
    # cherchee (marqueur) pour que le tour suivant conserve le sujet meme si le patient
    # n'ajoute qu'un age ou un lieu.
    if tool_calls:
        _ask = " ".join([condition] + symptoms).strip()
        reply_en_hist = ("I searched clinical trials for " + (_ask or "the patient's request")
                         + (f" in {location}" if location else "") + ".")
    else:
        reply_en_hist = visible

    # 5) SORTIE -> langue du patient (fr ET hi). Anglais : rien a traduire.
    reply_display = visible
    if need_tr and visible:
        t2 = await tr.translate(visible, "en", lang)
        if t2:
            reply_display = deepseek.clean(t2)
    # Traduction des raisons + libelles de criteres des essais (un seul appel par lot).
    if need_tr and trials:
        await _translate_trials(trials, lang)

    return {
        "reply": reply_display,        # a afficher / a lire (langue du patient)
        "reply_en": reply_en_hist,     # contexte historique (toujours anglais)
        "user_en": user_en,            # contexte historique (toujours anglais)
        "keywords": keywords,
        "trials": trials,
        "graph": graph_payload,
        "searched": bool(tool_calls),
        "disclaimer": DISCLAIMER,
    }


async def _translate_trials(trials: list, lang: str) -> None:
    """Traduit en place les raisons et libelles de criteres vers la langue du patient,
    en un seul appel groupe (robuste : si le decoupage ne correspond pas, on garde l'anglais)."""
    segs: list[str] = []
    slots: list = []  # (trial_index, 'reason') ou (trial_index, 'crit', crit_index)
    for i, t in enumerate(trials):
        if t.get("reason"):
            segs.append(t["reason"]); slots.append((i, "reason", None))
        for j, cr in enumerate(t.get("criteria_match") or []):
            if cr.get("label"):
                segs.append(cr["label"]); slots.append((i, "crit", j))
    if not segs:
        return
    SEP = "\n@@@\n"
    joined = SEP.join(segs)
    out = await tr.translate(joined, "en", lang)
    if not out:
        return
    parts = [p.strip() for p in out.split("@@@")]
    if len(parts) != len(segs):
        parts = [p.strip() for p in out.split("\n") if p.strip()]
    if len(parts) != len(segs):
        return  # decoupage incertain : on garde l'anglais plutot que de melanger
    for (i, kind, j), tx in zip(slots, parts):
        tx = deepseek.clean(tx)
        if kind == "reason":
            trials[i]["reason"] = tx
        else:
            trials[i]["criteria_match"][j]["label"] = tx


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
