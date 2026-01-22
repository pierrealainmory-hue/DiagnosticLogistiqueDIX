cat > src/catl.py <<EOL
import streamlit as st
import pandas as pd
import json
import random
import pydeck as pdk
from supabase import create_client

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Diagnostic Logistique - CATL", layout="wide")

# --- CONNEXION SUPABASE ---
# Utilisation des mêmes clés, mais on pointera vers une autre table
SUPABASE_URL = "https://lxoqhmfpnodyfnavmhmn.supabase.co"
SUPABASE_KEY = "sb_publishable_-LPq5CilDsNJcBuOKSG_hw_2nZUZrYg"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# --- FONCTIONS UTILITAIRES ---
def get_random_color(seed_str):
    random.seed(seed_str)
    return [random.randint(50, 200), random.randint(50, 200), random.randint(50, 200), 200]

def load_data():
    try:
        # CIBLE : TABLE CATL
        response = supabase.table("tournees_catl").select("*").execute()
        raw_data = response.data
        if not raw_data: return None
        return raw_data
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return None

# --- CHARGEMENT ---
st.title("🗺️ Diagnostic Logistique - CATL")
st.markdown("**Visualisation des flux de la Ceinture Aliment-Terre de Liège**")

raw_rows = load_data()

if not raw_rows:
    st.warning("Aucune donnée disponible pour le moment.")
    st.stop()

# --- PREPARATION DES DONNEES ---
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
    
    # Infos Dépôt
    depot_data = content.get("depot", {})
    depot_coords = depot_data.get("pData", {})
    vehicle_type = depot_data.get("veh", {}).get("type", "Non précisé")
    
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
            "Véhicule": vehicle_type,
            "Coût": float(stats.get("cost", 0)),
            "Distance": float(stats.get("dist", 0)),
            "Volume (kg)": sum([float(s.get("vol", 0)) for s in stops]),
            "Nb Arrêts": len(stops)
        })

        if depot_lat and depot_lon:
            path_coords = [[depot_lon, depot_lat]] 
            
            all_points.append({
                "name": f"DEPOT: {prod_name}",
                "coordinates": [depot_lon, depot_lat],
                "color": [30, 30, 30, 255],
                "radius": 250,
                "type": "Depot",
                "prod": prod_name,
                "day": day,
                "veh": vehicle_type
            })

            for s in stops:
                if s.get("lat") and s.get("lon"):
                    coord = [s.get("lon"), s.get("lat")]
                    path_coords.append(coord)
                    
                    all_points.append({
                        "name": f"{s.get('client')} ({prod_name})",
                        "coordinates": coord,
                        "color": prod_color,
                        "radius": 120,
                        "type": "Livraison",
                        "prod": prod_name,
                        "day": day,
                        "veh": vehicle_type
                    })
            
            path_coords.append([depot_lon, depot_lat])

            all_paths.append({
                "path": path_coords,
                "color": prod_color,
                "name": f"{prod_name} ({day})",
                "prod": prod_name,
                "day": day,
                "veh": vehicle_type
            })

df = pd.DataFrame(all_tours)

# --- FILTRES ---
st.sidebar.title("🎛️ Filtres CATL")

if not df.empty:
    prods_list = sorted(df["Producteur"].unique())
    st.sidebar.markdown(f"**👨‍🌾 Producteurs ({len(prods_list)})**")
    selected_prods = st.sidebar.multiselect("Sélectionner:", prods_list, default=prods_list)
    
    st.sidebar.markdown("---")

    week_order = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    days_present = df["Jour"].unique()
    days_sorted = sorted(days_present, key=lambda x: week_order.index(x) if x in week_order else 99)
    st.sidebar.markdown(f"**📅 Jours ({len(days_sorted)})**")
    selected_days = st.sidebar.multiselect("Sélectionner:", days_sorted, default=days_sorted)

    st.sidebar.markdown("---")

    veh_list = sorted(df["Véhicule"].unique())
    st.sidebar.markdown(f"**🚚 Flotte ({len(veh_list)})**")
    selected_vehs = st.sidebar.multiselect("Type:", veh_list, default=veh_list)

    mask = (df["Producteur"].isin(selected_prods) & df["Jour"].isin(selected_days) & df["Véhicule"].isin(selected_vehs))
    df_filtered = df[mask]
    
    filtered_paths = [p for p in all_paths if p["prod"] in selected_prods and p["day"] in selected_days and p["veh"] in selected_vehs]
    filtered_points = [p for p in all_points if p["prod"] in selected_prods and p["day"] in selected_days and p["veh"] in selected_vehs]

else:
    df_filtered = df
    filtered_paths = []
    filtered_points = []

# --- KPI ---
if not df_filtered.empty:
    st.markdown("### 📊 Performance Territoriale")
    
    total_km = df_filtered["Distance"].sum()
    total_stops = df_filtered["Nb Arrêts"].sum()
    total_vol = df_filtered["Volume (kg)"].sum()
    total_cost = df_filtered["Coût"].sum()
    
    kpi_density = total_km / total_stops if total_stops > 0 else 0
    kpi_unit = total_cost / total_vol if total_vol > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flux Cumulés", f"{total_km:,.0f} km")
    c2.metric("Arrêts Desservis", f"{total_stops}")
    c3.metric("Densité (Km/Arrêt)", f"{kpi_density:.1f} km", delta_color="inverse")
    c4.metric("Coût Unitaire", f"{kpi_unit:.2f} €/kg", delta_color="inverse")

    # --- CARTE ---
    st.markdown("### 📍 Visualisation des Flux")
    
    if filtered_paths:
        init_lat = filtered_points[0]["coordinates"][1]
        init_lon = filtered_points[0]["coordinates"][0]
        view_state = pdk.ViewState(latitude=init_lat, longitude=init_lon, zoom=10)

        layer_paths = pdk.Layer(
            "PathLayer",
            filtered_paths,
            get_color="color",
            width_scale=20,
            width_min_pixels=3,
            get_path="path",
            get_width=5,
            pickable=True
        )

        layer_points = pdk.Layer(
            "ScatterplotLayer",
            filtered_points,
            get_position="coordinates",
            get_color="color",
            get_radius="radius",
            radius_min_pixels=5,
            radius_max_pixels=15,
            pickable=True
        )

        r = pdk.Deck(
            layers=[layer_paths, layer_points],
            initial_view_state=view_state,
            tooltip={"text": "{name}\nProducteur: {prod}\nVéhicule: {veh}"},
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
        )
        st.pydeck_chart(r)
    else:
        st.info("Sélection vide.")

    st.markdown("### 📋 Détail Chiffré")
    st.dataframe(df_filtered.style.format({"Coût": "{:.2f} €", "Distance": "{:.1f} km", "Volume (kg)": "{:.0f} kg"}), use_container_width=True)

else:
    st.warning("Aucune donnée.")
EOL
