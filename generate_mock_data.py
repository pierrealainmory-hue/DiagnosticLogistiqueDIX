import pandas as pd
import random
from datetime import datetime, timedelta

# Création de fausses données réalistes
data = []
producteurs = ["Ferme du Val", "BioJardin", "Vergers de l'Est"]
clients = ["Restaurant A", "Cantine B", "Epicerie C", "Marché D"]
tournee_base_id = 2026011100

for i in range(50):  # On génère 50 lignes
    prod = random.choice(producteurs)
    tournee_id = f"{prod}_{tournee_base_id + random.randint(1, 5)}"
    
    data.append({
        "P_Date": 20260111,
        "Tournée ID": tournee_id,
        "Producteur": prod,
        "Ordre d'Arrêt": random.randint(1, 10),
        "Type Arrêt": random.choice(["Livraison", "Collecte"]),
        "Client / Point de Livraison": random.choice(clients),
        "Poids (kg)": random.randint(10, 200),
        "Montant (€)": random.randint(50, 500),
        "Temps d'arrêt (min)": 15
    })

df = pd.DataFrame(data)

# Sauvegarde dans le dossier data
df.to_csv("data/donnees_test_valides.csv", index=False)
print("✅ Fichier 'data/donnees_test_valides.csv' généré avec succès !")
