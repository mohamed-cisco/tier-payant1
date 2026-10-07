def document_archiver(request, id_document):
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

    if "DOCUMENT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'archiver un document."
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

    if request.method == "POST":
        try:
            ancienne_valeur = f"Statut : {document.statut}"

            document.statut = "ARCHIVE"
            document.save()

            enregistrer_audit(
                request=request,
                type_action="ARCHIVAGE",
                module="DOCUMENT",
                table_cible="document",
                id_enregistrement=document.id_document,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur="Statut : ARCHIVE",
                description=(
                    f"Archivage du document "
                    f"{document.nom_fichier}"
                ),
            )

            messages.success(
                request,
                "Document archivé avec succès."
            )

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de l'archivage : {e}"
            )

        return redirect("documents")

    return render(
        request,
        "core/document_archiver.html",
        {
            "document": document,
            "page": "documents",
        }
    )
