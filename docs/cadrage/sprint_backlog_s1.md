# Sprint Backlog — Sprint 1
**Projet** : EduTutor IA  
**Équipe** : Helena MOUGAMMADALY, Julien CANTAU, Kevin TCHIKAYA, Yanis MEDJADI, Keziah PERFILLON, Mohamed Abdelmalek DORBANI, Nick BEKOLO  
**Sprint** : S1 — Lundi 29/06 → Mardi 30/06/2026  
**Deadline cadrage** : Lundi 29/06 à 13h00  
**Rédigé par** : Nick BEKOLO  

---

## 🎯 Objectif du Sprint 1

Livrer les 7 artefacts de cadrage avant 13h00, faire l'inventaire du code existant l'après-midi, et démarrer le développement de US-01 (inscription/connexion) et US-02 (upload de cours).

---

## 📋 Kanban

| ID | Tâche | Catégorie | Responsable | Estimation | Priorité | Deadline | Statut |
|----|-------|-----------|-------------|------------|----------|----------|--------|
| T-01 | Product Vision Board | 🔵 Cadrage | Keziah PERFILLON | 1h | MUST | Lundi 13h | 📋 À faire |
| T-02 | Personas | 🔵 Cadrage | Helena MOUGAMMADALY | 1h30 | MUST | Lundi 13h | 📋 À faire |
| T-03 | Customer Journey Map | 🔵 Cadrage | Mohamed A. DORBANI | 1h30 | MUST | Lundi 13h | 📋 À faire |
| T-04 | Story Map | 🔵 Cadrage | Kevin TCHIKAYA | 1h30 | MUST | Lundi 13h | 📋 À faire |
| T-05 | Release Planning | 🔵 Cadrage | Yanis MEDJADI | 1h | MUST | Lundi 13h | 📋 À faire |
| T-06 | Product Backlog (MoSCoW + INVEST) | 🔵 Cadrage | Julien CANTAU | 2h | MUST | Lundi 13h | 📋 À faire |
| T-07 | Sprint Backlog S1 | 🔵 Cadrage | Nick BEKOLO | 1h | MUST | Lundi 13h | 📋 À faire |
| T-08 | Cloner le kit GitHub et lancer Docker Compose | 🟠 Inventaire | Toute l'équipe | 30min | MUST | Lundi après-midi | 📋 À faire |
| T-09 | Tester F1 (auth : inscription, connexion, reset) | 🟠 Inventaire | Helena MOUGAMMADALY | 45min | MUST | Lundi après-midi | 📋 À faire |
| T-10 | Tester F2/F3 (upload PDF + génération quiz Ollama) | 🟠 Inventaire | Kevin TCHIKAYA | 45min | MUST | Lundi après-midi | 📋 À faire |
| T-11 | Tester F4/F5 (correction + score) | 🟠 Inventaire | Julien CANTAU | 45min | MUST | Lundi après-midi | 📋 À faire |
| T-12 | Tester F6 (historique des quizz) | 🟠 Inventaire | Nick BEKOLO | 30min | MUST | Lundi après-midi | 📋 À faire |
| T-13 | Documenter l'inventaire (fait / à finir / à jeter) | 🟠 Inventaire | Yanis MEDJADI | 1h | MUST | Lundi après-midi | 📋 À faire |
| T-14 | Vérifier/finir endpoint /api/register Django | 🟢 Dev US-01 | À définir | 2h | MUST | Mardi | 📋 À faire |
| T-15 | Vérifier email de validation (Brevo ou console) | 🟢 Dev US-01 | À définir | 1h | MUST | Mardi | 📋 À faire |
| T-16 | Vérifier/finir formulaire React Login | 🟢 Dev US-01 | À définir | 1h30 | MUST | Mardi | 📋 À faire |
| T-17 | Tester et corriger le flow reset password | 🟢 Dev US-01 | À définir | 1h | MUST | Mardi | 📋 À faire |
| T-18 | Vérifier page profil (modifier + supprimer compte) | 🟢 Dev US-01 | À définir | 1h | MUST | Mardi | 📋 À faire |
| T-19 | Vérifier validation PDF ≤ 5 Mo côté Django | 🟣 Dev US-02 | À définir | 1h30 | MUST | Mardi | 📋 À faire |
| T-20 | Vérifier validation texte ≥ 200 caractères | 🟣 Dev US-02 | À définir | 1h | MUST | Mardi | 📋 À faire |

---

## 📊 Récapitulatif

| Catégorie | Nb tâches | Estimation |
|-----------|-----------|------------|
| 🔵 Cadrage | 7 | ~9h30 |
| 🟠 Inventaire | 6 | ~4h30 |
| 🟢 Dev US-01 | 5 | ~6h30 |
| 🟣 Dev US-02 | 2 | ~2h30 |
| **TOTAL** | **20** | **~23h** |

---

## ✅ Définition of Done

Une tâche est **Done** quand :
- Le code est commité sur GitHub avec un message Conventional Commits
- La fonctionnalité est testée manuellement
- Elle fonctionne en local via Docker Compose
- Elle a été revue par un autre membre de l'équipe

---

## ⚠️ Risques identifiés

| Risque | Impact | Mitigation |
|--------|--------|-----------|
| Ollama lent ou non installé | Élevé | Tester Docker dès lundi après-midi |
| Code existant instable | Élevé | Inventaire en priorité absolue |
| Perturbation J1 à 14h | Moyen | Prévoir du buffer dans le planning |
| Conflits Git entre membres | Moyen | Branches par feature, PR avant merge |
