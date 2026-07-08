# NEURO-SYNTHETIX — Design de la recherche IA (RAG re-ranking)

> But : faire de la recherche d'essais notre **point fort**. Précise, explicable,
> honnête (zéro bruit, zéro hallucination). Validé avant de coder.

---

## 1. Objectif

Quand un patient décrit sa situation (symptômes, maladie, lieu), le système doit :
1. Retrouver de **vrais** essais candidats dans la base (5 000+),
2. Laisser **l'IA juger la pertinence** de chaque candidat et **classer**,
3. Répondre en **expliquant pourquoi** chaque essai retenu correspond,
4. Ne **jamais** proposer un essai hors-sujet ni inventer.

---

## 2. État actuel (et ses limites)

Flux : DeepSeek (tool call) -> extract mots-clés -> Neo4j (24 conditions) + kb_search
(sous-chaîne) -> fusion -> résumé rendu au modèle.

Limites :
- Matching par **sous-chaîne** = bruit (un mot présent ≠ pertinent).
- Le modèle **ne voit pas** les essais candidats : il ne peut ni filtrer ni juger.
- **Éligibilité** (âge/sexe/stade) ignorée.
- Deux systèmes (Neo4j vs grande base) déconnectés.

---

## 3. Architecture cible : Retrieve → Re-rank (IA) → Respond

```
Patient (n'importe quelle langue)
        │  (hindi -> anglais via API traduction)
        ▼
DeepSeek (tool calling)  ──► appelle search(symptoms, condition, location, age?, sex?)
        │
        ▼
[ ÉTAPE A — RETRIEVAL ]  (rapide, déterministe, backend)
  - Recherche dans la grande base (5000) :
      • filtre pays si location
      • score lexical amélioré : condition exacte (x3) > mot dans conditions (x2) > mot dans blob (x1)
      • ne garde que RECRUITING
  - Retourne un CANDIDAT SET (~20 à 30 essais), champs compacts :
      id, title, conditions, brief eligibility (age/sex), country/city, url
        │
        ▼
[ ÉTAPE B — RE-RANK PAR L'IA ]  (2e appel DeepSeek, JSON strict)
  - On donne le candidat set au modèle avec la demande patient.
  - Consigne : sélectionne les essais VRAIMENT pertinents (max ~5),
    classe-les, et pour chacun donne une phrase "pourquoi ça colle".
  - Le modèle NE PEUT choisir QUE dans la liste fournie (grounding).
  - Sortie : JSON [{id, reason}] -> on ré-associe aux essais réels.
        │
        ▼
[ ÉTAPE C — RÉPONSE ]
  - Message patient (langue du patient) : intro courte + les essais retenus,
    chacun avec sa raison, + rappel "pas un diagnostic".
  - Cartes d'essais (réelles) + graphe seulement si relations Neo4j.
```

---

## 4. Contrats d'API (interne)

### search(...) — l'outil DeepSeek (inchangé en surface)
`{ symptoms: string[], condition?: string, location?: string, age?: number, sex?: "male"|"female" }`

### Étape A — retrieval (nouveau module `retrieval.py`)
`retrieve(terms, condition, country, limit=25) -> list[Candidate]`
```
Candidate = {
  id, title, conditions:[...], country, city,
  min_age, max_age, sex, url, lex_score
}
```

### Étape B — re-rank (nouveau, dans `deepseek.py`)
Entrée modèle (JSON) : la demande + la liste des candidats (id + title + conditions + eligibility).
Sortie modèle (JSON strict) :
```
{ "picks": [ { "id": "...", "reason": "one plain sentence" } ], "note": "optional" }
```
- Si `picks` vide -> "aucun essai vraiment pertinent" (honnête).
- On valide chaque id contre le candidat set (drop les ids inventés).

---

## 5. Éligibilité (léger, étape B assistée)

On ne fait PAS un moteur de règles complet. On passe au modèle l'âge/sexe requis
de chaque candidat + (si connus) l'âge/sexe du patient, et on lui demande d'écarter
les incompatibilités évidentes. Rigueur suffisante pour un outil d'orientation,
avec toujours le disclaimer "à confirmer avec un médecin".

---

## 6. Neo4j : rôle clarifié

- **N'est plus** le moteur de matching principal.
- Sert à **dessiner le graphe** des essais finalement retenus
  (patient -> symptômes -> condition -> essai -> hôpital), quand les relations existent.
- La grande base (5000) devient la **source unique** de vérité pour le matching.

---

## 7. Coût & latence (on reste économe)

- Tour "question" (pas de recherche) : 1 appel DeepSeek.
- Tour "recherche" : 2 appels (décision d'outil + re-rank). Le re-rank reçoit ~25
  candidats compacts (~1.5k tokens) -> maîtrisé.
- Retrieval = pur Python en cache (index de la base), quasi instantané.
- Garde-fous : max ~25 candidats, sortie JSON courte, pas d'appel sur vieux tours.

---

## 8. Anti-hallucination (garanties)

1. Le modèle ne choisit QUE dans la liste de candidats réels.
2. On revalide chaque id renvoyé ; tout id inconnu est ignoré.
3. Si 0 pick -> on dit honnêtement qu'on n'a rien trouvé de pertinent.
4. Les cartes affichées proviennent des essais réels ré-associés (jamais du texte du modèle).

---

## 9. Plan d'implémentation (étapes livrables)

- [ ] **Étape 1** — `retrieval.py` : candidat set + ranking lexical amélioré (condition exacte, RECRUITING, pays). Remplace l'usage direct de kb_search dans /chat.
- [ ] **Étape 2** — re-rank IA : 2e appel DeepSeek en JSON strict, validation des ids, ré-association.
- [ ] **Étape 3** — réponse : message + raisons par essai (dans la langue du patient), cartes réelles, graphe conditionnel.
- [ ] **Étape 4** — éligibilité assistée (âge/sexe) + captation de l'âge/sexe si le patient les donne.
- [ ] **Étape 5** — tests : Bénin, cancer/pays, maladie rare, patient vague, hindi. Vérifier zéro bruit, zéro hallucination, cohérence carte/chat.

---

## 10. Critères de réussite

- Une recherche ne renvoie que des essais **pertinents** (plus de « Cancer » pour « fièvre »).
- Chaque essai retenu vient avec **une raison** compréhensible.
- « trials in X » (pays) marche et est **cohérent avec la carte**.
- Rien d'inventé ; « rien trouvé » est dit honnêtement.
- Latence acceptable (< ~4 s pour un tour avec recherche).
