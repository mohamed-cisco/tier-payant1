def recours(request):
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

    if "RECOURS_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les recours."
        )
        return redirect("accueil")

    recours_list = (
        Recours.objects
        .select_related("id_personne")
        .all()
        .order_by("-id_recours")
    )

    return render(
        request,
        "core/recours.html",
        {
            "recours": recours_list,
            "permissions": permissions,
            "page": "recours",
        }
    )

