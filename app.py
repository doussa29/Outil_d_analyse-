import os
import io
import base64
import pandas as pd
import matplotlib

matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from flask import Flask, request, render_template_string, send_file

# Importation de tes modules d'analyse
from extractiondes_donneees import extraire_donnees
from analyse_de_donnees import analyser_donnees
from simuler_filtre import simuler_filtre
from assigner_donnees import assigner_donnees

app = Flask(__name__)
UPLOAD_FOLDER = 'temp_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Variables globales de session
donnees_globales = {
    'dataset': None,
    'nb_annotations': 0,
    'onglet_actif': 'brutes'
}

def fig_to_base64(fig):
    """Convertit une figure Matplotlib en image encodée pour le web."""
    if fig is None: return None
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return base64.b64encode(buf.read()).decode('utf-8')

def df_to_html(df, classes="table table-sm table-striped table-bordered text-dark"):
    """Convertit un DataFrame en joli tableau HTML Bootstrap."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty): return ""
    return df.to_html(classes=classes, index=False)

# =========================================================
# INTERFACE GRAPHIQUE (HTML/CSS via Bootstrap 5)
# =========================================================
TEMPLATE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI4Debunk - Centre de Validation</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', system-ui, sans-serif; }
        .navbar-brand { font-weight: 700; letter-spacing: 0.5px; }
        .card { border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-radius: 10px; margin-bottom: 25px; }
        .nav-pills .nav-link.active { background-color: #0d6efd; }
        .notebook-section { background: white; padding: 20px; border-radius: 8px; border-left: 5px solid #0d6efd; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .notebook-title { font-size: 1.1rem; font-weight: bold; color: #333; margin-bottom: 10px; }
        .notebook-desc { font-size: 0.9rem; color: #666; margin-bottom: 15px; }
        .graph-img { max-width: 100%; height: auto; border-radius: 8px; margin-top: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    </style>
</head>
<body>

    <nav class="navbar navbar-dark bg-dark mb-4 shadow-sm">
        <div class="container">
            <span class="navbar-brand mb-0 h1">📊 AI4Debunk - Plateforme d'Administration des Données</span>
            <span class="text-light small">Laboratoire ISIA (UMONS) — Amadou</span>
        </div>
    </nav>

    <div class="container">
        <div class="alert alert-info shadow-sm mb-4 border-0" style="background-color: #e2f0fd; color: #084298;">
            <h5 class="alert-heading fw-bold">🚀 Bienvenue sur le Dashboard de Traitement des Annotations</h5>
            <p class="mb-2">Ce tableau de bord centralise le traitement de vos annotations manuelles. Il vous permet de :</p>
            <ul class="mb-0">
                <li><strong>Extraire</strong> les données brutes de vos fichiers JSON.</li>
                <li><strong>Analyser</strong> l'accord inter-annotateurs (Kappas, Pearson, Typologie).</li>
                <li><strong>Simuler</strong> des règles de consensus pour générer vos <em>Gold Standards</em>.</li>
                <li><strong>Créer</strong> une feuille de route pour résoudre vos litiges d'annotation.</li>
            </ul>
        </div>

        <div class="card p-4 bg-white">
            <h4 class="card-title mb-4 text-primary">📦 Configuration & Actions</h4>
            <form action="/traiter" method="POST" enctype="multipart/form-data">
                
                <div class="row mb-4">
                    <div class="col-md-6 border-end">
                        <h6 class="fw-bold mb-3">1. Nommage des Annotateurs</h6>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="radio" name="naming_mode" id="mode_generique" value="generique" checked onchange="toggleCustomNames()">
                            <label class="form-check-label" for="mode_generique">Générique (Annotateur 1, Annotateur 2...)</label>
                        </div>
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="radio" name="naming_mode" id="mode_custom" value="custom" onchange="toggleCustomNames()">
                            <label class="form-check-label" for="mode_custom">Noms personnalisés</label>
                        </div>
                        
                        <div id="custom_names_div" style="display: none;">
                            <label class="form-label text-muted small mb-1">Entrez les prénoms dans l'ordre des fichiers (séparés par des virgules) :</label>
                            <input type="text" name="custom_names" class="form-control" placeholder="Ex: Amadou, Emma, Sandra, Zeren...">
                        </div>
                    </div>

                    <div class="col-md-6 ps-md-4">
                        <h6 class="fw-bold mb-3">2. Importation des fichiers JSON</h6>
                        <p class="text-muted small mb-2">Sélectionnez simultanément tous les fichiers JSON de votre équipe.</p>
                        <input type="file" name="fichiers" multiple class="form-control form-control-lg mb-3" {% if not upload_deja_fait %}required{% endif %}>
                        {% if upload_deja_fait %}
                        <span class="badge bg-success mb-2">✅ {{ nb_annotations }} annotations actuellement en mémoire.</span>
                        {% endif %}
                    </div>
                </div>

                <div class="row g-2">
                    <div class="col-md-4">
                        <button type="submit" name="action" value="analyse" class="btn btn-outline-primary w-100 fw-bold py-2 shadow-sm">📈 Lancer l'Analyse IAA</button>
                    </div>
                    <div class="col-md-4">
                        <button type="submit" name="action" value="simuler" class="btn btn-outline-success w-100 fw-bold py-2 shadow-sm">🧪 Lancer le Filtrage</button>
                    </div>
                    <div class="col-md-4">
                        <button type="submit" name="action" value="conflits" class="btn btn-outline-warning text-dark w-100 fw-bold py-2 shadow-sm">⚠️ Générer Réannotation</button>
                    </div>
                </div>
            </form>
        </div>

        {% if onglet_actif != 'brutes' %}
        <ul class="nav nav-pills nav-fill mb-4 p-1 bg-white rounded shadow-sm">
            <li class="nav-item">
                <a class="nav-link {% if onglet_actif == 'analyse' %}active{% endif %}" href="#">📈 Accords Inter-Annotateurs</a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if onglet_actif == 'simuler' %}active{% endif %}" href="#">🧪 Simulateur de Filtrage</a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if onglet_actif == 'conflits' %}active{% endif %}" href="#">⚠️ Gestion des Conflits</a>
            </li>
        </ul>
        {% endif %}

        <div class="tab-content" id="pills-tabContent">
            
            {% if onglet_actif == 'analyse' %}
            <div>
                <div class="notebook-section">
                    <div class="notebook-title">1. Répartition par Thématique (Topics)</div>
                    <div class="notebook-desc">Volume d'articles traités pour chaque catégorie d'actualité. Cela permet de vérifier la diversité du corpus analysé.</div>
                    <div class="text-center">
                        {% if img_topics %} <img src="data:image/png;base64,{{ img_topics }}" class="graph-img"> {% endif %}
                    </div>
                </div>

                <div class="notebook-section">
                    <div class="notebook-title">2. Accord Croisé (Kappa de Cohen)</div>
                    <div class="notebook-desc">Mesure mathématique de l'accord entre deux annotateurs spécifiques, en excluant le hasard. 1.0 indique un accord parfait.</div>
                    <div class="row align-items-center mt-3">
                        <div class="col-md-6"><div class="table-responsive">{{ tab_cohen | safe }}</div></div>
                        <div class="col-md-6 text-center">
                            {% if img_kappa %} <img src="data:image/png;base64,{{ img_kappa }}" class="graph-img"> {% endif %}
                        </div>
                    </div>
                </div>

                <div class="notebook-section">
                    <div class="notebook-title">3. Typologie des Annotations & Fleiss</div>
                    <div class="notebook-desc">
                        <strong class="text-primary">Score de Fleiss (Accord global) : {{ score_fleiss }}</strong><br>
                        Analyse détaillée de la force du consensus pour chaque article annoté.
                    </div>
                    <div class="row align-items-center mt-3">
                        <div class="col-md-5"><div class="table-responsive">{{ tab_typo | safe }}</div></div>
                        <div class="col-md-7 text-center">
                            {% if img_typo %} <img src="data:image/png;base64,{{ img_typo }}" class="graph-img"> {% endif %}
                        </div>
                    </div>
                </div>

                <div class="notebook-section">
                    <div class="notebook-title">4. Corrélations Numériques (Similarité)</div>
                    <div class="notebook-desc">
                        <strong class="text-primary">Corrélation Intraclasse (ICC) : {{ score_icc }}</strong><br>
                        <strong class="text-primary">Corrélation de Pearson (Moyenne) : {{ score_pearson }}</strong><br>
                        Évalue la proximité des scores algorithmiques extraits par chaque membre de l'équipe.
                    </div>
                    <div class="text-center">
                        {% if img_pearson %} <img src="data:image/png;base64,{{ img_pearson }}" class="graph-img" style="max-width: 650px;"> {% endif %}
                    </div>
                </div>
                
                <div class="notebook-section">
                    <div class="notebook-title">5. Analyse de l'Impact Individuel (Leave-One-Out)</div>
                    <div class="notebook-desc">Simule le score global (Fleiss) si un membre spécifique était retiré de l'équipe. Un delta positif signifie que l'annotateur a tendance à faire baisser la moyenne globale de l'accord.</div>
                    <div class="table-responsive">{{ tab_loo | safe }}</div>
                </div>
            </div>
            {% endif %}

            {% if onglet_actif == 'simuler' %}
            <div class="card p-4">
                <h5 class="text-dark fw-bold mb-3">Rapport des Scénarios Comparatifs</h5>
                <div class="table-responsive mb-4">{{ table_simulation | safe }}</div>
                
                <h5 class="text-dark fw-bold mb-3 mt-4">⚖️ Proportions et Équilibre des Relations</h5>
                <div class="table-responsive mb-4">{{ table_proportions | safe }}</div>

                <div class="alert shadow-sm mb-4 border-0" style="background-color: #fff3cd; color: #664d03;">
                    <h5 class="alert-heading fw-bold">🤖 Diagnostic d'Équilibre et Recommandation Algorithmique</h5>
                    <p class="mb-0" style="white-space: pre-line;">{{ diagnostic }}</p>
                </div>

                <div class="text-center mb-4">
                    {% if img_sim %} <img src="data:image/png;base64,{{ img_sim }}" class="graph-img"> {% endif %}
                </div>
                
                <div class="alert alert-success mt-4 shadow-sm border-0">
                    <h6 class="fw-bold text-success mb-3">💾 Fichiers de Production Prêts !</h6>
                    <p class="small text-muted mb-3">Les datasets consolidés ont été générés avec succès. Que souhaitez-vous télécharger ?</p>
                    <div class="d-flex gap-3 justify-content-center flex-wrap">
                        <a href="/telecharger/majorite" class="btn btn-primary fw-bold px-4 shadow-sm">📥 Télécharger Majorité (>50%)</a>
                        <a href="/telecharger/unanimite" class="btn btn-success fw-bold px-4 shadow-sm">📥 Télécharger Unanimité (100%)</a>
                    </div>
                </div>
            </div>
            {% endif %}

            {% if onglet_actif == 'conflits' %}
            <div class="card p-4">
                <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                    <h5 class="text-dark fw-bold mb-0">Éléments Arbitraires à Ré-annoter (Accord ≤ 50%)</h5>
                    {% if a_des_conflits %}
                    <a href="/telecharger_conflits" class="btn btn-warning fw-bold shadow-sm">💾 Télécharger la Feuille de Route CSV</a>
                    {% endif %}
                </div>
                
                {% if a_des_conflits %}
                <div class="table-responsive">
                    {{ table_priorites | safe }}
                </div>
                {% else %}
                <div class="text-center py-5">
                    <span class="display-4">🎉</span>
                    <h4 class="text-success mt-3">Aucun conflit d'accord majeur détecté !</h4>
                    <p class="text-muted">Votre équipe est unanime ou dispose d'une majorité nette sur l'ensemble de la campagne.</p>
                </div>
                {% endif %}
            </div>
            {% endif %}

        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function toggleCustomNames() {
            var mode = document.querySelector('input[name="naming_mode"]:checked').value;
            document.getElementById('custom_names_div').style.display = (mode === 'custom') ? 'block' : 'none';
        }
    </script>
</body>
</html>
"""

# =========================================================
# TRAITEMENT FLASK
# =========================================================
@app.route("/")
def index():
    return render_template_string(TEMPLATE_HTML, onglet_actif='brutes', upload_deja_fait=(donnees_globales['dataset'] is not None))

@app.route("/traiter", methods=["POST"])
def traiter_fichiers():
    global donnees_globales
    
    # Récupération de l'action cliquée (analyse, simuler, conflits)
    action_demandee = request.form.get("action")
    fichiers_charges = request.files.getlist("fichiers")
    
    # 1. Gestion des fichiers (On recharge si de nouveaux fichiers sont fournis)
    if fichiers_charges and fichiers_charges[0].filename != '':
        naming_mode = request.form.get("naming_mode", "generique")
        custom_names_str = request.form.get("custom_names", "")
        noms_personnalises = [n.strip() for n in custom_names_str.split(',')] if naming_mode == "custom" and custom_names_str.strip() else []

        fichiers_equipe = {}
        fichiers_charges_tries = sorted(fichiers_charges, key=lambda x: x.filename)
        
        for idx, f in enumerate(fichiers_charges_tries):
            nom_ann = noms_personnalises[idx] if naming_mode == "custom" and idx < len(noms_personnalises) else f"Annotateur {idx + 1}"
            chemin_complet = os.path.join(UPLOAD_FOLDER, f.filename)
            f.save(chemin_complet)
            fichiers_equipe[nom_ann] = chemin_complet

        df = extraire_donnees(fichiers_equipe)
        donnees_globales['dataset'] = df
        donnees_globales['nb_annotations'] = len(df) if df is not None else 0
    else:
        # Sinon on utilise ceux déjà en mémoire
        df = donnees_globales['dataset']

    if df is None or df.empty:
        return "❌ Veuillez d'abord importer des fichiers JSON valides.", 400

    # 2. Routage vers l'action demandée
    if action_demandee == "analyse":
        plt.close('all')
        rapport = analyser_donnees(df)
        
        return render_template_string(
            TEMPLATE_HTML, onglet_actif='analyse', upload_deja_fait=True, nb_annotations=donnees_globales['nb_annotations'],
            img_topics=fig_to_base64(rapport.get('fig_topics')),
            img_kappa=fig_to_base64(rapport.get('fig_kappa')),
            img_typo=fig_to_base64(rapport.get('fig_typo')),
            img_pearson=fig_to_base64(rapport.get('fig_pearson')),
            tab_cohen=df_to_html(rapport.get('df_cohen')),
            tab_typo=df_to_html(rapport.get('df_typo')),
            tab_loo=df_to_html(rapport.get('df_loo')),
            score_fleiss=rapport.get('fleiss', 'N/A'),
            score_icc=rapport.get('icc_txt', 'N/A'),
            score_pearson=rapport.get('pearson_txt', 'N/A')
        )

    elif action_demandee == "simuler":
        plt.close('all')
        # ⚠️ IMPORTANT: Assure-toi que simuler_filtre retourne bien le dictionnaire !
        resultats_sim = simuler_filtre(df) 
        img_sim = fig_to_base64(plt.gcf())
        
        return render_template_string(
            TEMPLATE_HTML, 
            onglet_actif='simuler', 
            upload_deja_fait=True, 
            nb_annotations=donnees_globales['nb_annotations'],
            table_simulation=df_to_html(resultats_sim['df_rapport'], "table table-striped table-bordered fw-medium text-center"),
            table_proportions=df_to_html(resultats_sim['df_proportions'], "table table-sm table-hover table-bordered text-dark"),
            diagnostic=resultats_sim.get('diagnostic', "Information non disponible"),
            img_sim=img_sim
        )

    elif action_demandee == "conflits":
        df_priorites = assigner_donnees(df)
        a_des_conflits = df_priorites is not None and not df_priorites.empty
        
        return render_template_string(
            TEMPLATE_HTML, onglet_actif='conflits', upload_deja_fait=True, nb_annotations=donnees_globales['nb_annotations'],
            table_priorites=df_to_html(df_priorites, "table table-sm table-warning table-hover table-bordered text-dark"),
            a_des_conflits=a_des_conflits
        )

# =========================================================
# ROUTES DE TÉLÉCHARGEMENT DES CSV
# =========================================================
@app.route("/telecharger_conflits")
def telecharger_conflits():
    """Télécharge la feuille de route pour la réannotation."""
    nom_fichier = "feuille_de_route_reannotation.csv"
    if os.path.exists(nom_fichier):
        return send_file(nom_fichier, as_attachment=True)
    return "Fichier introuvable. Avez-vous lancé la détection de conflits ?", 404

@app.route("/telecharger/<type_fichier>")
def telecharger_fichier(type_fichier):
    """Télécharge dynamiquement les Gold Standards (Majorité / Unanimité)."""
    fichiers_disponibles = {
        "majorite": "dataset_valide_majorite.csv",
        "unanimite": "dataset_valide_unanimite.csv"
    }
    
    nom_fichier = fichiers_disponibles.get(type_fichier)
    if nom_fichier and os.path.exists(nom_fichier):
        return send_file(nom_fichier, as_attachment=True)
    
    return "Fichier introuvable. Veuillez relancer la simulation.", 404

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌍 WEB APPLICATION INITIALISÉE AVEC SUCCÈS")
    print("👉 VEUILLEZ OUVRIR LE LIEN SUIVANT : http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(debug=True, use_reloader=False, port=5000)