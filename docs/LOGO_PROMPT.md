# Neuro-Synthetix — Logo generation prompt (4K / HD)

Use this with any image model (Midjourney, DALL·E, Ideogram, Flux, Gemini Image, etc.).
The mark must contain **NO text, NO letters, NO words** — a pure symbol only.

---

## PRIMARY PROMPT (copy-paste)

```
A modern, minimal startup logo mark for a health-tech company that connects patients to clinical trials. Abstract symbol only, absolutely no text, no letters, no words.

Concept: a bridge made of connected nodes — a small "human" dot on one side linked through a clean network graph to a "care" node on the other side, symbolizing a voice bridge between a patient and the right clinical trial. Blend two ideas subtly: (1) a neural / knowledge-graph constellation of circles joined by thin confident lines, and (2) a gentle speech / sound wave that flows through the connection, hinting at a voice-first assistant.

Style: flat vector, geometric, precise, friendly and trustworthy, medical-grade but warm and human. Balanced negative space, single centered mark, strong silhouette that stays legible at 16px as an app icon and crisp at 4K. Smooth rounded joints, even line weights, subtle depth. Think Stripe / Linear / Notion level of craft — clean, timeless, premium.

Color palette: deep medical teal-green #0E7C66 as the primary, with a soft mint #EAF6F1 highlight, one warm coral accent #E4573B and a single warm amber dot #F0C888 for a spark of humanity. Cohesive, calm, high-contrast.

Composition: the symbol perfectly centered, generous even padding around it, isolated on a pure flat background. Vector illustration, sharp edges, no photographic texture, no gradient noise, no drop shadows, no 3D bevels, no mockups, no watermark.

Ultra high resolution, 4K, crisp, production-ready, transparent-friendly.
```

---

## BACKGROUND VARIANTS (generate all three)

Append ONE of these lines to the primary prompt:

- **On transparent** (for the app / web, preferred):
  `Background: pure transparent (PNG alpha), the mark isolated with clean edges.`
- **On light** (for the site header):
  `Background: solid warm off-white #FAF7F2, flat, no texture.`
- **On brand green** (for the splash / app icon):
  `Background: solid deep teal-green #0E7C66, the mark drawn in mint #EAF6F1 and warm accents, high contrast.`

---

## NEGATIVE PROMPT (for models that support it)

```
text, letters, words, typography, numbers, watermark, signature, caption, tagline,
photorealism, human face, stethoscope cliché, red cross, generic medical cross, pill,
DNA double helix cliché, heartbeat line cliché, gradient banding, noise, grain,
3D render, bevel, heavy drop shadow, mockup, frame, border, busy background, clutter,
low resolution, blurry, jpeg artifacts, distorted, asymmetrical mess
```

---

## TECHNICAL SPECS TO REQUEST / EXPORT

- **Resolution:** 4096 × 4096 px (square), then export the sizes below.
- **Format:** PNG with transparent alpha (master), plus SVG if the tool can.
- **Aspect:** perfectly square, mark centered, ~15% safe padding.
- **Deliverables to hand back to me so I replace it everywhere:**
  - `logo-master.png` — 4096×4096, transparent
  - `logo-1024.png` — app icon (green background variant)
  - `logo-512.png`, `logo-192.png` — PWA / small
  - `favicon.png` — 64×64
  - (optional) `logo.svg`

---

## WHERE IT WILL BE REPLACED (once you send me the generated file)

- `mobile/app.json` → splash + Android/iOS icon
- `mobile/App.js` → splash logo + welcome logo
- `backend/app/static/landing.html` → header + footer brand mark
- `backend/app/static/index.html` → chat header / bot avatar
- `backend/app/static/proof.html` → header
- `README.md` → top banner

Just drop the generated PNG(s) in the repo (or send me the path) and tell me
"remplace le logo" — I will wire them into every surface above.
```
