def documents(request):
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
            "Vous n'avez pas l'autorisation de consulter les documents."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    documents = (
        Document.objects
        .select_related("id_utilisateur")
        .all()
        .order_by("-date_depot")
    )

    if recherche:
        documents = documents.filter(
            Q(nom_fichier__icontains=recherche)
            | Q(type_document__icontains=recherche)
            | Q(extension__icontains=recherche)
            | Q(hash_fichier__icontains=recherche)
        )

    if statut:
        documents = documents.filter(statut=statut)

    statuts = (
        Document.objects
        .exclude(statut__isnull=True)
        .exclude(statut="")
        .values_list("statut", flat=True)
        .distinct()
        .order_by("statut")
    )

    return render(
        request,
        "core/documents.html",
        {
            "documents": documents,
            "permissions": permissions,
            "recherche": recherche,
            "statut": statut,
            "statuts": statuts,
            "page": "documents",
        }
    )
