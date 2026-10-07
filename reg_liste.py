def reglements(request):
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
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
    )

    if "REGLEMENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les règlements."
        )
        return redirect("accueil")

    reglements = (
        Reglement.objects
        .select_related(
            "id_facture",
            "id_facture__id_prestataire",
        )
        .order_by("-id_reglement")
    )

    for reglement in reglements:
        montant_deja_regle = (
            Reglement.objects
            .filter(
                id_facture=reglement.id_facture,
                statut="VALIDEE"
            )
            .aggregate(total=Sum("montant"))["total"]
            or Decimal("0")
        )

        reglement.montant_total_facture = reglement.id_facture.montant_valide
        reglement.montant_deja_regle = montant_deja_regle
        reglement.reste_a_payer = (
            reglement.id_facture.montant_valide - montant_deja_regle
        )

    return render(
        request,
        "core/reglements.html",
        {
            "reglements": reglements,
            "permissions": permissions,
            "page": "reglements",     # ← AJOUTE
        }
    )


