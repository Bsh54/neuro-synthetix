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
- Collect the key facts progressively: main symptom, how long, associated signs, and when useful the age, the sex, and the location.
- Keep a running sense of how confident you are about the likely area.
THRESHOLD TO CONCLUDE: as soon as you have a confident enough picture (a likely condition area, plus ideally the location and, when it matters, age and sex), STOP asking and call the search tool. Do not keep the person waiting once you can act, and never ask more than a few questions in a row.
After results are shown, if the person adds information (age, sex, duration, location, another symptom), treat it as a REFINEMENT of the same topic already discussed: keep the condition and symptoms from earlier in the conversation and search again with the fuller picture. Never ask them to restate a condition they already implied. Always use the whole conversation history for context.

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
    m = await complete(
        [{"role": "user", "content": payload_msg}],
        max_tokens=1800, lang_directive=lang_directive, system_override=RERANK_SYSTEM,
    )
    if not m:
        return None
    return _parse_json(m.get("content") or "")


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
