# Sprint Backlog — Sprint 2
**Projet** : EduTutor IA  
**Équipe** : Helena MOUGAMMADALY, Julien CANTAU, Kevin TCHIKAYA, Yanis MEDJADI, Keziah PERFILLON, Mohamed Abdelmalek DORBANI, Nick BEKOLO  
**Sprint** : S2 — Jeudi 02/07 → Vendredi 03/07/2026  
**Deadline Release 2** : Jeudi 02/07 à 17h45  
**Rédigé par** : Nick BEKOLO  

---

## Objectif du Sprint 2

Livrer la Release 2 avec 3 fonctionnalités prioritaires (a11y + i18n + scale), répondre à la perturbation J4 (retour Mme Lefèvre), et préparer la soutenance vendredi.

---

## Kanban

| ID | Tâche | Catégorie | Responsable | Estimation | Priorité | Deadline | Statut |
|----|-------|-----------|-------------|------------|----------|----------|--------|
| T-01 | Audit RGAA + focus visible & contrastes | a11y | Mohamed A. DORBANI | 8 pts | MUST | Jeu 17h45 | À faire |
| T-02 | Externaliser les textes en fichiers de langue | i18n | Kevin TCHIKAYA | 8 pts | MUST | Jeu 17h45 | À faire |
| T-03 | Paramètre de langue du LLM à la volée | i18n | Kevin TCHIKAYA | 5 pts | SHOULD | Jeu 17h45 | À faire |
| T-04 | Test de charge + cache + autoscaling | scale | Yanis MEDJADI | 13 pts | MUST | Jeu 17h45 | À faire |
| T-05 | Fournisseur LLM de secours (résilience) | risk | Julien CANTAU | 5 pts | COULD | Jeu 17h45 | À faire |
| T-06 | Modèle QuestionReport (signalement erreurs) | J4 | Helena MOUGAMMADALY | 3 pts | MUST | Ven 09h00 | À faire |
| T-07 | Audit qualité 50 questions générées par LLM | J4 | Keziah PERFILLON | 3 pts | MUST | Ven 09h00 | À faire |
| T-08 | Email client réponse à Mme Lefèvre | J4 | Nick BEKOLO | 1 pt | MUST | Ven 09h00 | À faire |
| T-09 | Post-mortem blameless (5 perturbations) | J4 | Nick BEKOLO | 2 pts | MUST | Ven 09h00 | À faire |
| T-10 | Tag Git v1.1.0 + démo vidéo 5 min | Release | Toute l'équipe | 2 pts | MUST | Jeu 17h45 | À faire |
| T-11 | Support soutenance (.pptx ou .pdf) | Soutenance | Toute l'équipe | 3 pts | MUST | Ven matin | À faire |
| T-12 | Mise à jour Sprint Backlog S2 | Gestion Agile | Nick BEKOLO | 1 pt | MUST | Jeu matin | À faire |

---

## Récapitulatif

| Catégorie | Nb tâches | Story Points |
|-----------|-----------|-------------|
| Accessibilité (a11y) | 1 | 8 pts |
| Internationalisation (i18n) | 2 | 13 pts |
| Scalabilité (scale) | 1 | 13 pts |
| Résilience (risk) | 1 | 5 pts |
| Perturbation J4 | 4 | 9 pts |
| Release | 1 | 2 pts |
| Soutenance | 1 | 3 pts |
| Gestion Agile | 1 | 1 pt |
| **TOTAL** | **12** | **54 pts** |

---

## Vélocité Sprint 1 vers Sprint 2

| Sprint | Story Points engagés | Story Points livrés |
|--------|---------------------|---------------------|
| S1 | 8 pts (US-01 + US-02) | 8 pts |
| S2 | 54 pts | En cours |

---

## Définition of Done

Une tâche est Done quand :
- Le code est commité sur GitHub avec un message Conventional Commits
- La fonctionnalité est testée manuellement
- Elle fonctionne en local via Docker Compose
- Elle a été revue par au moins un autre membre de l'équipe

---

## Risques identifiés

| ID | Risque | Catégorie | Probabilité | Impact | Exposition | Priorité | Mitigation |
|----|--------|-----------|-------------|--------|------------|----------|-----------|
| R-01 | Saturation serveur au pic de charge | Scalabilité | 3 | 3 | 9 (Rouge) | MUST | Cache Redis + autoscaling horizontal (HPA) — T-04 |
| R-02 | Rejet plateforme pour non-conformité RGAA | Accessibilité | 2 | 3 | 6 (Rouge) | MUST | Audit axe-core + correction contrastes + navigation clavier — T-01 |
| R-04 | Hallucinations LLM en langue étrangère | Qualité / i18n | 3 | 2 | 6 (Rouge) | SHOULD | Adapter dynamiquement le system prompt avec variable langue — T-03 |
| R-05 | Coût infrastructure cloud hors budget | Financier | 2 | 2 | 4 (Orange) | SHOULD | Alertes facturation + limite instances scaling — T-04 |
| R-03 | Panne ou indisponibilité Ollama | Résilience | 1 | 3 | 3 (Orange) | COULD | File d'attente asynchrone Celery/Redis — T-05 |
| R-06 | Bug affichage mineur interface | UX | 1 | 1 | 1 (Vert) | — | Accepté sans action |

---

*Rédigé par Nick BEKOLO — Sprint Backlog S2 — APOCAL'IPSSI 2026*
