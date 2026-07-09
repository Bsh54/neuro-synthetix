# Neuro-Synthetix — Logo generation prompt (4K / HD)

Use this with any image model (Midjourney, DALL·E, Ideogram, Flux, Gemini Image, etc.).
The mark must contain **NO text, NO letters, NO words** — a pure symbol only.

---

## PRIMARY PROMPT (copy-paste) — vivid, modern, high-impact

```
A bold, vibrant, modern startup app-icon logo mark for a health-tech company that connects patients to clinical trials. Abstract symbol only — absolutely no text, no letters, no words.

Concept: a luminous "connection pulse" — glowing network nodes forming a bridge that arcs from a human spark on one side to a care node on the other, energized by a flowing sound/voice wave running through it (voice-first assistant). It should feel alive, electric and hopeful: a signal traveling, a link lighting up. Iconic and instantly memorable at any size.

Style: premium 2025 app-icon energy. Vivid, high-saturation gradient with real depth and a soft inner glow / light bloom around the nodes, clean crisp edges, dynamic sense of motion. Confident smooth curves, bold rounded geometry, strong central silhouette. Think the polish of Linear / Arc / Framer / modern iOS icons — striking, glossy-clean, luminous, but still refined (not childish, not cluttered).

Color: an energetic gradient flowing from emerald green #10B981 through deep medical teal #0E7C66 into a bright cyan #22D3EE, with a vivid coral-orange spark #FF6B4A and a glowing warm amber node #FFC55C as the human accent. High contrast, radiant, saturated, cohesive.

Lighting & finish: subtle luminous glow, gentle gradient bloom, crisp highlights, a hint of glass-like depth. Balanced negative space, single centered mark, generous even padding, legible as a 16px favicon and stunning at 4K.

Vector-clean shapes, sharp edges, no photographic texture, no noise, no mockup, no watermark, no frame.

Ultra high resolution, 4K, production-ready.
```

### Optional style pushes (add one line if you want a specific direction)
- **Gradient-flat / iOS icon:** `Flat vivid gradient icon, rounded-square friendly, glossy modern, subtle bloom.`
- **Glowing neon-tech:** `Neon glow accents, dark-friendly, electric light trails between the nodes.`
- **3D-lite depth:** `Soft 3D depth, glassy translucent layers, gentle drop light, still icon-clean.`

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
DNA double helix cliché, heartbeat line cliché, banding, noise, grain, jpeg artifacts,
mockup, frame, border, busy background, clutter, dull, flat lifeless colors, muddy,
low resolution, blurry, distorted, asymmetrical mess
```

> Note: we now WANT vivid gradients, glow and depth — so do NOT exclude gradient/glow/3D.
> Only exclude banding/noise (bad gradients), not gradients themselves.

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
