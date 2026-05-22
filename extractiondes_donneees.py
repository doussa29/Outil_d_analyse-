import pandas as pd
import json

def extraire_donnees(fichiers):
    """
    Ouvre les fichiers JSON des annotateurs et extrait toutes les données utiles,
    y compris les textes complets et les vrais topics.
    """
    donnees_brutes = []
    print("⏳ Extraction des données en cours...")

    for nom_annotateur, chemin_fichier in fichiers.items():
        try:
            with open(chemin_fichier, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for ancre in data:
                    # 1. Extraction des infos de l'ancre
                    id_brut = ancre.get("metadata", {}).get("id", "Inconnu")
                    id_article = f"ID {id_brut}" 
                    titre_ancre = ancre.get("news", "Titre inconnu")
                
                    # 2. Parcours des cibles
                    if 'database' in ancre:
                        for index, cible in enumerate(ancre['database']):
                            relation = cible.get('related')
                            
                            if relation is not None:
                                pos_cible = f"T{index + 1}"
                                titre_cible = cible.get("news", cible.get("text", "Texte cible inconnu"))
                                
                                # 🟢 LE CHANGEMENT EST ICI : 
                                # On récupère le 'topic' directement depuis l'objet 'cible' !
                                categorie = cible.get("topic", "Inconnu")
                                score_similarite = cible.get("metadata", {}).get("similarity_annotation", cible.get("metadata", {}).get("similarity_avg", ""))
                                relation_propre = str(relation).title().strip()
                                
                                # 3. On sauvegarde TOUTES les infos, avec le bon topic !
                                donnees_brutes.append({
                                    'article_id': f"{id_article}_{pos_cible}", 
                                    'id_ancre': id_article,
                                    'texte_ancre': titre_ancre,
                                    'cible': pos_cible,
                                    'texte_cible': titre_cible,
                                    'annotateur': nom_annotateur,
                                    'score': relation_propre,
                                    'categorie': categorie,
                                    'score_similarite': score_similarite
                                })
                                
        except FileNotFoundError:
            print(f"Attention : Le fichier pour {nom_annotateur} ('{chemin_fichier}') est introuvable.")
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier de {nom_annotateur} : {e}")

    df_final = pd.DataFrame(donnees_brutes)
    if not df_final.empty:
        print(f"Extraction terminée : {len(df_final)} annotations récupérées au total.")
    return df_final