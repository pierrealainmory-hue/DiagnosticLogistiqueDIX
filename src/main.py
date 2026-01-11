import streamlit as st
import pandas as pd
import json
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Logistique DIX - PNR", layout="wide")

# VOS CLES SUPABASE
SUPABASE_URL = "https://lxoqhmfpnodyfnavmhmn.supabase.co"
SUPABASE_KEY = "sb_publishable_-LPq5CilDsNJcBuOKSG_hw_2nZUZrYg"

# Connexion
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.title("🚛 Tableau de Bord - PNR Préalpes d'Azur")
st.markdown("---")

# --- 2. RECUPERATION DES DONNEES ---
try:
    response = supabase.table("tournees").select("*").execute()
    raw_data = response.data
    
    if not raw_data:
        st.warning("📭 La connexion fonctionne, mais la table est vide.")
        st.stop()
        
except Exception as e:
    st.error(f"❌ Erreur de connexion : {e}")
    st.stop()

# --- 3. TRANSFORMATION (Avec sécurité JSON) ---
all_rows = []

for entry in raw_data:
    try:
        prod_name = entry.get("nom_producteur", "Inconnu")
        date_envoi = entry.get("created_at", "")[:10]
        
        # --- CORRECTION BLINDÉE ICI ---
        # On récupère le contenu
        content = entry.get("data_json", {})
        
        # Si c'est du texte (cas fréquent), on le transforme en dictionnaire
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                content = {} # Si ça échoue, on met vide pour ne pas planter
        
        # On récupère les tournées
        tours = content.get("tours", [])
        
        for t in tours:
            stats = t.get("stats", {})
            stops = t.get("stops", [])
            
            row = {
                "Producteur": prod_name,
                "Date Envoi": date_envoi,
                "Nom Tournée": t.get("name", "Sans nom"),
                "Jour": t.get("day", ""),
                "Coût Total (€)": float(stats.get("cost", 0)),
                "CA Tournée (€)": float(stats.get("ca", 0)),
                "Distance (km)": float(stats.get("dist", 0)),
                "Nb Arrêts": len(stops),
                "Poids Total (kg)": sum([float(s.get("vol", 0)) for s in stops])
            }
            all_rows.append(row)
            
    except Exception as e:
        # En cas d'erreur sur une ligne, on continue les autres
        print(f"Erreur sur une ligne : {e}")
        continue

# --- 4. AFFICHAGE ---
if all_rows:
    df = pd.DataFrame(all_rows)
    
    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Producteurs Actifs", df["Producteur"].nunique())
    col2.metric("Total Tournées", len(df))
    col3.metric("Volume Transporté", f"{int(df['Poids Total (kg)'].sum())} kg")
    
    st.markdown("---")
    
    # Graphiques
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Coût par Producteur")
        st.bar_chart(df, x="Producteur", y="Coût Total (€)", color="Producteur")
    
    with c2:
        st.subheader("Distance par Tournée")
        st.bar_chart(df, x="Nom Tournée", y="Distance (km)")
    
    # Données brutes
    st.subheader("Détail des réceptions")
    st.dataframe(df)
else:
    st.info("⚠️ Les données ont été reçues mais aucune tournée valide n'a pu être extraite.")
    with st.expander("Voir les données brutes pour débogage"):
        st.write(raw_data)

# Bouton de rechargement
if st.button("🔄 Rafraîchir les données"):
    st.rerun()
