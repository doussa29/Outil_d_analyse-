import pandas as pd

def assigner_donnees(df):
    """
    Identifie et trie UNIQUEMENT les articles en conflit (ex: 2-2-1, 3-3, accord <= 50%)
    pour générer la feuille de route de la prochaine session de ré-annotation.
    """
    if df is None or df.empty:
        print(" Le tableau de données est vide. Impossible de calculer les assignations.")
        return None 

    print(" ALGORITHME D'ASSIGNATION (GESTION DES CONFLITS)")
    total_par_article = df.groupby('article_id').size().reset_index(name='total_votes')
    
    comptage_votes = df.groupby(['article_id', 'score']).size().reset_index(name='nb_votes')
    max_vote_label = comptage_votes.groupby('article_id')['nb_votes'].max().reset_index(name='votes_majoritaires')
 
    analyse_assign = pd.merge(total_par_article, max_vote_label, on='article_id')
    analyse_assign['taux_accord'] = analyse_assign['votes_majoritaires'] / analyse_assign['total_votes']

    df_textes = df[['article_id', 'id_ancre', 'texte_ancre', 'cible', 'texte_cible', 'categorie']].drop_duplicates('article_id')
    analyse_complete = pd.merge(analyse_assign, df_textes, on='article_id', how='left')

    lignes_prioritaires = []

    for _, row in analyse_complete.iterrows():
        
        if row['taux_accord'] <= 0.50 and row['total_votes'] > 1:
           
            votes_article = comptage_votes[comptage_votes['article_id'] == row['article_id']]
            config_votes = "-".join(map(str, sorted(votes_article['nb_votes'].tolist(), reverse=True)))
            raison = f"Conflit majeur (Configuration {config_votes}). Ré-annotation requise."

            lignes_prioritaires.append({
                "Niveau_Priorite": " P2 (Conflit)",
                "ID_Article": row['article_id'],
                "Topic": row['categorie'],
                "Votes_Actuels": row['total_votes'],
                "Max_Votes_Identiques": row['votes_majoritaires'],
                "Raison_Assignation": raison,
                "ID_Ancre": row['id_ancre'],
                "Texte_Ancre": row['texte_ancre'],
                "Cible": row['cible'],
                "Texte_Cible": row['texte_cible']
            })

    # 5. Création du DataFrame avec SÉCURITÉ
    if len(lignes_prioritaires) > 0:
        df_priorites = pd.DataFrame(lignes_prioritaires)
        
        print(f" Analyse terminée : {len(df_priorites)} articles détectés pour ré-annotation.")
        print("\n APERÇU DES TÂCHES À REDISTRIBUER :")
        print(df_priorites[["Niveau_Priorite", "ID_Article", "Topic", "Votes_Actuels", "Raison_Assignation"]].to_string(index=False)) 
        
        nom_fichier = "feuille_de_route_reannotation.csv"
        df_priorites.to_csv(nom_fichier, index=False, encoding='utf-8-sig')
        print(f"\n Fichier '{nom_fichier}' enregistré avec TOUTES les colonnes de texte !")
    
        return df_priorites
        
    else:
        print(" Aucun conflit détecté dans le dataset ! L'équipe est d'accord sur tout.")
        return pd.DataFrame()