# Rapport de Benchmark LLM — Perturbation J2 (Latence)

**Projet** : EduTutor IA  
**Date** : 30 Juin 2026  
**Équipe** : Groupe 30  
**Responsable Benchmark** : Keziah Perfillon  

---

## 1. Protocole de Benchmark

Pour répondre de manière rigoureuse aux plaintes du bêta-testeur (latence de 45 secondes inacceptable), nous avons défini un protocole de test standard et reproductible.

### Contexte Matériel (Machine de Test)
- **Processeur (CPU)** : Intel Core i7-10750H (6 cœurs, 12 threads @ 2.60GHz)
- **Mémoire Vive (RAM)** : 16 Go DDR4
- **Carte Graphique (GPU)** : NVIDIA GeForce GTX 1660 Ti (6 Go VRAM)
- **Disque** : SSD NVMe M.2
- **Système d'exploitation** : Windows 11 (Docker WSL2)

### Conditions du Test
- **Document de référence** : Un cours d'algorithmie de Master 2 au format PDF contenant du texte et du pseudo-code (~12 pages, 4 800 mots, taille du fichier : 1.2 Mo).
- **Nombre de runs par modèle** : 5 runs consécutifs pour chaque modèle afin de calculer la latence médiane ($p_{50}$) et le pire cas ($p_{95}$).
- **État du système** : Redémarrage d'Ollama avant chaque série de tests pour vider le cache VRAM/RAM. Aucune autre application lourde en arrière-plan.
- **Paramètres de génération** : Température fixée à 0.4 (valeur par défaut du projet dans `quiz_prompt.py` pour limiter les hallucinations).
- **Évaluation de la qualité** : 3 testeurs de l'équipe ont évalué subjectivement la pertinence des 10 questions générées sur une échelle de 1 à 5 (1 = mauvaise/hors-sujet, 5 = excellente/pertinente).

---

## 2. Exécution et Mesures

Nous avons testé 3 modèles locaux via Ollama (le modèle par défaut et 2 alternatives légères), ainsi qu'une solution Cloud (Gemini 1.5 Flash via API) à titre de comparaison technique.

### Modèles testés :
1. **Llama 3.1 8B (Q4_K_M)** : Modèle par défaut du kit.
2. **Llama 3.2 3B (Q4_K_M)** : Alternative ultra-légère recommandée pour les configurations à faible RAM.
3. **Phi-3 Mini (3.8B - Q4_K_M)** : Modèle de Microsoft réputé pour son excellent rapport taille/raisonnement.
4. **Gemini 1.5 Flash (Cloud API)** : Solution externe utilisée pour mesurer le gain d'une bascule Cloud.

---

## 3. Résultats et Analyse

Voici le tableau récapitulatif des mesures obtenues :

| Métrique / Modèle | Llama 3.1 8B (Local) | Llama 3.2 3B (Local) | Phi-3 Mini 3.8B (Local) | Gemini 1.5 Flash (Cloud) |
| :--- | :---: | :---: | :---: | :---: |
| **Taille sur Disque** | 4.7 Go | 2.0 Go | 2.2 Go | 0 Go (Hébergé) |
| **RAM/VRAM requise** | ~5.8 Go VRAM | ~2.2 Go VRAM | ~2.5 Go VRAM | 0 Go (API Externe) |
| **Latence Médiane ($p_{50}$)** | **46.2 s** | **12.4 s** | **14.8 s** | **3.2 s** |
| **Latence Pire Cas ($p_{95}$)** | **54.8 s** | **17.2 s** | **21.5 s** | **4.9 s** |
| **Qualité Subjective (/5)** | **4.6 / 5** | **3.6 / 5** | **3.8 / 5** | **4.3 / 5** |
| **Statut RGPD** | 🟢 100% Conforme | 🟢 100% Conforme | 🟢 100% Conforme | 🔴 Données hors UE |

### Analyse des compromis (Trade-offs)

1. **Llama 3.1 8B** : 
   - *Avantages* : Excellente qualité des questions, respecte parfaitement le format JSON demandé.
   - *Inconvénients* : Latence médiane à **46.2s** (hors des critères d'acceptation utilisateur de < 15s). Consomme la quasi-totalité de la VRAM (5.8 Go sur 6 Go disponibles), ce qui ralentit l'affichage global sur le PC hôte.

2. **Llama 3.2 3B** : 
   - *Avantages* : Très rapide (médiane à **12.4s**, sous l'exigence des 15s). Consommation de ressources très faible (~2.2 Go), ce qui libère la machine hôte.
   - *Inconvénients* : Qualité des questions en légère baisse (parfois des formulations simplistes ou répétitives). A besoin d'un prompt système robuste pour éviter les erreurs de format JSON.

3. **Phi-3 Mini (3.8B)** :
   - *Avantages* : Bon compromis vitesse/qualité (médiane à **14.8s**). Meilleure logique de raisonnement que Llama 3.2 3B sur les concepts scientifiques complexes.
   - *Inconvénients* : Légèrement plus lent que Llama 3.2 3B, s'approche de la limite de tolérance des 15s.

4. **Gemini 1.5 Flash (Cloud)** :
   - *Avantages* : Vitesse instantanée (médiane à **3.2s**), excellente qualité.
   - *Inconvénients* : Envoi des documents de cours sur des serveurs externes Google hors UE. **Incompatible avec l'invariant de souveraineté et de conformité RGPD strict** fixé pour le MVP de la plateforme.

---

## 4. Conclusion du Benchmark

Pour respecter le critère de latence imposé par le Product Owner ($T_{génération} \le 15\text{ s}$) tout en garantissant un traitement local et souverain des données scolaires (respect strict du RGPD) :

**Le modèle Llama 3.2 3B est retenu.** Il offre un gain de vitesse de **3.7x** par rapport à Llama 3.1 8B tout en restant sous le seuil maximal de 15 secondes. La légère baisse de qualité s'accompagnera d'une consolidation du prompt système et de l'ajout d'une étape de validation des questions.
