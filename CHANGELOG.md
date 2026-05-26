# Changelog

Toutes les évolutions notables du kit IPSSI_APOCAL_KIT.

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ·
Versioning : [SemVer](https://semver.org/lang/fr/).

---

## [1.0.0] — 2026-05-26

🎉 **Première release stable du kit de démarrage APOCAL'IPSSI 2026.**

Le kit fournit un embryon fonctionnel (≈30 % du MVP) pour le projet
EduTutor IA, à forker par les équipes le lundi matin de la semaine.

### Ajouté

#### Bootstrap (K0)
- Structure de projet complète : backend, frontend, docker, docs, scripts
- `Makefile` avec 11 cibles documentées
- `docker-compose.yml` avec 4 services
- Scripts shell : `pull-model.sh`, `seed-data.sh`, `reset-db.sh`
- LICENSE CC BY-NC-SA 4.0
- `.env.example` documenté

#### Backend Django (K1)
- Projet Django 5.1 + DRF + drf-spectacular (Swagger)
- App `accounts` : signup, login, logout, me (Token + Session)
- App `llm` : ping endpoint
- App `quizzes` : modèles Quiz + Question, list, detail
- Migration `0001_initial.py` pré-générée
- Commande `python manage.py seed` (user test + 2 quizz exemples)
- pyproject.toml : black + ruff + pytest + coverage configurés
- `docker/backend.Dockerfile`

#### Endpoints LLM (K2)
- Abstraction `LLMClient` (Strategy + Factory pattern)
- `MockLLMClient` déterministe (seed sur hash texte)
- `OllamaLLMClient` avec prompt FR strict + validation post-LLM
- Parsing PDF avec `pypdf` (limite 5 Mo)
- Endpoint `POST /api/llm/generate-quiz/` (PDF ou texte)
- Endpoint `POST /api/quizzes/<id>/answer/` (correction + score)

#### Frontend React (K3)
- React 18 + Vite 6 + TypeScript strict
- Tailwind CSS 3.4 avec palette site (indigo + ambre)
- Pages : Home, Login, Signup, Upload, Quiz, History
- Layout commun + RequireAuth
- AuthContext avec restauration session
- API client axios avec interceptor token + 401 handling
- `docker/frontend.Dockerfile`

#### Outils dev & CI (K4 + K5)
- Pipeline `.github/workflows/ci.yml` (backend + frontend en parallèle)
- Service Postgres sidecar pour les tests backend
- Cache pip et npm
- `LLM_BACKEND=mock` en CI (pas d'appel Ollama)
- `.editorconfig`
- `CONTRIBUTING.md` avec workflow Git, Conventional Commits, DoD
- `.pre-commit-config.yaml` : black, ruff, prettier, conventional-commits

#### Documentation (K6)
- 8 fiches thématiques dans `docs/` (1409 lignes)
- 3 diagrammes Mermaid (architecture, auth, génération)
- Tutorial dédié test adversarial (préparation perturbation J3)
- Templates ADR + Post-mortem blameless prêts à l'emploi

### Tests
- 18 tests pytest (accounts 7, llm 5, quizzes 11)
- Couverture sur les flows critiques (auth, génération mock, correction)

---

## Roadmap (post-1.0.0 — à la main des équipes)

Pas de release planifiée — le kit est un point de départ. Les équipes
forkent et font évoluer selon leur produit.

Pistes ouvertes (catalogue Release 2, non obligatoires) :
- Questions ouvertes LLM-graded
- Dashboard de progression
- Identification automatique des lacunes
- Plan de révision personnalisé
- Multi-cours par utilisateur
- Mode flashcards
- Export PDF
- Niveau de difficulté ajustable

---

[1.0.0]: https://github.com/melafrit/IPSSI_APOCAL_KIT/releases/tag/v1.0.0
