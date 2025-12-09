def agent_diagnostiqueur(reference: str, panne: str) -> str:
    """Agent 1: Diagnostiqueur électrique via Perplexity."""
    product = get_product_by_ref(reference)
    product_name = product['name'] if product else "produit inconnu"
    
    prompt = f"""Tu es un électricien expert Somfy tertiaire avec 20 ans d'expérience.

Produit: {product_name} (ref {reference})
Panne décrite: {panne}

Génère un DIAGNOSTIC ÉLECTRIQUE COMPLET avec:

1. **VÉRIFICATIONS DE SÉCURITÉ**
   - Coupure d'alimentation générale obligatoire
   - Attendre 5 minutes minimum pour décharge
   - Équipement de protection personnelle (gants isolants)
   - Vérifier absence de tension avec testeur sans contact

2. **MESURE TENSION BUS IB/IB+**
   - Multimètre en mode DC 24V
   - Mesurer entre IB+ (rouge) et C/masse (noir)
   - Valeur attendue: 16V DC ± 0,5V (15,5V - 16,5V acceptable)
   - Si <14V: problème de source ou rupture câble
   - Si >18V: DANGER - arrêter immédiatement et contacter support
   - Tester aussi aux deux extrémités du câble (source et boîtier)

3. **TESTS DE CONTINUITÉ**
   - Multimètre en mode Ohm/continuité
   - Vérifier IB+ in (arrivée depuis contrôleur) - doit sonner
   - Vérifier IB+ out (départ vers motor controllers) - doit sonner
   - Vérifier Subzone 1 et 2 (sorties indépendantes)
   - Vérifier Switch in (entrée bouton) - doit sonner
   - Chercher: ruptures de câble, court-circuits, bornes desserrées
   - Vérifier isolation (pas de court sur masse)

4. **ARBRE DE DÉCISION**
   - SI tension absence complète → vérifier alimentation source 230V
   - SI tension trop basse → chercher rupture câble ou résistance haute
   - SI continuité cassée → câble rompu, à remplacer
   - SI tout OK électriquement → problème logiciel/paramétrage

5. **CONCLUSION**
   - Diagnostic clair et actionnable
   - Pièces à tester ou remplacer si nécessaire
   - Quand appeler support Somfy Pro
   - Recommandations de sécurité

Format: clair, numéroté, professionnel, pour électricien sur site."""
    
    return call_perplexity(prompt)
