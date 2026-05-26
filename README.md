# IPSSI_APOCAL_KIT 🚀

[![CI](https://github.com/melafrit/IPSSI_APOCAL_KIT/actions/workflows/ci.yml/badge.svg)](https://github.com/melafrit/IPSSI_APOCAL_KIT/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-indigo)](./CHANGELOG.md)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-amber.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18-cyan.svg)](https://react.dev/)

**Kit de démarrage officiel** pour la semaine immersive **APOCAL'IPSSI 2026** —
projet étudiant **EduTutor IA** : plateforme de révision personnalisée à base
de LLM open source.

> ⚡ **30 % du MVP déjà câblé.** Concentrez-vous sur la logique produit et
> votre réactivité agile, pas sur la plomberie.

---

## 🏗️ Stack

| Couche | Technologie | Version |
|---|---|---|
| Backend | Django + DRF | Python 3.11+ |
| Frontend | React + Vite + TypeScript | React 18 |
| Base de données | PostgreSQL | 16 (Docker) |
| LLM | Ollama + Llama 3.1 8B | Changement libre après ADR |
| Parsing PDF | `pypdf` | — |
| Conteneurisation | Docker + Compose | — |
| API docs | drf-spectacular | Swagger UI auto |

---

## 🚀 Démarrage en 4 commandes

```bash
# 1. Forker ce repo dans le compte de votre équipe, puis cloner
git clone https://github.com/VOTRE-EQUIPE/IPSSI_APOCAL_KIT.git
cd IPSSI_APOCAL_KIT

# 2. Copier la config et lancer les services
cp .env.example .env
docker compose up -d

# 3. Télécharger le modèle LLM (~5 min, à faire UNE fois)
make pull-model

# 4. Insérer les données de test et ouvrir l'app
make seed
open http://localhost:3000      # front React
open http://localhost:8000/api/docs  # Swagger UI
```

> 💡 Prérequis : Docker + Docker Compose, ≥ 8 Go RAM dispos pour Ollama,
> ≥ 5 Go d'espace disque pour le modèle.

---

## 📚 Documentation détaillée

Le dossier [`docs/`](./docs) contient 8 fiches thématiques :

| Fichier | Sujet |
|---|---|
| [00-getting-started.md](./docs/00-getting-started.md) | Setup détaillé + screenshots + troubleshooting 1ʳᵉ démarrage |
| [01-architecture.md](./docs/01-architecture.md) | Diagramme Django ↔ React ↔ Postgres ↔ Ollama + flux d'auth |
| [02-llm-integration.md](./docs/02-llm-integration.md) | Câblage Ollama, changement de modèle, structure du prompt |
| [03-auth.md](./docs/03-auth.md) | Auth Django REST, sessions vs JWT, où ajouter votre logique |
| [04-testing.md](./docs/04-testing.md) | pytest, vitest + tutorial test adversarial (préparation J3) |
| [05-ci-cd.md](./docs/05-ci-cd.md) | GitHub Actions, Conventional Commits, hooks pre-commit |
| [06-troubleshooting.md](./docs/06-troubleshooting.md) | Docker, ports en conflit, Ollama, CORS |
| [07-bonnes-pratiques.md](./docs/07-bonnes-pratiques.md) | ADR, post-mortem, INVEST, MoSCoW + lien cours Agile |

---

## 🛠️ Commandes utiles (Makefile)

```bash
make help          # Liste toutes les cibles
make dev           # Lance tous les services
make down          # Arrête tous les services
make logs          # Logs en temps réel
make pull-model    # Télécharge Llama 3.1 8B (1 fois)
make test          # Lance pytest + vitest
make lint          # black, ruff, eslint, prettier
make ci            # lint + test (cible CI)
make seed          # Insère données de test
make reset-db      # ⚠️ Supprime + recrée la DB
```

---

## 📐 Périmètre attendu (rappel APOCAL'IPSSI)

### MVP must-have — Release 1 (mercredi soir)

| # | Feature |
|---|---|
| F1 | Inscription / connexion (Django Auth) |
| F2 | Saisie cours (PDF ≤ 5 Mo OU texte ≥ 200 caractères) |
| F3 | Génération auto de 10 QCM via Llama 3.1 8B |
| F4 | Soumission + correction auto |
| F5 | Affichage score /10 + détail |
| F6 | Historique persisté par utilisateur |

### Release 2 — Catalogue de pistes (jeudi soir)

Aucune obligatoire — votre Product Owner et votre Story Map décident :
P1 questions ouvertes LLM · P2 dashboard progression · P3 identification lacunes · P4 plan de révision personnalisé · P5 multi-cours · P6 difficulté ajustable · P7 flashcards · P8 export PDF · P9 mode focus lacunes · P10 markdown

---

## 🎓 Cours de référence

Cours Agile/Scrum complet utilisé tout au long de la semaine :
**[mohamedelafrit.com/teaching/Master_Classe_Agile](https://mohamedelafrit.com/teaching/Master_Classe_Agile/cours.html)**

---

## 🌐 Site pédagogique APOCAL'IPSSI

Toutes les informations sur la semaine (déroulement, perturbations, modèles,
FAQ) : **[apocal.mohamedelafrit.com](https://apocal.mohamedelafrit.com)**

---

## 👤 Auteur

**Mohamed Amine EL AFRIT** — [mohamedelafrit.com](https://www.mohamedelafrit.com)
GitHub : [@melafrit](https://github.com/melafrit)

## 📄 Licence

**Creative Commons BY-NC-SA 4.0** — voir [LICENSE](./LICENSE)
