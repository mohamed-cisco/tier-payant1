def document_create(request):
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

    if "DOCUMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de déposer un document."
        )
        return redirect("documents")

    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                with transaction.atomic():
                    fichier = form.cleaned_data["fichier"]

                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=(
                            form.cleaned_data["type_document"]
                            or getattr(fichier, "content_type", None)
                            or "INCONNU"
                        ),
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="DEPOT_DOCUMENT",
                        module="DOCUMENT",
                        table_cible="document",
                        id_enregistrement=document.id_document,
                        nouvelle_valeur=(
                            f"Fichier : {document.nom_fichier}, "
                            f"Type : {document.type_document}, "
                            f"Taille : {document.taille} octets, "
                            f"Statut : {document.statut}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                messages.success(
                    request,
                    "Document déposé avec succès."
                )

                return redirect("documents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors du dépôt du document : {e}"
                )

    else:
        form = DocumentForm()

    return render(
        request,
        "core/document_form.html",
        {
            "form": form,
            "titre": "Déposer un document",
            "page": "documents",
        }
    )
