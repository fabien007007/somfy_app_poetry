def agent_somfy_specialist(reference: str) -> str:
    """Agent 2: Spécialiste Somfy (base de données)."""
    product = get_product_by_ref(reference)
    
    if not product:
        available = ", ".join(SOMFY_PRODUCTS.keys())
        return f"❌ Référence {reference} non trouvée.\n\nRéférences disponibles: {available}"
    
    return f"""## 🔧 AGENT 2 - SPÉCIALISTE SOMFY

**Référence:** {reference}
**Nom du produit:** {product['name']}
**Type:** {product['type']}
**Normes applicables:** {product['norms']}

### 📋 Caractéristiques principales
{product['specs']}

### 🔌 Raccordements électriques
{product['connections']}

### 💼 Cas d'usage typiques
{product['use_cases']}

---
*(Données issues de la base Somfy Pro)*"""
