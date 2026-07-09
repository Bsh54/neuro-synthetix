"""Couche conversationnelle IA (DeepSeek, compatible OpenAI).

Le modele mene la conversation : UNE question a la fois pour cerner le besoin
du patient, puis emet une directive de recherche que le backend execute.
Sortie en texte simple (aucun markdown, aucune etoile).
"""
from __future__ import annotations

import html
import re
import httpx

from .config import settings

BASE = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash"

SYSTEM_PROMPT = """You are Neuro-Synthetix, a warm, flexible and helpful assistant that helps people find clinical trials. You are NOT a doctor and you never diagnose.

You are the smart layer that understands people no matter how they express themselves: plain words, slang, a mentioned drug, a body part, a vague clue, another language, or a misspelling. Always turn what they say into clean standard English search terms before searching. Ask a short clarifying question when a clue is ambiguous.

You work in two modes; pick the right one:

MODE 1 - Direct request: if the person names a disease, a place, or asks a clear question (for example trials in a country, or trials for a specific disease), call the search tool right away with what they gave you. Do not interrogate them.

MODE 2 - Vague symptoms: act like a sharp, efficient clinician who is genuinely trying to help. Lead the conversation and gather the picture step by step:
- Ask ONE focused question at a time (one or two short sentences).
- Be proactive: instead of open questions, propose concrete possibilities to converge fast, as either/or or yes/no. For example: is the pain more in the chest or in the belly, do you also have fever, has it lasted days or weeks, did you ever have this before.
- Collect the key facts progressively: main symptom, how long, associated signs.
- Keep a running sense of how confident you are about the likely area.
THRESHOLD TO CONCLUDE: search EARLY. As soon as you can name a likely condition area from the symptoms, STOP asking and call the search tool. Ask at most TWO clarifying questions in a whole conversation before searching. Age and location are optional refinements: NEVER wait for them or block a search to get them. Do NOT ask for the person's sex unless the condition is clearly sex-specific (pregnancy, breast, ovarian, cervical, uterine, prostate, testicular). If the person tells you to just search, search immediately with whatever you have.
CARRY THE CONTEXT: when you call the search tool, you MUST include the condition and all symptoms established anywhere earlier in this conversation, not only the last message. If the person only adds an age, a sex or a location, keep the previously discussed symptoms and condition and search again with the fuller picture. Never search with only an age or location and no condition when a condition was already implied earlier. Never ask them to restate something they already implied.

You can also answer simple general questions about the service in one or two sentences.

Style:
- Plain, human language. Never use markdown, asterisks, stars, bullets, bold or headings. Plain sentences only. One or two sentences per message unless you are listing found trials.
- Reassuring and simple, for someone with no medical background.

Boundaries:
- Never give a diagnosis, never name a disease as your conclusion, never suggest medication or treatment. You only orient toward trials. If asked for medical advice, gently decline and suggest seeing a doctor.
- Never invent trials or facts. Only talk about trials the search tool actually returns. If the search returns nothing, say so honestly and kindly (for example, suggest looking in a nearby country or seeing a local doctor). Do not pretend results exist.

Eligibility:
- The patient's age and sex often decide whether they can join a trial. When it would help (for example a sex-specific condition, or when age clearly matters), ask the person their age or sex in one short question. Pass age and sex to the search tool whenever you know them, so ineligible trials can be filtered out.

Next steps:
- If the person asks what to do now, or how to join a trial after seeing results, explain the simple path in plain sentences: note the trial reference number, show it to their own doctor, contact the research site (give the contact shown for that trial if there is one, otherwise the hospital), the team will confirm their eligibility with a few checks, and taking part is free for patients. Always keep their doctor in the loop.

Searching:
- Call search_clinical_trials as soon as you have something usable: symptoms, or a disease/condition, or a location, or a combination. Put English words in the tool. Include the location whenever the person mentioned one.
- If the person simply names a country or city and asks whether there are trials there, call the tool immediately with just that location, without first asking for a condition. Then report honestly what came back, even if it is nothing.
- After results come back, briefly and plainly tell the person what was found, and remind them this is guidance, not a diagnosis.
"""

TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_clinical_trials",
        "description": "Search real recruiting clinical trials. Call only when you have a clear picture of the patient's symptoms.",
        "parameters": {
            "type": "object",
            "properties": {
                "symptoms": {"type": "array", "items": {"type": "string"},
                             "description": "key symptoms in plain standard English. Infer them from ANY wording the person used: everyday words, slang, a body part, a drug name, or an indirect clue. Translate to standard medical English terms."},
                "condition": {"type": "string", "description": "the disease or medical condition in standard English (normalize spelling and synonyms), optional"},
                "location": {"type": "string", "description": "country or city in its common English name (e.g. United States, United Kingdom, India), optional"},
                "age": {"type": "integer", "description": "the patient's age in years, if they mentioned it, optional"},
                "sex": {"type": "string", "enum": ["male", "female"], "description": "the patient's sex, if known and relevant, optional"},
            },
            "required": ["symptoms"],
        },
    },
}]

SEARCH_RE = re.compile(r"SEARCH_QUERY:\s*(.*?)(?:\|\s*LOCATION:\s*(.*))?$", re.I | re.M)


def clean(text: str) -> str:
    """Decode les entites HTML puis retire le markdown pour un rendu texte propre."""
    if not text:
        return ""
    text = html.unescape(text)                      # &#39; -> '  etc.
    text = re.sub(r"[*_`]+", "", text)              # gras / italique / code
    text = re.sub(r"^\s*[#>]+\s*", "", text, flags=re.M)  # titres / citations en debut de ligne
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.M)   # puces
    return re.sub(r"[ \t]{2,}", " ", text).strip()


async def complete(messages: list[dict], tools: list | None = None,
                   max_tokens: int = 700, lang_directive: str | None = None,
                   system_override: str | None = None) -> dict | None:
    """Retourne l'objet message brut du modele (content + eventuels tool_calls)."""
    if not settings.deepseek_api_key:
        return None
    base = system_override if system_override is not None else SYSTEM_PROMPT
    system = base + (("\n\n" + lang_directive) if lang_directive else "")
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    try:
        async with httpx.AsyncClient(timeout=50) as cl:
            r = await cl.post(BASE,
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}",
                         "Content-Type": "application/json"},
                json=payload)
            if r.status_code != 200:
                return None
            return r.json()["choices"][0]["message"]
    except Exception:
        return None


RERANK_SYSTEM = """You rank real clinical trials for a patient. You are given the patient's request and a list of CANDIDATE trials (each has an id, title, conditions, country, eligibility).

Your job:
- Select ONLY the candidates that are genuinely relevant to this patient: same or closely related condition. Drop anything off topic (do not pass an unrelated condition just because a single word matched).
- If the patient asked for a specific country, prefer trials in that country. If there are none there but genuinely relevant trials exist elsewhere, you may include up to 3 of them and clearly mention their country in the reason (for example: this trial is in India), so the patient knows the option exists abroad.
- Consider eligibility. Each candidate may carry an eligibility note (sex, min age, max age). If the patient's age or sex is given in the patient profile and a candidate clearly excludes them (wrong sex, or age outside the allowed range), do NOT choose it. When you do choose a trial that has a notable eligibility requirement, mention it briefly in the reason (for example: for adults over 18).
- Choose at most 5, best first.
- For each chosen trial, write ONE short plain sentence saying why it fits this patient.
- Also write a short, warm intro sentence for the patient.

Hard rules:
- Use ONLY ids that appear in the candidate list. Never invent an id or a trial.
- If none of the candidates are genuinely relevant, return an empty picks list and say so kindly in the intro.
- Never diagnose. This is orientation, not medical advice.
- Output STRICT JSON only, no markdown, no stars, no extra text:
{"intro": "one or two short sentences", "picks": [{"id": "...", "reason": "one short sentence"}]}
"""


async def rerank(request_text: str, candidates: list[dict],
                 patient: dict | None = None,
                 lang_directive: str | None = None) -> dict | None:
    """Re-rank IA. Retourne {intro, picks:[{id, reason}]} ou None."""
    import json as _json
    if not candidates:
        return {"intro": "", "picks": []}
    prof = []
    if patient:
        if patient.get("age") not in (None, ""):
            prof.append(f"age {patient['age']}")
        if patient.get("sex"):
            prof.append(str(patient["sex"]))
    profile = ", ".join(prof) if prof else "unknown"
    payload_msg = (
        "Patient profile: " + profile +
        "\n\nPatient request:\n" + request_text.strip()[:600] +
        "\n\nCandidate trials (choose ONLY from these ids):\n" +
        _json.dumps(candidates, ensure_ascii=False)
    )
    for attempt in range(2):
        m = await complete(
            [{"role": "user", "content": payload_msg}],
            max_tokens=2600, lang_directive=lang_directive, system_override=RERANK_SYSTEM,
        )
        if m:
            parsed = _parse_json(m.get("content") or "")
            if isinstance(parsed, dict) and (parsed.get("picks") or parsed.get("intro")):
                return parsed
    return None


ELIG_SYSTEM = """You assess, for a patient, whether they might be eligible for each clinical trial, using ONLY the trial's eligibility text. This is orientation, never a diagnosis.

For EACH trial you are given (with its id, title and eligibility text):
- Pick the 3 or 4 MOST decisive eligibility points (key inclusion or exclusion criteria, plus age or sex when they matter).
- Rewrite each as a very short, plain-language label a non-medical person understands (max ~6 words, no jargon dump).
- Mark each with a status, comparing to the patient profile:
    "met"     = the patient clearly satisfies it,
    "unmet"   = the patient clearly does NOT satisfy it,
    "unknown" = we do not have this information about the patient (most common),
    "na"      = not applicable to this patient.
- Give an overall confidence from 0 to 100 that this patient could be eligible (higher = more of the key points look met or plausible; lower if something looks unmet).

Hard rules:
- Use ONLY the ids given. Do not invent criteria that are not in the eligibility text.
- Be honest: if the eligibility text is thin, use "unknown" and a modest confidence.
- Output STRICT JSON only, no markdown, no stars, no extra text:
{"trials": [{"id": "...", "confidence": 70, "criteria": [{"label": "Adults 18 to 65", "status": "met"}, {"label": "Type 2 diabetes", "status": "unknown"}]}]}
"""


async def eligibility(request_text: str, patient: dict | None,
                      trials: list[dict],
                      lang_directive: str | None = None) -> dict:
    """Analyse d'eligibilite par critere sur les essais deja choisis.
    Retourne {id: {"confidence": int, "criteria": [{"label","status"}]}}."""
    import json as _json
    if not trials:
        return {}
    prof = []
    if patient:
        if patient.get("age") not in (None, ""):
            prof.append(f"age {patient['age']}")
        if patient.get("sex"):
            prof.append(str(patient["sex"]))
    profile = ", ".join(prof) if prof else "unknown"
    slim = [{"id": t.get("nct_id") or t.get("id"),
             "title": (t.get("title") or "")[:120],
             "eligibility": (t.get("criteria") or "")[:900]} for t in trials]
    payload = (
        "Patient profile: " + profile +
        "\n\nWhat the patient is looking for:\n" + (request_text or "").strip()[:400] +
        "\n\nTrials to assess:\n" + _json.dumps(slim, ensure_ascii=False)
    )
    m = await complete(
        [{"role": "user", "content": payload}],
        max_tokens=1600, lang_directive=lang_directive, system_override=ELIG_SYSTEM,
    )
    if not m:
        return {}
    d = _parse_json(m.get("content") or "")
    out: dict = {}
    for t in (d or {}).get("trials", []) if isinstance(d, dict) else []:
        tid = t.get("id")
        if not tid:
            continue
        crits = []
        for cr in (t.get("criteria") or [])[:4]:
            lab = clean(str(cr.get("label") or "")).strip()
            st = str(cr.get("status") or "unknown").lower().strip()
            if st not in ("met", "unmet", "unknown", "na"):
                st = "unknown"
            if lab:
                crits.append({"label": lab[:60], "status": st})
        conf = t.get("confidence")
        try:
            conf = max(0, min(100, int(conf)))
        except Exception:
            conf = None
        out[tid] = {"confidence": conf, "criteria": crits}
    return out


EXTRACT_SYSTEM = """From the whole conversation, identify what the patient is looking for, for a clinical-trial search. Output the medical condition and key symptoms in STANDARD ENGLISH. Normalize whatever the patient expressed (any language, everyday words, slang, a mentioned drug, a body part, or an indirect clue) into standard medical English, without assuming a specific disease: stay faithful to what was actually said. Include a location only if the patient named one. If nothing medical was given, return empty fields.
Output STRICT JSON only, no markdown, no extra text:
{"condition": "standard english condition or empty", "symptoms": ["english symptom", "..."], "location": "country/city in english or empty"}
"""


async def extract_terms(convo_text: str) -> dict:
    """Filet de securite cross-langue : deduit condition/symptomes/lieu en anglais
    depuis toute la conversation, quand le modele appelle la recherche sans condition."""
    if not (convo_text or "").strip():
        return {}
    m = await complete(
        [{"role": "user", "content": convo_text[-1800:]}],
        max_tokens=220, system_override=EXTRACT_SYSTEM,
    )
    if not m:
        return {}
    d = _parse_json(m.get("content") or "")
    if not isinstance(d, dict):
        return {}
    return {
        "condition": (d.get("condition") or "").strip(),
        "symptoms": [str(s).strip() for s in (d.get("symptoms") or []) if str(s).strip()][:6],
        "location": (d.get("location") or "").strip(),
    }


def _parse_json(text: str) -> dict | None:
    """Extrait un objet JSON {intro, picks} d'une reponse, tolerant."""
    import json as _json
    if not text:
        return None
    t = re.sub(r"```(?:json)?", "", text)  # retire les fences markdown
    # on cherche le fragment { ... } contenant "picks"
    s = t.find("{")
    e = t.rfind("}")
    if s == -1 or e == -1 or e <= s:
        return None
    frag = t[s:e + 1]
    for attempt in (frag, frag.replace("\n", " "), frag[:frag.rfind("}") + 1]):
        try:
            d = _json.loads(attempt)
            if isinstance(d, dict):
                return d
        except Exception:
            continue
    # Recuperation d'un JSON tronque : on reconstruit intro + picks complets a la main
    salv = _salvage(t)
    return salv


def _salvage(text: str) -> dict | None:
    """Extrait intro + les objets pick complets d'une reponse JSON tronquee/bruitee."""
    import json as _json
    out: dict = {}
    mi = re.search(r'"intro"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if mi:
        try:
            out["intro"] = _json.loads('"' + mi.group(1) + '"')
        except Exception:
            out["intro"] = mi.group(1)
    picks = []
    # chaque pick complet : {"id": "...", "reason": "..."} meme si le tableau est coupe apres
    for pm in re.finditer(
        r'\{\s*"id"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"reason"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}', text):
        rid, reason = pm.group(1), pm.group(2)
        try:
            reason = _json.loads('"' + reason + '"')
        except Exception:
            pass
        picks.append({"id": rid, "reason": reason})
    if picks:
        out["picks"] = picks[:5]
    if out:
        out.setdefault("picks", [])
        return out
    return None


def parse_search(reply: str) -> tuple[str, dict | None]:
    """Detecte la directive SEARCH_QUERY. Retourne (texte_visible, {symptoms, location} | None)."""
    m = SEARCH_RE.search(reply or "")
    if not m:
        return clean(reply), None
    symptoms = (m.group(1) or "").strip()
    location = (m.group(2) or "").strip()
    visible = SEARCH_RE.sub("", reply).strip()
    return clean(visible), {"symptoms": symptoms, "location": location}
