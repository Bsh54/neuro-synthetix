# 🧠 NEURO-SYNTHETIX — Plan de Bataille HACKHAZARDS '26

> Pont vocal multilingue entre les patients et les essais cliniques.
> **Positionnement corrigé : on n'établit PAS de diagnostic. On ORIENTE vers des essais cliniques potentiellement pertinents, à valider par un médecin.**

---

## 0. L'idée corrigée (à retenir par cœur)

**Avant (risqué) :** « L'appli écoute tes symptômes → te dit que tu as la Tuberculose → t'envoie à l'essai. »
→ C'est du diagnostic médical = red flag légal + danger patient.

**Après (défendable) :** « L'appli écoute ce que tu ressens dans ta langue → identifie des *mots-clés cliniques* → cherche dans la base publique **ClinicalTrials.gov** les essais qui recrutent des patients avec ce profil, près de chez toi → te présente les résultats + un **disclaimer clair : "Ceci n'est pas un diagnostic. Consulte un médecin pour confirmer ton éligibilité."** »

**On garde TOUTES les fonctionnalités prévues :**
1. Entrée **vocale multilingue** (hindi/tamoul/…) → Sarvam AI (STT)
2. Extraction de **mots-clés cliniques** à partir du texte
3. **Graphe Neo4j** : Symptôme → Condition → Essai → Hôpital → Contact
4. **Filtrage géographique** (essais proches du patient)
5. **Réponse vocale** dans la langue du patient → Sarvam AI (TTS)
6. **App mobile Expo** (React Native)
7. **Backend sur Render**
8. **Visualisation en graphe** (la "toile d'araignée" qui se construit à l'écran)

---

## 1. Alignement avec les critères de jugement (les 7 critères)

| Critère | Comment on marque des points |
|--------|------------------------------|
| Innovation & Originalité | Voix multilingue + graphe d'essais = angle rare |
| Implémentation Technique | Neo4j réel + Sarvam AI réel + déploiement Render live |
| Impact Pratique | Accès santé pour zones rurales/pauvres, barrière langue |
| UX & Design | 1 bouton micro, réponse vocale, graphe animé |
| Exhaustivité & Exécution | **1 démo qui marche à 100%** > 5 features cassées |
| Qualité de la Démo | Vidéo 2 min scénarisée (voir §6) |
| Documentation | README propre + article de blog bonus |

**Tracks visées (1 projet → 4 tracks) :**
- 🟢 **Neo4j Track** (500 $) — le graphe est le cœur
- 🟢 **Sarvam AI Track** (1000 $ crédits) — voix multilingue
- 🟢 **Render Track** (900 $ crédits) — hébergement backend
- 🟢 **Expo** — app mobile
- Thème principal : **HealthTech & Bio Platforms**

---

## 2. Architecture technique

```
┌─────────────────────────────────────────────────────────┐
│  APP MOBILE (Expo / React Native)                        │
│  - Écran accueil : gros bouton micro                     │
│  - Enregistre l'audio                                    │
│  - Affiche le graphe (react-native-svg / webview)        │
│  - Joue la réponse audio (TTS)                           │
└───────────────┬─────────────────────────────────────────┘
                │ HTTPS (audio + langue + géoloc)
                ▼
┌─────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI, déployé sur Render)                   │
│                                                          │
│  1. /voice  → Sarvam AI STT  → texte                     │
│  2. extract → mots-clés cliniques (règles + LLM léger)   │
│  3. /match  → requête Cypher sur Neo4j                    │
│  4. filtre géographique (distance)                       │
│  5. Sarvam AI TTS → audio réponse                        │
│  6. renvoie : {graphe JSON, texte, audio_url}            │
└───────────────┬─────────────────────────────────────────┘
                │ Bolt protocol
                ▼
┌─────────────────────────────────────────────────────────┐
│  NEO4J (AuraDB gratuit ou conteneur)                     │
│  Nœuds : (:Symptom) (:Condition) (:Trial) (:Hospital)    │
│  Rels  : (Symptom)-[:INDICATES]->(Condition)             │
│          (Condition)-[:STUDIED_BY]->(Trial)              │
│          (Trial)-[:LOCATED_AT]->(Hospital)               │
│  Données : import depuis ClinicalTrials.gov API (public) │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Structure de dossiers cible

```
neuro-synthetix/
├── docs/
│   ├── PLAN.md            ← ce fichier
│   ├── ARCHITECTURE.md
│   └── DEMO_SCRIPT.md     ← script vidéo 2 min
├── backend/
│   ├── app/
│   │   ├── main.py        (FastAPI)
│   │   ├── config.py      (clés API via env)
│   │   ├── sarvam.py      (STT + TTS)
│   │   ├── extract.py     (texte → mots-clés cliniques)
│   │   ├── graph.py       (Neo4j : requêtes Cypher)
│   │   ├── geo.py         (filtrage distance)
│   │   └── ingest.py      (import ClinicalTrials.gov → Neo4j)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example       (JAMAIS de vraies clés commit)
├── mobile/                (app Expo)
│   ├── App.js
│   ├── screens/
│   └── package.json
├── .gitignore            (.env, node_modules, .venv)
└── README.md
```

---

## 4. Roadmap en phases (chaque phase = démo qui marche)

### Phase 1 — Fondations backend (base minimale qui répond)
- [ ] FastAPI + endpoint `/health`
- [ ] Connexion Neo4j (AuraDB gratuit)
- [ ] Schéma du graphe + contraintes
- [ ] `.env.example` + `.gitignore` propre

### Phase 2 — Données réelles
- [ ] `ingest.py` : récupérer ~50 essais depuis ClinicalTrials.gov API
- [ ] Peupler Neo4j : Symptom → Condition → Trial → Hospital
- [ ] Endpoint `/match?keywords=...&lat=...&lon=...`

### Phase 3 — La voix (Sarvam AI)
- [ ] `sarvam.py` : STT (audio → texte hindi)
- [ ] `extract.py` : texte → mots-clés cliniques
- [ ] TTS (texte réponse → audio hindi)
- [ ] Endpoint `/voice` bout-en-bout

### Phase 4 — Mobile (Expo)
- [ ] Écran accueil + bouton micro
- [ ] Enregistrement audio → POST backend
- [ ] Affichage graphe + lecture audio réponse

### Phase 5 — Déploiement & polish
- [ ] Backend live sur **Render**
- [ ] README + captures
- [ ] Article blog (Dev.to / Medium) → **bonus**
- [ ] Badge social partagé par chaque membre → **bonus**

### Phase 6 — Démo
- [ ] Vidéo 2 min scénarisée
- [ ] Repo GitHub public propre
- [ ] Soumission avant le **30 juin 2026**

---

## 5. Règle d'or du scope (anti-échec n°1)

> **On livre 1 maladie, 1 langue (hindi), 1 région (ex. Delhi) qui marche À 100%,
> avant d'élargir.** Une démo parfaite sur un cas bat 5 cas bancals.

Cas de démo choisi : **Tuberculose** (symptômes fièvre + toux + perte de poids),
essais réels autour de Delhi (AIIMS). Données publiques, vérifiables.

---

## 6. Script de la vidéo démo (2 min)

1. (0:00) Écran d'accueil épuré, un bouton micro.
2. (0:15) On parle en hindi : *"J'ai de la fièvre depuis 3 semaines et je tousse la nuit."*
3. (0:30) L'app transcrit → extrait les mots-clés → le **graphe se construit à l'écran**.
4. (0:50) Résultat : Essai TB à AIIMS Delhi + contact + **disclaimer médical visible**.
5. (1:10) L'app **parle en hindi** : *"Nous avons trouvé un essai près de chez vous. Consultez un médecin pour confirmer."*
6. (1:30) On montre : Neo4j (graphe réel), Sarvam AI (voix), Render (live URL).
7. (1:50) Punchline : *"Du village au laboratoire, dans ta langue, en 2 secondes."*

---

## 7. Sécurité & secrets (NON négociable)

- ❌ Ne JAMAIS commit `serveurs-ssh.md`, mot de passe VPS, clé Gemini/Sarvam.
- ✅ Toutes les clés en variables d'environnement (Render dashboard + `.env` local ignoré).
- ✅ `.gitignore` inclut `.env`, `.venv/`, `node_modules/`.
- ⚠️ RAPPEL : la clé API et le mot de passe root dans `serveurs-ssh.md` doivent être **révoqués/changés** car ils ont été écrits en clair.

---

## 8. Prochaine action

Valider ce plan → puis **Phase 1** : squelette FastAPI + connexion Neo4j + `.gitignore`.
