import pandas as pd
import matplotlib.pyplot as plt

def simuler_filtre(df):
    """
    Simule les filtrages, génère les CSV, construit les tableaux de proportions,
    émet un diagnostic, et retourne un dictionnaire complet pour l'interface Flask.
    """
    if df is None or df.empty:
        print("❌ Le tableau de données est vide.")
        return {
            'df_rapport': None,
            'df_proportions': None,
            'diagnostic': "Aucune donnée disponible pour la simulation."
        }
    
    # 1. Calcul des votes majoritaires par article
    comptage_votes = df.groupby(['article_id', 'score']).size().reset_index(name='nb_votes')
    total_par_article = df.groupby('article_id').size().reset_index(name='total_votes')
    
    votes_fusionnes = pd.merge(comptage_votes, total_par_article, on='article_id')
    votes_fusionnes['taux_accord'] = votes_fusionnes['nb_votes'] / votes_fusionnes['total_votes']
    
    top_votes = votes_fusionnes.sort_values(['article_id', 'nb_votes'], ascending=[True, False]).drop_duplicates('article_id')
    total_articles_initiaux = len(top_votes)

    # 2. Création des filtres de scénarios
    filtre_majorite = top_votes[top_votes['taux_accord'] > 0.50]
    filtre_unanimite = top_votes[top_votes['taux_accord'] == 1.0]

    # 3. Tableau 1 : Rapport Global
    def calculer_equilibre(sous_df):
        if sous_df.empty: return "Aucune donnée"
        repartition = sous_df['score'].value_counts(normalize=True) * 100
        return ", ".join([f"{idx}: {val:.0f}%" for idx, val in repartition.items()])

    lignes_rapport = [
        {"Scenario": "1. Sans Filtre (Brut)", "Articles": len(top_votes), "Conserve": "100%", "Equilibre": calculer_equilibre(top_votes)},
        {"Scenario": "2. MAJORITE (>50%)", "Articles": len(filtre_majorite), "Conserve": f"{(len(filtre_majorite) / total_articles_initiaux) * 100:.1f}%" if total_articles_initiaux > 0 else "0%", "Equilibre": calculer_equilibre(filtre_majorite)},
        {"Scenario": "3. UNANIMITE (100%)", "Articles": len(filtre_unanimite), "Conserve": f"{(len(filtre_unanimite) / total_articles_initiaux) * 100:.1f}%" if total_articles_initiaux > 0 else "0%", "Equilibre": calculer_equilibre(filtre_unanimite)}
    ]
    df_rapport = pd.DataFrame(lignes_rapport)

    # 4. Tableau 2 : Proportions
    dist_maj_pct = filtre_majorite['score'].value_counts(normalize=True) * 100 if not filtre_majorite.empty else pd.Series(dtype=float)
    dist_una_pct = filtre_unanimite['score'].value_counts(normalize=True) * 100 if not filtre_unanimite.empty else pd.Series(dtype=float)
    
    df_comp_proportions = pd.DataFrame({
        'Pourcentage dans Majorite': dist_maj_pct,
        'Pourcentage dans Unanimite': dist_una_pct
    }).fillna(0)
    
    # Récupération des chiffres bruts pour le "Cerveau"
    min_pct_maj = df_comp_proportions['Pourcentage dans Majorite'].min() if not df_comp_proportions.empty else 0
    min_pct_una = df_comp_proportions['Pourcentage dans Unanimite'].min() if not df_comp_proportions.empty else 0

    # Formatage texte pour le tableau (ajout des symboles %)
    df_comp_proportions_disp = df_comp_proportions.copy()
    df_comp_proportions_disp['Pourcentage dans Majorite'] = df_comp_proportions_disp['Pourcentage dans Majorite'].round(1).astype(str) + '%'
    df_comp_proportions_disp['Pourcentage dans Unanimite'] = df_comp_proportions_disp['Pourcentage dans Unanimite'].round(1).astype(str) + '%'
    
    df_comp_proportions_disp.index.name = 'Relation'
    df_comp_proportions_disp = df_comp_proportions_disp.reset_index()
    df_comp_proportions_disp = df_comp_proportions_disp[['Relation', 'Pourcentage dans Unanimite', 'Pourcentage dans Majorite']]

    # 5. Diagnostic du Robot (Recommandation)
    seuil_vital = 10.0
    
    if min_pct_una >= seuil_vital:
        meilleur_choix = "UNANIMITÉ (100%)"
        explication = f"Le dataset reste équilibré (la plus petite classe survit à {min_pct_una:.1f}% >= {seuil_vital}%). Privilégiez la qualité parfaite."
    elif min_pct_maj >= seuil_vital:
        meilleur_choix = "MAJORITÉ (>50%)"
        explication = f"L'Unanimité détruit la classe minoritaire (chute à {min_pct_una:.1f}%), tandis que la Majorité la préserve à {min_pct_maj:.1f}%. Choisissez la Majorité."
    else:
        meilleur_choix = "MAJORITÉ (>50%)"
        explication = f"Le dataset est très déséquilibré de base. Conservez la Majorité pour sauver le maximum de données rares."

    diagnostic_complet = f"👉 La meilleure option recommandée est : {meilleur_choix}\n📝 Pourquoi ? {explication}"

    # 6. Sauvegarde des CSV "Gold Standards"
    colonnes_textes = ['article_id', 'id_ancre', 'texte_ancre', 'cible', 'texte_cible', 'categorie', 'score_similarite']
    colonnes_presentes = [c for c in colonnes_textes if c in df.columns] 
    df_textes = df[colonnes_presentes].drop_duplicates('article_id')

    df_export_majorite = pd.merge(filtre_majorite, df_textes, on='article_id', how='left').rename(columns={'score': 'Label_Majoritaire'})
    df_export_unanimite = pd.merge(filtre_unanimite, df_textes, on='article_id', how='left').rename(columns={'score': 'Label_Majoritaire'})

    df_export_majorite['Pourcentage_Accord'] = (df_export_majorite['taux_accord'] * 100).round(0).astype(int).astype(str) + '%'
    df_export_unanimite['Pourcentage_Accord'] = (df_export_unanimite['taux_accord'] * 100).round(0).astype(int).astype(str) + '%'

    ordre_colonnes = ['id_ancre', 'texte_ancre', 'cible', 'texte_cible', 'categorie', 'score_similarite', 'Label_Majoritaire', 'Pourcentage_Accord']
    ordre_final = [c for c in ordre_colonnes if c in df_export_majorite.columns]

    df_export_majorite[ordre_final].to_csv("dataset_valide_majorite.csv", index=False, encoding='utf-8-sig')
    df_export_unanimite[ordre_final].to_csv("dataset_valide_unanimite.csv", index=False, encoding='utf-8-sig')

    # 7. Génération du graphique
    try:
        dist_brut = top_votes['score'].value_counts(normalize=True) * 100
        df_graph = pd.DataFrame({
            f'Sans Filtre ({len(top_votes)})': dist_brut,
            f'Majorite ({len(filtre_majorite)})': dist_maj_pct,
            f'Unanimite ({len(filtre_unanimite)})': dist_una_pct
        }).fillna(0)
        
        fig, ax = plt.subplots(figsize=(11, 5))
        df_graph.plot(kind='bar', color=['#95a5a6', '#3498db', '#e74c3c'], edgecolor='black', alpha=0.85, ax=ax)
        for container in ax.containers:
            ax.bar_label(container, fmt='%.1f%%', padding=3, fontsize=9, fontweight='bold')
        
        plt.title("Evolution de l'equilibre des classes", fontsize=14, fontweight='bold', pad=15)
        plt.ylabel("Proportion (%)")
        plt.ylim(0, 110)
        plt.xticks(rotation=0) 
        plt.tight_layout()
    except Exception as e:
        pass

    # 8. LE RETOUR FINAL : Flask reçoit tout le package !
    return {
        'df_rapport': df_rapport,
        'df_proportions': df_comp_proportions_disp,
        'diagnostic': diagnostic_complet
    }