import pandas as pd
import numpy as np
import itertools
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display

try:
    import pingouin as pg
    HAS_PINGOUIN = True
except ImportError:
    HAS_PINGOUIN = False

def analyser_donnees(df):
    if df is None or df.empty:
        return None

    rapport = {}
    sns.set_theme(style="whitegrid")

    # 1. & 2. TOPICS
    dist_categories = df['categorie'].value_counts(normalize=True) * 100
    try:
        fig_topics, ax = plt.subplots(figsize=(10, 4))
        dist_categories.plot(kind='bar', color='skyblue', edgecolor='black', ax=ax)
        for container in ax.containers:
            ax.bar_label(container, fmt='%.1f%%', padding=3, fontsize=9, fontweight='bold')
        plt.title("Répartition des thématiques (Topics)", fontsize=14, fontweight='bold', pad=15)
        plt.ylabel("Pourcentage (%)")
        plt.ylim(0, max(dist_categories) + 12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        rapport['fig_topics'] = fig_topics
    except Exception:
        rapport['fig_topics'] = None

    df_pivot = df.pivot_table(index='article_id', columns='annotateur', values='score', aggfunc='first')
    annotateurs = df_pivot.columns

    # 3. KAPPA DE COHEN
    mk = pd.DataFrame(np.ones((len(annotateurs), len(annotateurs))), index=annotateurs, columns=annotateurs)
    lignes_cohen = []

    for a1, a2 in itertools.combinations(annotateurs, 2):
        commun = df_pivot[[a1, a2]].dropna()
        if len(commun) >= 2:
            score_k = cohen_kappa_score(commun[a1], commun[a2])
            mk.loc[a1, a2] = score_k
            mk.loc[a2, a1] = score_k
            lignes_cohen.append({
                "Paire": f"{a1} & {a2}",
                "Articles communs": len(commun),
                "Kappa": round(score_k, 3),
                "Interprétation": _interpreter_kappa(score_k)
            })
        else:
            mk.loc[a1, a2] = np.nan
            mk.loc[a2, a1] = np.nan

    rapport['df_cohen'] = pd.DataFrame(lignes_cohen)

    try:
        fig_kappa = plt.figure(figsize=(7, 5))
        sns.heatmap(mk.astype(float), annot=True, cmap="YlGnBu", vmin=0, vmax=1, center=0.5, fmt=".2f", square=True)
        plt.title("Matrice de Kappa de Cohen", fontsize=14, fontweight='bold', pad=15)
        plt.tight_layout()
        rapport['fig_kappa'] = fig_kappa
    except Exception:
        rapport['fig_kappa'] = None

    # 4. KAPPA DE FLEISS
    try:
        table_fleiss, _ = aggregate_raters(df_pivot.fillna("Non annoté").values)
        score_fleiss = fleiss_kappa(table_fleiss)
        rapport['fleiss'] = f"{score_fleiss:.3f} ({_interpreter_kappa(score_fleiss)})"
    except Exception:
        rapport['fleiss'] = "Calcul impossible (données manquantes)"

    # 5. TYPOLOGIE
    typo_counts = {}
    for _, row in df_pivot.iterrows():
        v = row.dropna()
        n_val = len(v)
        if n_val >= 3:
            max_f = v.value_counts().max()
            if n_val == 5:
                if max_f == 5: cat = "Unanimité (5-0)"
                elif max_f == 4: cat = "Majorité forte (4-1)"
                elif max_f == 3: cat = "Majorité faible (3-2)"
                else: cat = "Désaccord profond"
            else:
                cat = f"Accord Majoritaire ({max_f}/{n_val})" if max_f > (n_val/2) else "Désaccord / Division"
            typo_counts[cat] = typo_counts.get(cat, 0) + 1

    if typo_counts:
        df_typo = pd.DataFrame(list(typo_counts.items()), columns=['Typologie', 'Nombre de cas']).sort_values('Nombre de cas', ascending=False)
        rapport['df_typo'] = df_typo
        try:
            fig_typo = plt.figure(figsize=(9, 4))
            sns.barplot(data=df_typo, x='Typologie', y='Nombre de cas', palette='Blues_r')
            plt.title("Répartition par type d'accord", fontsize=14, fontweight='bold', pad=15)
            plt.xticks(rotation=30, ha='right')
            plt.tight_layout()
            rapport['fig_typo'] = fig_typo
        except Exception:
            rapport['fig_typo'] = None
    else:
        rapport['df_typo'] = None
        rapport['fig_typo'] = None

    # 6. LEAVE-ONE-OUT
    try:
        results_loo = []
        for n in annotateurs:
            colonnes_restantes = [c for c in annotateurs if c != n]
            if len(colonnes_restantes) >= 2:
                df_sub = df_pivot[colonnes_restantes].dropna(how='all')
                agg_s, _ = aggregate_raters(df_sub.fillna("Non annoté").values)
                sub_kappa = fleiss_kappa(agg_s)
                results_loo.append({
                    "Annotateur retiré": n, 
                    "Nouveau Fleiss": round(sub_kappa, 3), 
                    "Différence": f"{sub_kappa - score_fleiss:+.3f}"
                })
        rapport['df_loo'] = pd.DataFrame(results_loo)
    except Exception:
        rapport['df_loo'] = None

    # 7. PEARSON & ICC
    if 'score_similarite' in df.columns:
        df['score_similarite_num'] = pd.to_numeric(df['score_similarite'], errors='coerce')
        df_sim_pivot = df.pivot_table(index='article_id', columns='annotateur', values='score_similarite_num', aggfunc='first')
        
        corr_matrix = df_sim_pivot.corr(method='pearson')
        valid_vals = corr_matrix.values[np.triu_indices_from(corr_matrix, k=1)]
        mean_p = np.nanmean(valid_vals) if len(valid_vals) > 0 else np.nan
        rapport['pearson_txt'] = f"{mean_p:.3f} ({_interpret_pearson(mean_p)})"

        try:
            fig_pearson = plt.figure(figsize=(7, 5))
            sns.heatmap(corr_matrix.astype(float), annot=True, cmap="coolwarm", vmin=-1, vmax=1, center=0, fmt=".2f", square=True)
            plt.title("Corrélation de Pearson (Similarité)", fontsize=14, fontweight='bold', pad=15)
            plt.tight_layout()
            rapport['fig_pearson'] = fig_pearson
        except Exception:
            rapport['fig_pearson'] = None

        if HAS_PINGOUIN:
            try:
                df_long = df_sim_pivot.reset_index().melt(id_vars='article_id', var_name='Rater', value_name='Score').dropna()
                if df_long['Score'].var() > 0:
                    icc_res = pg.intraclass_corr(data=df_long, targets='article_id', raters='Rater', ratings='Score')
                    icc2_row = icc_res[icc_res['Type'] == 'ICC2']
                    icc_val = icc2_row['ICC'].values[0] if not icc2_row.empty else icc_res['ICC'].values[0]
                    rapport['icc_txt'] = f"{icc_val:.3f} ({_interpret_icc(icc_val)})"
                else:
                    rapport['icc_txt'] = "Variance nulle"
            except Exception:
                rapport['icc_txt'] = "Erreur de calcul"
        else:
            rapport['icc_txt'] = "Librairie 'pingouin' manquante"
    else:
        rapport['pearson_txt'] = "N/A"
        rapport['icc_txt'] = "N/A"
        rapport['fig_pearson'] = None

    return rapport

def _interpreter_kappa(val):
    if val is None or pd.isna(val) or isinstance(val, str): return "—"
    if val < 0.00: return "Désaccord total"
    elif val <= 0.20: return "Accord léger"
    elif val <= 0.40: return "Accord passable"
    elif val <= 0.60: return "Accord modéré"
    elif val <= 0.80: return "Accord fort"
    else: return "Accord presque parfait"

def _interpret_pearson(r):
    if pd.isna(r): return "Non calculable"
    if r >= 0.70: return "Forte corrélation"
    elif r >= 0.30: return "Corrélation modérée"
    elif r > 0: return "Faible corrélation"
    else: return "Corrélation nulle ou négative"

def _interpret_icc(icc):
    if pd.isna(icc): return "Non calculable"
    if icc < 0.50: return "Fiabilité faible"
    elif icc < 0.75: return "Fiabilité modérée"
    elif icc < 0.90: return "Fiabilité bonne"
    else: return "Fiabilité excellente"