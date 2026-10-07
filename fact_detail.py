def facture_detail(request, id_facture):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "FACTURE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("factures")

    try:
        facture = (
            Facture.objects
            .select_related("id_prestataire")
            .get(id_facture=id_facture)
        )
    except Facture.DoesNotExist:
        messages.error(request, "Facture introuvable.")
        return redirect("factures")

    details = (
        DetailFacture.objects
        .select_related("id_consommation", "id_acte")
        .filter(id_facture=facture)
        .order_by("id_detail_facture")
    )

    champs = get_valeurs_champs_entite("FACTURE", facture.id_facture)
    champs = [c for c in champs if c["valeur"] and str(c["valeur"]).strip()]

    return render(
        request,
        "core/facture_detail.html",
        {
            "facture": facture,
            "details": details,
            "champs_personnalises": champs,
            "page": "factures",
        }
    )



def _generer_reference_reglement(mode_reglement):
    """Génère une référence unique pour un règlement selon son mode."""
    annee = timezone.now().year

    prefixes = {
        "VIREMENT": f"VIR-{annee}-",
        "CHEQUE": f"CHQ-{annee}-",
        "ESPECES": f"ESP-{annee}-",
    }

    prefixe = prefixes.get(mode_reglement, f"REF-{annee}-")

    # Récupère toutes les références existantes pour ce préfixe
    references = (
        Reglement.objects
        .filter(reference_reglement__startswith=prefixe)
        .values_list("reference_reglement", flat=True)
    )

    valeurs = []
    for ref in references:
        try:
            valeurs.append(int(ref.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    reference = f"{prefixe}{prochain:04d}"

    # Vérifie l'unicité
    while Reglement.objects.filter(
        reference_reglement=reference
    ).exists():
        prochain += 1
        reference = f"{prefixe}{prochain:04d}"

    return reference
def _generer_numero_reglement():
    """Génère un numéro de règlement unique."""
    annee = timezone.now().year
    prefixe = f"REG-{annee}-"

    numeros = (
        Reglement.objects
        .filter(numero_reglement__startswith=prefixe)
        .values_list("numero_reglement", flat=True)
    )

