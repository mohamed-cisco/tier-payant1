def reglement_detail(request, id_reglement):
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
            "Vous n'avez pas l'autorisation de consulter le détail du règlement."
        )
        return redirect("reglements")

    try:
        reglement = (
            Reglement.objects
            .select_related(
                "id_facture",
                "id_facture__id_prestataire",
            )
            .get(id_reglement=id_reglement)
        )
    except Reglement.DoesNotExist:
        messages.error(
            request,
            "Règlement introuvable."
        )
        return redirect("reglements")

    return render(
        request,
        "core/reglement_detail.html",
        {
            "reglement": reglement,
            "page": "reglements",
        }
    )

