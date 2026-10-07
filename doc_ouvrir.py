def document_ouvrir(request, id_document):
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

    if "DOCUMENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ouvrir ce document."
        )
        return redirect("documents")

    try:
        document = Document.objects.get(
            id_document=id_document
        )
    except Document.DoesNotExist:
        messages.error(
            request,
            "Document introuvable."
        )
        return redirect("documents")

    if not default_storage.exists(document.emplacement):
        messages.error(
            request,
            "Le fichier physique est introuvable."
        )
        return redirect("documents")

    fichier = default_storage.open(
        document.emplacement,
        "rb"
    )

    response = FileResponse(
        fichier,
        as_attachment=False,
        filename=document.nom_fichier
    )

    return response

