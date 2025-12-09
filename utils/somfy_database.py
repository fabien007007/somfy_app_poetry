"""Base de données Somfy - Produits & Documentation"""

SOMFY_PRODUCTS = {
    "1810392": {
        "name": "Animeo Switch Zone Splitter",
        "type": "Séparateur de zone IB/IB+",
        "norms": "CE, 16V SELV, NFC 15-100",
        "specs": (
            "- Découpe une zone IB+ en 1 ou 2 sous-zones\n"
            "- Entrée IB+ : 16 V DC SELV\n"
            "- 2 sorties IB+ Subzone indépendantes\n"
            "- Entrée switch pour bouton Smoove Origin IB\n"
            "- Boîtier IP65, -10 °C à +60 °C"
        ),
        "connections": (
            "- IB+ in / C : arrivée bus 16 V DC + masse\n"
            "- IB+ out : sortie vers motor controllers\n"
            "- IB+ Subzone 1 & 2 : sorties indépendantes\n"
            "- Switch in : entrée bouton Smoove"
        ),
        "use_cases": (
            "- Gestion stores/volets par zone en tertiaire\n"
            "- Création de sous-zones pilotage indépendant\n"
            "- Intégration domotique Somfy animeo"
        ),
        "documents": [
            {
                "title": "Notice d'installation Animeo Switch Zone Splitter 1810392",
                "url": "https://service.somfy.com/downloads/bui_v4/animeoswitch-zone-splitter_1810392_20181230.pdf",
            },
            {
                "title": "Fiche produit Somfy Pro",
                "url": "https://www.somfypro.fr/produits/1810392-animeo-switch-zone-splitter",
            },
        ],
    },
    "1811272": {
        "name": "Smoove Origin IB",
        "type": "Commande murale IB+",
        "norms": "CE, 16V SELV",
        "specs": "- Commande locale pour bus IB+\n- Fonctions montée/descente/stop",
        "connections": "- Connexion sur bus IB+ via bornier",
        "use_cases": "Commande locale stores/volets tertiaire",
        "documents": [
            {
                "title": "Notice Smoove Origin IB",
                "url": "https://www.somfypro.fr/produits/1811272-smoove-origin-ib",
            }
        ],
    },
}

def get_product_by_ref(reference: str):
    """Retourne les infos produit par référence."""
    return SOMFY_PRODUCTS.get(reference)

def search_products_by_keyword(keyword: str):
    """Cherche des produits par mot-clé."""
    results = []
    for ref, product in SOMFY_PRODUCTS.items():
        if keyword.lower() in product["name"].lower() or keyword.lower() in product["type"].lower():
            results.append((ref, product))
    return results
