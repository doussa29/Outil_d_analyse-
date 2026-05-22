
# Plateforme de Validation et d'Analyse des Annotations 

Cette application web interactive, développée avec **Flask (Python)** et **Bootstrap 5**, est un outil d'administration conçu pour centraliser, valider et optimiser les campagnes d'annotations d'articles de presse dans le cadre du projet **AI4Debunk**.

L'application permet de passer d'un ensemble de fichiers d'annotations individuels (JSON) à un dataset consolidé et validé, tout en mesurant la fiabilité de l'équipe et en gérant intelligemment les désaccords.

## Fonctionnalités Clés

1. **Collecte Multi-Annotateurs Synchrone** : Interface web permettant de téléverser simultanément les fichiers JSON des 5 annotateurs de l'équipe.
2. **Analyse de l'Accord Inter-Annotateurs (IAA)** :
   * Calcul des coefficients de **Kappa de Cohen** (analyses croisées deux à deux).
   * Calcul du **Kappa de Fleiss** (cohérence globale du groupe).
   * Visualisation dynamique de la distribution des thématiques (*Topics*) extraites.
3. **Simulateur de Filtrage & Équilibre des Classes** :
   * Comparaison en temps réel entre le scénario à la **Majorité (>50%)** et à l'**Unanimité (100%)**.
   * Diagnostic automatique de l'équilibre des classes basé sur un seuil vital pour préserver les données minoritaires (*Supporting*).
   * Export automatique des datasets finaux au format CSV nettoyés des variables de calcul intermédiaires, intégrant la clé `similarity_annotation`.
4. **Gestion Tactique des Conflits (Active Learning)** : Isolement des articles en situation de blocage (configurations 2-2-1, 3-3, ou accord ≤ 50%) et génération d'une feuille de route d'action pour les futures sessions de ré-annotation.

## Architecture des Modules

* `app.py` : Serveur Flask principal gérant l'interface Web, le routage, et la conversion dynamique des graphiques Matplotlib en Base64.
* `extractiondes_donneees.py` : Pipeline d'extraction et de structuration des métadonnées imbriquées du fichier JSON d'origine.
* `analyse_de_donnees.py` : Moteur statistique calculant la cohérence inter-annotateurs et générant l'analyse des thématiques.
* `simuler_filtre.py` : Simulateur décisionnel d'équilibre des classes avec système de recommandation algorithmique intégré.
* `assignation_donnees.py` : Algorithme de tri et de détection des structures de conflits pour la ré-annotation.

## Installation et Démarrage

### 1. Prérequis

Assurez-vous d'avoir Python 3.8+ installé. Clonez le dépôt et installez les dépendances requises :

```bash
pip install -r requirements.txt
```
