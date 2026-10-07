def recours_detail(request, id_recours):
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
        return redirect("recours")

    try:
        recours_obj = (
            Recours.objects
            .select_related("id_personne")
            .get(id_recours=id_recours)
        )
    except Recours.DoesNotExist:
        messages.error(
            request,
            "Recours introuvable."
        )
        return redirect("recours")

    documents_lies = (
        RecoursDocument.objects
        .select_related(
            "id_document",
            "id_document__id_utilisateur",
        )
        .filter(id_recours=recours_obj)
        .order_by("-date_ajout")
    )

    return render(
        request,
        "core/recours_detail.html",
        {
            "recours": recours_obj,
            "documents_lies": documents_lies,
            "permissions": permissions,
            "page": "recours",
        }
    )

