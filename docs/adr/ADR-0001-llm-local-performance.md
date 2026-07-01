# ADR-0001 : Bascule du modèle Ollama par défaut vers Llama 3.2 3B

**Statut** : Accepté
**Date** : 2026-07-01
**Auteur** : Julien CANTAU

## Contexte

La story US-03 impose de générer 10 QCM en moins de 60 secondes. Le modèle local
initial `llama3.1:8b` respecte la souveraineté des données, mais sa latence CPU
peut dépasser l'objectif produit sur un laptop sans GPU.

## Options envisagées

| Option | Latence attendue | Qualité | RAM | Données |
|---|---:|---:|---:|---|
| Garder `llama3.1:8b` | élevée | bonne | ~5 Go | locales |
| Basculer vers `llama3.2:3b` | plus faible | correcte | ~2 Go | locales |
| Basculer vers `phi3:mini` | plus faible | correcte | ~2.3 Go | locales |
| Utiliser Groq/Gemini | très faible | bonne | 0 local | cloud |

## Décision

Le modèle Ollama local par défaut devient `llama3.2:3b`.

## Justification

- Il conserve l'engagement produit "local-first" et évite un transfert cloud.
- Il réduit la RAM et la latence attendue par rapport au modèle 8B.
- Il reste installable avec la commande existante `make pull-model`.
- Le modèle reste configurable via `.env` et via l'admin.

## Conséquences

Positives :
- Démarrage plus accessible sur les machines étudiantes.
- Meilleure probabilité de tenir le seuil de 60 secondes.
- La validation devient mesurable avec `make benchmark-llm`.

Négatives :
- Qualité potentiellement inférieure au 8B sur certains cours complexes.
- Nécessite de surveiller les questions hors-sujet en recette.

À surveiller :
- `make benchmark-llm` doit passer sur la machine de démonstration.
- Si la qualité devient insuffisante, tester `llama3.1:8b` ou un backend cloud
  documenté par un nouvel ADR.
