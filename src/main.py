import streamlit as st
import pandas as pd
import json
import random
import pydeck as pdk
from supabase import create_client

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Diagnostic Territorial - Logistique", layout="wide")

# --- CONNEXION SUPABASE ---
SUPABASE_URL = "https://lxoqhmfpnodyfnavmhmn.supabase.co"
SUPABASE_KEY = "sb_publishable_-LPq5CilDsNJcBuOKSG_hw_2nZUZrYg"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# --- FONCTIONS UTILITAIRES ---
def get_random_color(seed_str):
    """Génère une couleur unique et fixe pour chaque producteur"""
    random.seed(seed_str)
    return [random.randint(50, 255), random.randint(50, 255), random.randint(50, 255), 200]

def load_data():
    """Charge et nettoie les données brutes"""
    try:
        response = supabase.table("tournees").select("*").execute()
        raw_data = response.data
        if not raw_data: return None
        return raw_data
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return None

# --- 1. CHARGEMENT ET PREPARATION ---
st.title("🗺️ Diagnostic Logistique Territorial")
st.markdown("**Visualisation des flux et potentiels de mutualisation**")

raw_rows = load_data()

if not raw_rows:
    st.warning("Aucune donnée disponible pour le moment.")
    st.stop()

# Transformation des données
all_tours = []
all_paths = [] 
all_points = [] 

for row in raw_rows:
    prod_name = row.get("nom_producteur", "Inconnu")
    prod_color = get_random_color(prod_name) 
    
    content = row.get("data_json", {})
    if isinstance(content, str):
        try: content = json.loads(content)
        except: content = {}
    
    depot_coords = content.get("depot", {}).get("pData", {})
    depot_lat = depot_coords.get("lat")
    depot_lon = depot_coords.get("lon")
    
    tours = content.get("tours", [])
    
    for t in tours:
        day = t.get("day", "Indéfini")
        tour_name = t.get("name", "Sans nom")
        stops = t.get("stops", [])
        stats = t.get("stats", {})
        
        all_tours.append({
            "Producteur": prod_name,
            "Jour": day,
            "Tournée": tour_name,
            "Coût": float(stats.get("cost", 0)),
            "Distance": float(stats.get("dist", 0)),
            "Volume (kg)": sum([float(s.get("vol", 0)) for s in stops]),
            "Nb Arrêts": len(stops),
            "Vehicule": content.get("depot", {}).get("veh", {}).get("type", "?")
        })

        if depot_lat and depot_lon:
            path_coords = [[depot_lon, depot_lat]] 
            
            # Dépôt
            all_points.append({
                "name": f"Dépôt: {prod_name}",
                "coordinates": [depot_lon, depot_lat],
                "color": [0, 0, 0, 255], 
                "radius": 200,
                "type": "Depot",
                "prod": prod_name,
                "day": day
            })

            # Arrêts
            for s in stops:
                if s.get("lat") and s.get("lon"):
                    coord = [s.get("lon"), s.get("lat")]
                    path_coords.append(coord)
                    
                    all_points.append({
                        "name": f"{s.get('client')} ({prod_name})",
                        "coordinates": coord,
                        "color": prod_color,
                        "radius": 100,
                        "type": "Livraison",
                        "prod": prod_name,
                        "day": day
                    })
            
            path_coords.append([depot_lon, depot_lat])

            all_paths.append({
                "path": path_coords,
                "color": prod_color,
                "name": f"{prod_name} - {day}",
                "prod": prod_name,
                "day": day
            })

df = pd.DataFrame(all_tours)

# --- 2. FILTRES LATERAUX ---
st.sidebar.header("🔍 Filtres d'Analyse")

days_avail = df["Jour"].unique() if not df.empty else []
selected_days = st.sidebar.multiselect("Jours de la semaine", days_avail, default=days_avail)

prods_avail = df["Producteur"].unique() if not df.empty else []
selected_prods = st.sidebar.multiselect("Producteurs", prods_avail, default=prods_avail)

if not df.empty:
    df_filtered = df[df["Jour"].isin(selected_days) & df["Producteur"].isin(selected_prods)]
    filtered_paths = [p for p in all_paths if p["day"] in selected_days and p["prod"] in selected_prods]
    filtered_points = [p for p in all_points if p["day"] in selected_days and p["prod"] in selected_prods]
else:
    df_filtered = df
    filtered_paths = []
    filtered_points = []

# --- 3. KPIs ---
st.subheader("📊 Indicateurs de Performance Territoriale")

if not df_filtered.empty:
    total_km = df_filtered["Distance"].sum()
    total_stops = df_filtered["Nb Arrêts"].sum()
    total_vol = df_filtered["Volume (kg)"].sum()
    total_cost = df_filtered["Coût"].sum()
    
    kpi_density = total_km / total_stops if total_stops > 0 else 0
    kpi_unit_cost = total_cost / total_vol if total_vol > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flux Totaux", f"{total_km:.0f} km", help="Cumul des distances")
    c2.metric("Points Livrés", f"{total_stops}", help="Nombre total d'arrêts")
    c3.metric("Densité Logistique", f"{kpi_density:.1f} km/arrêt", delta_color="inverse", help="Km moyen entre deux arrêts")
    c4.metric("Coût Unitaire", f"{kpi_unit_cost:.2f} €/kg", delta_color="inverse", help="Coût de transport par kg")

    # --- 4. LA CARTE (CORRIGÉE AVEC FOND CARTO) ---
    st.subheader(f"📍 Carte des Flux ({len(selected_prods)} producteurs)")

    if filtered_paths:
        init_lat = filtered_points[0]["coordinates"][1] if filtered_points else 43.7
        init_lon = filtered_points[0]["coordinates"][0] if filtered_points else 6.5

        view_state = pdk.ViewState(latitude=init_lat, longitude=init_lon, zoom=9, pitch=0)

        layer_paths = pdk.Layer(
            "PathLayer",
            filtered_paths,
            pickable=True,
            get_color="color",
            width_scale=20,
            width_min_pixels=2,
            get_path="path",
            get_width=5
        )

        layer_points = pdk.Layer(
            "ScatterplotLayer",
            filtered_points,
            pickable=True,
            get_position="coordinates",
            get_color="color",
            get_radius="radius",
            radius_min_pixels=4,
            radius_max_pixels=10
        )

        r = pdk.Deck(
            layers=[layer_paths, layer_points],
            initial_view_state=view_state,
            tooltip={"text": "{name}\nProducteur: {prod}"},
            # C'EST ICI QUE CA CHANGE : Utilisation d'un style CartoDB gratuit
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
        )
        st.pydeck_chart(r)
        
        st.caption("ℹ️ Les lignes représentent les flux théoriques. Chaque couleur est un producteur.")

    else:
        st.info("Sélectionnez des jours/producteurs pour voir la carte.")

    with st.expander("Voir le détail des tournées"):
        st.dataframe(df_filtered)

else:
    st.info("Aucune donnée ne correspond aux filtres.")
