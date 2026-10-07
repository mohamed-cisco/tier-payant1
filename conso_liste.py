def consommations(request):
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

    if "CONSOMMATION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les consommations."
        )
        return redirect("accueil")

    consommations = (
        Consommation.objects
        .select_related(
            "id_detail_pec",
            "id_personne_beneficiaire",
            "id_adhesion",
            "id_acte",
            "id_garantie",
            "id_prestataire",
        )
        .order_by("-id_consommation")
    )

    return render(
        request,
        "core/consommations.html",
        {
            "consommations": consommations,
            "permissions": permissions,
            "page": "consommations",
        }
    )



