import streamlit as st
import pandas as pd
import os
import plotly.express as px

# 1. CONFIGURATION DE LA PAGE
st.set_page_config(page_title="Logistique DIX - Analyse", layout="wide")

st.title("🚛 Diagnostic Logistique DIX")
st.markdown("---")

# 2. GESTION DU FICHIER LOCAL
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 3. BARRE LATÉRALE : IMPORTATION
with st.sidebar:
    st.header("1. Importation")
    uploaded_file = st.file_uploader("Charger un fichier CSV", type=['csv'])
    
    # Bouton de rechargement pour les tests
    if st.button("Recharger les données"):
        st.rerun()

# Fonction de chargement avec cache pour la rapidité
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        # Nettoyage basique si nécessaire
        return df
    except Exception as e:
        return None

# 4. LOGIQUE PRINCIPALE
current_file_path = os.path.join(DATA_DIR, "fichier_actuel.csv")

# Si l'utilisateur vient d'uploader un fichier, on l'écrase
if uploaded_file is not None:
    with open(current_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success("Fichier mis à jour !")

# Si le fichier existe sur le disque, on l'analyse
if os.path.exists(current_file_path):
    df = load_data(current_file_path)
    
    if df is not None:
        # --- SECTION ANALYSE ---
        
        st.subheader("2. Vue d'ensemble")
        
        # Calcul des KPIs (Indicateurs Clés)
        total_poids = df["Poids (kg)"].sum()
        nb_tournees = df["Tournée ID"].nunique()
        nb_clients = df["Client / Point de Livraison"].nunique()
        
        # Affichage des KPIs en colonnes
        col1, col2, col3 = st.columns(3)
        col1.metric("Poids Total", f"{total_poids} kg")
        col2.metric("Tournées Identifiées", nb_tournees)
        col3.metric("Points livrés", nb_clients)
        
        st.markdown("---")
        
        # --- SECTION GRAPHIQUES ---
        col_graph1, col_graph2 = st.columns(2)
        
        with col_graph1:
            st.subheader("Répartition par Producteur (Poids)")
            # Groupement des données
            df_prod = df.groupby("Producteur")["Poids (kg)"].sum().reset_index()
            # Graphique à barres interactif
            fig_bar = px.bar(df_prod, x="Producteur", y="Poids (kg)", color="Producteur")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_graph2:
            st.subheader("Types d'arrêts")
            # Camembert
            fig_pie = px.pie(df, names="Type Arrêt", title="Distribution Livraison vs Collecte")
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- SECTION DÉTAIL ---
        with st.expander("Voir les données brutes"):
            st.dataframe(df)
            
    else:
        st.error("Erreur de lecture du fichier.")
else:
    st.info("👈 Veuillez charger un fichier CSV dans la barre latérale.")
