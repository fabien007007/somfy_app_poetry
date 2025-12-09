def agent_documenteur(reference: str) -> str:
    """Agent 3: Documenteur (Perplexity + PDF Somfy)."""
    product = get_product_by_ref(reference)
    
    if not product:
        return f"❌ Aucune documentation trouvée pour référence {reference}"
    
    prompt = f"""Tu es un formateur Somfy certifié pour installateurs électriciens tertiaire.

Produit: {product['name']} (ref {reference})

Génère une PROCÉDURE DÉTAILLÉE ET COMPLÈTE de mise en service avec:

**ÉTAPE 1 - PRÉPARATION ET SÉCURITÉ**
- Liste complète du matériel nécessaire:
  * Multimètre numérique (catégorie III minimum)
  * Tournevisses isolés (plat + cruciforme)
  * Câbles électriques 0.75mm² (si raccordement)
  * Gants isolants 1000V minimum
  * Testeur sans contact pour tension
- Points de sécurité absolus à respecter
- Normes applicables: NFC 15-100, SELV, CE
- Vérifications préalables sur installation existante

**ÉTAPE 2 - RACCORDEMENTS ÉLECTRIQUES**
- Procédure raccordement IB+ in et C (alimentation 16V + masse)
  * Clémence et serrage (couple recommandé si applicable)
  * Orientation des câbles (pas d'épingle)
- Raccordement IB+ out (vers motor controllers)
  * Longueur maximale câble recommandée
- Raccordement Subzone 1 et 2 (si applicable)
  * Isolation des sorties entre elles
- Raccordement Switch in (bouton ou poussoir)
  * Type de bouton compatible
- Points d'attention particuliers (ex: pas de croisement avec 230V)

**ÉTAPE 3 - MESURE TENSION 16V DC**
- Préparation multimètre (sélecteur sur DC 24V)
- Où mesurer exactement (points de mesure sur le boîtier)
- Valeur attendue: 16V DC (15,5V - 16,5V acceptable)
- Que faire si tension incorrecte:
  * Trop basse → diagnostiquer source
  * Trop haute → arrêter immédiatement
  * Absente → vérifier continuité câbles
- Mesurer aussi aux deux bouts du câble (différence = chute de tension)

**ÉTAPE 4 - TESTS DE FONCTIONNEMENT**
- Test basique: commander montée/descente/stop des volets
  * Depuis bouton Smoove/poussoir
  * Vérifier mouvements fluides et symétriques
- Test LED et signalisation du boîtier
  * Quelles LED doivent allumer
  * Clignotements normaux vs anormaux
  * Codes d'erreur (si applicable)
- Valider indépendance 2 sous-zones (si applicable)
  * Chaque zone répond indépendamment
  * Pas d'interférence
- Tester en conditions extrêmes (si possible)
  * Volet complètement levé/baissé
  * Commandes rapides successives

**ÉTAPE 5 - VÉRIFICATIONS FINALES & MISE EN SERVICE**
- Checklist finale:
  ☐ Tension 16V stable
  ☐ Tous les raccordements serrés
  ☐ Continuité OK sur tous les câbles
  ☐ Fonctionnement OK montée/descente/stop
  ☐ LED/signalisation normales
  ☐ Documentation remplie avec date/technicien
- Erreurs fréquentes et solutions:
  * Boîtier ne réagit pas → vérifier tension
  * Mouvement lent → vérifier câble
  * Sous-zones ne réagissent pas indépendamment → raccordement
  * LED clignotent anormalement → voir doc produit
- Quand contacter support Somfy Pro:
  * Problèmes électriques non résolus
  * Codes erreur anormaux
  * Besoin expertise installation
- Maintenance recommandée:
  * Vérifier tension tous les 6 mois
  * Serrage bornes annuel
  * Nettoyage boîtier si nécessaire

Format: clair, étape par étape, professionnel, pour électricien tertiaire."""
    
    procedure = call_perplexity(prompt)
    
    # Ajouter les liens PDF Somfy
    docs = "\n### 📄 Notices officielles Somfy\n"
    for link in product["documents"]:
        docs += f"- **[{link['title']}]({link['url']})**\n"
    
    return f"## 📚 AGENT 3 - DOCUMENTATION & PROCÉDURES\n\n{procedure}\n{docs}"
