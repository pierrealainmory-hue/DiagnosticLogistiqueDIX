import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="PNR Préalpes - Dashboard Logistique",
    page_icon="📊",
    layout="wide"
)

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stDataFrame { background-color: white; border-radius: 10px; }
    h1, h2, h3 { color: #2c3e50; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION SUPABASE ---
SUPABASE_URL = "https://lxoqhmfpnodyfnavmhmn.supabase.co"
SUPABASE_KEY = "sb_publishable_-LPq5CilDsNJcBuOKSG_hw_2nZUZrYg" 

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Erreur de connexion à la base de données : {e}")

# --- CHARGEMENT ET TRAITEMENT DES DONNÉES ---
@st.cache_data(ttl=300) # Cache de 5 minutes
def load_and_process_data():
    try:
        # 1. Récupérer les projets envoyés
        response = supabase.table("tournees").select("*").execute()
        if not response.data:
            return pd.DataFrame(), pd.DataFrame()
        
        raw_df = pd.DataFrame(response.data)
        
        # 2. Aplatir les données des tournées
        rows = []
        for _, entry in raw_df.iterrows():
            json_content = entry['data_json']
            tours = json_content.get('tours', [])
            nom_prod = entry['nom_producteur']
            date_envoi = pd.to_datetime(entry['created_at'])
            
            for t in tours:
                stats = t.get('stats', {})
                rows.append({
                    "ID_Projet": entry['id'],
                    "Producteur": nom_prod,
                    "Date": date_envoi.strftime('%d/%m/%Y'),
                    "Tournée": t.get('name', 'Sans nom'),
                    "Jour": t.get('day', 'Inconnu'),
                    "CA (€)": float(stats.get('ca', 0)),
                    "Coût (€)": float(stats.get('cost', 0)),
                    "Ratio (%)": float(stats.get('ratio', 0)),
                    "Distance (km)": float(stats.get('dist', 0)),
                    "Temps (min)": float(stats.get('time', 0)),
                    "Nb Arrêts": len(t.get('stops', []))
                })
        
        analysis_df = pd.DataFrame(rows)
        return analysis_df, raw_df
    except Exception as e:
        st.error(f"Erreur lors du traitement des données : {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- INTERFACE PRINCIPALE ---
st.title("📊 Diagnostic Logistique Territorial")
st.markdown("#### Parc Naturel Régional des Préalpes d'Azur")

data, raw_data = load_and_process_data()

if data.empty:
    st.info("👋 Bienvenue ! Aucune donnée n'a été transmise par les producteurs pour le moment.")
    st.image("https://www.parcs-naturels-regionaux.fr/sites/federationpnr/files/styles/contenu/public/image/parc/sans_titre.png?itok=z_7I7Msh", width=200)
else:
    # --- BARRE LATÉRALE ---
    st.sidebar.image("https://www.parcs-naturels-regionaux.fr/sites/federationpnr/files/styles/contenu/public/image/parc/sans_titre.png?itok=z_7I7Msh", width=150)
    st.sidebar.header("Filtres d'analyse")
    
    selected_prods = st.sidebar.multiselect(
        "Producteurs", 
        options=sorted(data["Producteur"].unique()),
        default=sorted(data["Producteur"].unique())
    )
    
    selected_days = st.sidebar.multiselect(
        "Jours de livraison", 
        options=["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
        default=["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    )

    filtered_df = data[(data["Producteur"].isin(selected_prods)) & (data["Jour"].isin(selected_days))]

    # --- INDICATEURS CLÉS (KPI) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Projets Reçus", len(raw_data))
    with c2:
        st.metric("CA Cumulé", f"{filtered_df['CA (€)'].sum():,.0f} €")
    with c3:
        avg_ratio = filtered_df['Ratio (%)'].mean()
        st.metric("Ratio Moyen", f"{avg_ratio:.1f} %", delta="-20%" if avg_ratio > 20 else None, delta_color="inverse")
    with c4:
        st.metric("Distance Totale", f"{filtered_df['Distance (km)'].sum():,.0f} km")

    st.markdown("---")

    # --- GRAPHIQUES ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("💰 Équilibre Économique par Producteur")
        fig_bar = px.bar(
            filtered_df, 
            x="Producteur", 
            y=["CA (€)", "Coût (€)"],
            barmode="group",
            color_discrete_sequence=["#27ae60", "#e74c3c"],
            template="plotly_white"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.subheader("🎯 Efficacité Logistique (Ratio vs CA)")
        fig_scatter = px.scatter(
            filtered_df,
            x="CA (€)",
            y="Ratio (%)",
            size="Distance (km)",
            color="Producteur",
            hover_name="Tournée",
            template="plotly_white",
            size_max=40
        )
        # Ligne de seuil de rentabilité critique
        fig_scatter.add_hline(y=20, line_dash="dot", line_color="#e67e22", annotation_text="Seuil critique")
        st.plotly_chart(fig_scatter, use_container_width=True)

    # --- TABLEAU DÉTAILLÉ ---
    st.subheader("📑 Registre des Tournées Analysées")
    
    # Formatage spécifique pour le tableau
    st.dataframe(
        filtered_df.sort_values(by="Ratio (%)", ascending=False),
        column_config={
            "Ratio (%)": st.column_config.ProgressColumn(
                "Ratio Log.",
                help="Coût divisé par le CA",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "CA (€)": st.column_config.NumberColumn("CA (€)", format="%.2f €"),
            "Coût (€)": st.column_config.NumberColumn("Coût (€)", format="%.2f €"),
            "Nb Arrêts": st.column_config.NumberColumn("Arrêts", format="%d 🛑"),
        },
        use_container_width=True,
        hide_index=True
    )

    # --- EXPORTATION ---
    st.markdown("### 📥 Export des données")
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Télécharger le rapport CSV pour Excel",
        data=csv,
        file_name=f"diagnostic_pnr_{datetime.date.today()}.csv",
        mime='text/csv',
    )

# --- PIED DE PAGE ---
st.markdown("---")
st.caption(f"© 2026 DIX Autrement - Dashboard d'Analyse Territoriale | Dernière mise à jour : {datetime.datetime.now().strftime('%H:%M:%S')}")
