# ADR-001 : Choix du modèle LLM pour la génération de quiz

**Statut** : Accepté
**Date** : 30 juin 2026
**Décideurs** : Équipe Groupe 30 (Keziah PERFILLON - Benchmark, Nick BEKOLO - documentation)

---

## 1. Contexte

Lors de la phase de test J2, un bêta-testeur a signalé une latence de génération de quiz **inacceptable de 45 secondes**, là où l'expérience utilisateur cible impose un délai inférieur à 15 secondes (critère d'acceptation du MVP : génération en moins de 60 secondes dans le cas nominal, avec un objectif confortable sous 15s pour une expérience fluide).

Le modèle par défaut du kit (**Llama 3.1 8B**) montre une latence médiane de **46.2 secondes**, bien au-delà du seuil acceptable, malgré une excellente qualité de génération (4.6/5).

La contrainte RGPD impose un traitement **local et souverain** des données scolaires : aucune donnée de cours ne doit quitter l'infrastructure (cf. différenciation produit EduTutor IA face aux concurrents utilisant des API cloud hors UE).

**Problème reformulé en une phrase** : *On veut réduire la latence médiane de génération de quiz de 46.2s à moins de 15s, sans sacrifier le traitement local des données ni une qualité de questions acceptable (≥ 3.5/5).*

---

## 2. Options envisagées

| Option | Latence p50 | Latence p95 | Qualité /5 | RAM/VRAM | RGPD |
|--------|-------------|-------------|------------|----------|------|
| **A. Ne rien changer** (Llama 3.1 8B) | 46.2s | 54.8s | 4.6/5 | ~5.8 Go | 🟢 Conforme |
| **B. Llama 3.2 3B** | 12.4s | 17.2s | 3.6/5 | ~2.2 Go | 🟢 Conforme |
| **C. Phi-3 Mini 3.8B** | 14.8s | 21.5s | 3.8/5 | ~2.5 Go | 🟢 Conforme |
| **D. Gemini 1.5 Flash (Cloud)** | 3.2s | 4.9s | 4.3/5 | 0 Go | 🔴 Hors UE |

**Méthodologie** : 5 runs par modèle, document de référence identique (cours d'algorithmie Master 2, ~4800 mots), cache VRAM/RAM vidé avant chaque série, température fixée à 0.4. Médiane (p50) et 95e percentile (p95) calculés plutôt que la moyenne.

---

## 3. Décision retenue

Nous retenons l'**option B : Llama 3.2 3B** comme modèle par défaut pour la génération de quiz.

---

## 4. Justification

- **Llama 3.1 8B (option A)** est exclu : latence p50 de 46.2s, soit 3x au-dessus du seuil acceptable de 15s. Inutilisable en production malgré sa qualité supérieure.
- **Gemini 1.5 Flash (option D)** est exclu malgré ses performances excellentes : il enverrait les documents de cours (données scolaires, potentiellement données d'élèves mineurs) vers des serveurs hors UE, ce qui viole l'invariant non-négociable de conformité RGPD du projet.
- **Phi-3 Mini (option C)** est une alternative valide (14.8s, qualité légèrement supérieure à B) mais se rapproche dangereusement du seuil de 15s, laissant peu de marge pour absorber une charge serveur plus élevée en production.
- **Llama 3.2 3B (option B)** offre le meilleur compromis : un gain de vitesse de **3.7x** par rapport au modèle par défaut, une marge confortable sous le seuil des 15s (12.4s médiane, 17.2s p95), une empreinte mémoire réduite (2.2 Go vs 5.8 Go, libérant des ressources serveur), et une conformité RGPD totale.

La baisse de qualité observée (3.6/5 vs 4.6/5) est jugée acceptable et sera compensée par des actions correctives (cf. conséquences).

---

## 5. Conséquences

**Positives**
- Latence médiane divisée par 3.7, sous le seuil utilisateur critique
- Empreinte mémoire réduite de 62%, libère des ressources pour la montée en charge
- Conformité RGPD maintenue à 100%

**Négatives**
- Qualité subjective des questions en baisse (-1.0 point sur 5) : formulations parfois plus simplistes ou répétitives
- Risque accru d'erreurs de format JSON en sortie, nécessitant un prompt système plus robuste

**À surveiller**
- Mettre en place une étape de validation/parsing strict des questions générées (retry automatique en cas de JSON malformé)
- Consolider le prompt système pour limiter les répétitions de formulation
- Réévaluer ce choix si la qualité perçue par les utilisateurs en Sprint Review s'avère insuffisante (possibilité de bascule vers Phi-3 Mini en fallback)
- Documenter ce changement dans le Sprint Backlog (tâches de migration feature-flaggée + tests)

---

*Rédigé par Nick BEKOLO, basé sur le benchmark de Keziah PERFILLON — Perturbation J2, 30 juin 2026*
