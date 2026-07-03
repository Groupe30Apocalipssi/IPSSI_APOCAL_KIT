# Livrable J4 : Analyse de risques → Backlog

**Projet** : EduTutor IA  
**Équipe** : Équipe 30  
**Livrable** : Perturbation 5 (J4 - Passage à l'échelle & Plateforme d'État) - Axe 2 : Gestion des risques  
**Date** : 02/07/2026  
**Statut** : Version Finale  

---

## 🛡️ 1. Matrice des Risques (Probabilité × Impact)

L'exposition d'un risque est calculée selon la formule :  
$$\text{Exposition} = \text{Probabilité (1 à 3)} \times \text{Impact (1 à 3)}$$

*   **Exposition $\ge$ 6 (Rouge)** : Risques prioritaires (forte exposition) nécessitant une action préventive immédiate planifiée et estimée en Story Points (SP) dans le backlog.
*   **Exposition 3-4 (Orange)** : Risques modérés à surveiller de près.
*   **Exposition $<$ 3 (Vert)** : Risques résiduels acceptés sans action.

| Probabilité ↓ / Impact → | 1 (Faible) | 2 (Moyen) | 3 (Fort) |
| :--- | :--- | :--- | :--- |
| **3 (Élevée)** | | [R-04] Hallucinations du LLM en langue étrangère (Expo: 6) | [R-01] Saturation serveur au pic de charge (Expo: 9) |
| **2 (Moyenne)** | | [R-05] Coût d'infra cloud hors budget (Expo: 4) | [R-02] Rejet de la plateforme pour non-conformité RGAA (Expo: 6) |
| **1 (Faible)** | [R-06] Bug d'affichage mineur de l'interface (Expo: 1) | | [R-03] Panne ou indisponibilité du service Ollama (Expo: 3) |

---

## 🎒 2. Registre des Risques & Actions Préventives dans le Backlog

Nous avons identifié 5 risques principaux liés au pivot technique de la plateforme (passage à l'échelle, accessibilité RGAA d'État et internationalisation). Pour chaque risque prioritaire (exposition $\ge$ 6), une action préventive a été rédigée sous forme de ticket estimé dans le backlog pour en réduire la probabilité ou l'impact.

### [R-01] Saturation du serveur lors des pics de trafic (Tech / Scalabilité)
*   **Cause probable** : Un seul conteneur Ollama gérant les générations, base de données Postgres non répliquée en lecture lors des pics nationaux.
*   **Exposition** : Élevée (Probabilité : 3 × Impact : 3 = **9**)
*   **Action préventive (Backlog)** : 
    *   *Ticket* : `[scale] Mettre en place un cache Redis pour stocker les QCM des cours déjà générés et configurer l'autoscaling horizontal (HPA) pour déployer plusieurs instances Ollama/Django.`
    *   *Estimation* : **8 SP**
    *   *Priorité MoSCoW* : **MUST** (réduit l'impact et la probabilité de panne).

### [R-02] Rejet de la plateforme par l'État pour non-conformité RGAA (Légal / Accessibilité)
*   **Cause probable** : Interface existante codée sans critères d'accessibilité (manque de contrastes textuels, pas de navigation clavier, balises ARIA absentes pour lecteurs d'écran).
*   **Exposition** : Moyenne/Forte (Probabilité : 2 × Impact : 3 = **6**)
*   **Action préventive (Backlog)** :
    *   *Ticket* : `[a11y] Réaliser un audit d'accessibilité automatique au build (intégration d'axe-core) et corriger les contrastes des thèmes ainsi que la navigation au clavier (focus visibles).`
    *   *Estimation* : **5 SP**
    *   *Priorité MoSCoW* : **MUST** (exigence légale d'État non négociable).

### [R-04] Hallucinations du LLM local en langue étrangère (Qualité / i18n)
*   **Cause probable** : Le modèle Llama 3.2 (3B) est plus petit et peut halluciner ou ne pas respecter la consigne de langue si le prompt système n'est pas assez directif.
*   **Exposition** : Moyenne/Forte (Probabilité : 3 × Impact : 2 = **6**)
*   **Action préventive (Backlog)** :
    *   *Ticket* : `[i18n] Adapter dynamiquement le System Prompt de génération de quiz pour y injecter la variable de langue ({langue}) choisie par l'élève, et valider la structure JSON finale en sortie.`
    *   *Estimation* : **5 SP**
    *   *Priorité MoSCoW* : **SHOULD** (assure la pertinence pédagogique).

### [R-05] Coût d'infrastructure cloud hors budget (Financier / Cloud)
*   **Cause probable** : L'autoscaling horizontal déclenche trop de conteneurs cloud gourmands en mémoire face aux requêtes successives des élèves.
*   **Exposition** : Moyenne (Probabilité : 2 × Impact : 2 = **4**)
*   **Action préventive (Backlog)** :
    *   *Ticket* : `[scale] Mettre en place des alertes de facturation mensuelles sur la console cloud (AWS/GCP) et limiter le nombre d'instances maximum dans la configuration de scaling.`
    *   *Estimation* : **3 SP**
    *   *Priorité MoSCoW* : **SHOULD** (garde le projet viable financièrement).

### [R-03] Panne ou indisponibilité du service Ollama local (Technique / Résilience)
*   **Cause probable** : Plantage de la VRAM GPU de la machine hôte ou du conteneur Ollama sous Docker.
*   **Exposition** : Modérée (Probabilité : 1 × Impact : 3 = **3**)
*   **Action préventive (Backlog)** :
    *   *Ticket* : `[scale] Configurer une file d'attente asynchrone (Celery / Redis) pour traiter les demandes de génération en tâche de fond avec affichage d'un loader dynamique côté client.`
    *   *Estimation* : **5 SP**
    *   *Priorité MoSCoW* : **COULD** (améliore la résilience mais non bloquant pour le MVP).
