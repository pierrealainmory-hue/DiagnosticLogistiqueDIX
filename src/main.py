import streamlit as st
import pandas as pd
import os

# 1. Configuration de la page
st.set_page_config(page_title="Logistique DIX", layout="wide")
st.title("🚛 Diagnostic Logistique DIX - Importation")

# 2. Gestion du dossier de sauvegarde
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 3. Zone de chargement de fichier
st.write("### 1. Chargement des données")
st.info("Le fichier sera sauvegardé localement pour éviter la perte de données.")

uploaded_file = st.file_uploader("Déposez votre fichier CSV ici (Export Optim)", type=['csv'])

if uploaded_file is not None:
    # A. On définit le chemin de sauvegarde
    save_path = os.path.join(DATA_DIR, "fichier_actuel.csv")
    
    # B. On écrit le fichier sur le disque (Sauvegarde physique)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"✅ Fichier sauvegardé sous : {save_path}")

    # C. Lecture et affichage d'un aperçu
    try:
        # Essai de lecture standard (séparateur virgule)
        df = pd.read_csv(save_path)
        
        # Si le fichier a une seule colonne, c'est souvent un problème de séparateur (point-virgule ?)
        if df.shape[1] < 2:
            df = pd.read_csv(save_path, sep=';')

        st.write("### 2. Aperçu des données reçues")
        st.write(f"Dimensions : {df.shape[0]} lignes x {df.shape[1]} colonnes")
        st.dataframe(df.head())
        
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")

else:
    st.warning("En attente d'un fichier...")

