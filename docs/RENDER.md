# Render Workflow — mise a jour des donnees (Option A)

Ce qu'on met sur Render : **uniquement** le pipeline de donnees (le refresh 12h),
en tant que **Render Workflow**. L'app live reste sur le VPS + Cloudflare (pas de
cold start pour l'app). Le batch, lui, se reveille, travaille, s'eteint : le cold
start de Render est sans impact.

Le workflow (`backend/workflow.py`) :
1. reconstruit la base de connaissances depuis les registres publics
   (ClinicalTrials.gov + Inde, CTIS-EU, ISRCTN),
2. la livre au conteneur de prod du VPS (`docker cp`),
3. declenche `/reload` pour recharger les caches sans redemarrer.

---

## Ce que TU dois faire (une seule fois)

### 1. Compte Render
Cree un compte gratuit sur https://render.com

### 2. Creer le service Workflow
Dans le dashboard Render :
- **New +** -> **Workflow** (beta ; si absent, choisis **Background Worker**).
- **Connect a repository** -> `Bsh54/neuro-synthetix` (repo public).
- **Root Directory** : `backend`
- **Build Command** : `pip install -r requirements-workflow.txt`
- **Start Command** : `python workflow.py`
- Plan : Free.

### 3. Variables d'environnement (onglet Environment du service)
| Cle | Valeur |
|-----|--------|
| `SSH_HOST` | 213.156.135.72 |
| `SSH_USER` | root |
| `SSH_PW` | (le mot de passe du VPS) |
| `RELOAD_URL` | https://neuro.shadrakbessanh.me/reload |
| `RELOAD_TOKEN` | (voir `backend/.env` local, non commite) |

(Le meme `RELOAD_TOKEN` est deja configure cote backend VPS.)

### 4. Lancer / planifier
- **Test** : dans le service, declenche un run de la tache `refresh_knowledge_base`
  depuis le dashboard. Il doit renvoyer `{trial_count, sources, delivery}`.
- **Planification 12h** : cree un **Cron Job** Render (New + -> Cron Job) qui declenche
  la tache toutes les 12h (`0 */12 * * *`), ou garde le cron existant du VPS en secours.

---

## Ce que MOI j'ai deja prepare
- `backend/workflow.py` : le Render Workflow (tache durable + retries + livraison).
- `backend/requirements-workflow.txt` : dependances du service Render.
- Endpoint `POST /reload` sur le backend (protege par `RELOAD_TOKEN`) pour recharger
  la base sans redemarrer.
- Aucune modification risquee de la prod : la livraison se fait par `docker cp`.

## Pour la soumission (track Render)
- URL du service Render (le Workflow) : a coller dans la soumission.
- Montre un run reussi (logs Render) : c'est la preuve qu'on utilise Render Workflows
  pour un vrai pipeline de donnees multi-sources, durable et planifie.
