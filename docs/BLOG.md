# Blog article — Neuro-Synthetix (HackHazards '26)

Ci-dessous : l'article prêt à copier-coller, puis OÙ et COMMENT le publier.
Écrit en anglais (meilleure portée + les juges lisent l'anglais).

---

## OÙ PUBLIER (plateformes acceptées par HackHazards '26)

Publie sur **au moins une** de ces trois (toutes gratuites) :

1. **Hashnode** — https://hashnode.com (le plus « dev », mis en avant par les hackathons)
2. **Dev.to** — https://dev.to
3. **Medium** — https://medium.com

Conseils :
- Titre accrocheur (voir ci-dessous).
- Ajoute une image de couverture (une capture de l'app ou de la carte des labos).
- Mets des **tags** : `healthtech`, `ai`, `neo4j`, `hackathon`, `hackhazards`.
- Colle le **lien du repo GitHub** et le **lien live** (https://neuro.shadrakbessanh.me).
- Après publication, tu déclares l'URL dans le **formulaire de points bonus** du dashboard HackHazards.
- Chaque membre partage aussi son **badge** sur un réseau social (2e tâche bonus).

Titre suggéré :
> **Neuro-Synthetix: a voice bridge from a village to the world's clinical trials**

Sous-titre :
> How we built a multilingual, voice-first assistant that connects patients to real
> recruiting clinical trials — with Neo4j, Sarvam AI, and an AI re-ranking search.

---

## L'ARTICLE (copier-coller)

### The problem: two worlds that never meet

On one side, a patient in a village. Fever for three weeks, a cough, weight loss.
The local doctor is out of options, the big hospitals are far and expensive, and the
patient speaks Hindi, not medical English.

On the other side, somewhere in the world, a research team is urgently looking for
patients with exactly that profile for a clinical trial. Free for the patient. Yet the
two sides have no idea the other exists.

The information that could bridge them is public — clinical trial registries are open —
but it is fragmented across countries, written in English, and buried in eligibility
criteria no ordinary person will read.

**Neuro-Synthetix** closes that gap. You describe how you feel, by voice or text, in your
own language, and it finds real trials that are recruiting, near you. It never diagnoses:
it orients toward trials and always reminds you to confirm with a doctor.

Live: https://neuro.shadrakbessanh.me

### What it does, end to end

1. A conversational AI leads a short, clinician-like conversation. It understands any
   wording — everyday words, slang, a drug name, a body part, a vague clue, another
   language, a misspelling — and turns it into clean clinical search terms.
2. It asks focused, progressive questions when needed, and searches as soon as it has a
   confident picture.
3. It searches a base of thousands of real trials, unified from several public registries.
4. An AI re-ranking step keeps only the genuinely relevant trials and explains, in one
   sentence, why each fits. It can only pick from real candidates, so it never invents a trial.
5. It takes age and sex into account to drop trials the patient cannot join.
6. Every result shows a clear "how to proceed" path (reference, see your doctor, contact
   the site, eligibility check, participation is free) plus the official link.
7. In Hindi, speech-to-text and text-to-speech run through Sarvam AI, and a graph
   visualizes the care pathway.

### The tech stack

- **Backend:** FastAPI (Python), Docker.
- **Graph:** Neo4j (symptom → condition → trial → hospital).
- **AI:** DeepSeek for the conversation, tool calling, and RAG re-ranking; Sarvam AI for
  Hindi speech-to-text and text-to-speech; a translation layer used only for Hindi.
- **Data:** a unified clinical-trial knowledge base built from ClinicalTrials.gov (global
  and a dedicated India pull), CTIS (EU), and ISRCTN — refreshed every 12 hours.
- **Frontend:** a lightweight chat, a voice mode, a world map of research sites, and a
  proof page, all multilingual (English, French, Hindi).

### Partner tracks we used

- **Neo4j:** the graph is the heart of the visualization. We model symptoms, conditions,
  trials and hospitals as nodes and draw the patient's care pathway from the results.
- **Sarvam AI:** the whole promise is "in your language." Sarvam powers real Hindi
  speech-to-text (saarika) and text-to-speech (bulbul), so a patient can simply speak.
- **Render:** the 12-hour data-refresh pipeline is implemented as a Render Workflow
  (a durable, retried, scheduled job) that rebuilds the knowledge base from the registries.
- **Expo:** the mobile app, so the tool reaches a low-end Android phone in a village.

### How the search actually works (the interesting part)

Naive keyword search is noisy: searching "fever cough" can surface a cancer trial just
because a word matched. And a plain model can hallucinate trials that do not exist.

So we split the search into two stages, RAG-style:

1. **Retrieval (fast, deterministic):** we pull ~25 real candidate trials from the base,
   ranked by exact-condition match first, then keyword, filtered by country if the patient
   gave a location. This is the safety net.
2. **Re-ranking (the AI layer):** we hand those real candidates to DeepSeek, which selects
   only the genuinely relevant ones, ranks them, and writes one sentence explaining why each
   fits. The model can only choose from the ids we gave it, and we re-validate every id it
   returns — so it is mathematically impossible for it to invent a trial.

If nothing fits in the requested country, the AI honestly says so and offers the same kind
of trial elsewhere, naming the country. If the model's output fails to parse, we fall back
to the ranked candidates, so the user never hits an empty screen.

### Challenges we hit (and fixed)

- **Cost of a reasoning model:** DeepSeek's re-ranking is a reasoning model, so we had to
  size the token budget generously enough for it to reason and still return valid JSON,
  while keeping searches to two model calls.
- **Honest failure vs a silent bug:** early on, a country filter dropped valid trials, so
  the app said "no trials in Benin" while the map showed a site there. We traced it, made
  the country match authoritative, and the map and the assistant now tell the same truth.
- **Multilingual without waste:** we translate only for Hindi; English and French are
  handled natively by the model, which is faster and cleaner.
- **Voice for people who can't read:** the entry screen shows each language in its own
  script and a big "speak or write" choice with icons, so choosing needs no reading.
- **Clean text:** we strip all markdown and HTML entities, because a patient should read
  plain sentences, not asterisks or `&#39;`.

### What is real, and what we are honest about

Every trial we show keeps its official reference (NCT, CTIS, or ISRCTN) so anyone can
verify it at the source. Nothing is generated by the AI. Detailed eligibility is richer
for ClinicalTrials.gov entries than for others, and some registries (like India's CTRI)
block automated access — so we surface Indian trials through ClinicalTrials.gov's India
data instead. We would rather be honest about a limit than fake a number.

### On your phone (Expo)

The same assistant runs as a native mobile app built with Expo / React Native — same
backend, same voice, same real trials. Install **Expo Go**, then scan this QR code
(or open the link inside Expo Go):

![Scan with Expo Go](https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=8&data=exp://ncarnci-bsh54-8081.exp.direct)

`exp://ncarnci-bsh54-8081.exp.direct`

### Try it

- Live web: https://neuro.shadrakbessanh.me
- Mobile (Expo Go): `exp://ncarnci-bsh54-8081.exp.direct`
- Code: (colle ici le lien de ton repo GitHub)

Neuro-Synthetix is an orientation tool. It does not provide a medical diagnosis and does
not replace a doctor's advice.

---

## Rappel bonus (2 tâches)
1. Publier cet article (Hashnode / Dev.to / Medium) + déclarer l'URL dans le formulaire bonus.
2. Chaque membre partage son badge HackHazards '26 sur un réseau social (LinkedIn/Twitter/Instagram).
