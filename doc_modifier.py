def document_modifier(request, id_document):
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

    if "DOCUMENT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un document."
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
        form = DocumentForm(
            request.POST,
            request.FILES
        )

        form.fields["fichier"].required = False

        if form.is_valid():
            try:
                ancienne_valeur = (
                    f"Nom : {document.nom_fichier}, "
                    f"Type : {document.type_document}, "
                    f"Statut : {document.statut}"
                )

                fichier = form.cleaned_data.get("fichier")

                if fichier:
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

                    document.nom_fichier = fichier.name
                    document.extension = (
                        extension or None
                    )
                    document.taille = fichier.size
                    document.emplacement = chemin
                    document.hash_fichier = (
                        hash_sha256.hexdigest()
                    )

                document.type_document = (
                    form.cleaned_data["type_document"]
                    or document.type_document
                )

                document.statut = (
                    form.cleaned_data["statut"]
                )

                document.save()

                nouvelle_valeur = (
                    f"Nom : {document.nom_fichier}, "
                    f"Type : {document.type_document}, "
                    f"Statut : {document.statut}"
                )

                enregistrer_audit(
                    request=request,
                    type_action="MODIFICATION",
                    module="DOCUMENT",
                    table_cible="document",
                    id_enregistrement=document.id_document,
                    ancienne_valeur=ancienne_valeur,
                    nouvelle_valeur=nouvelle_valeur,
                    description=(
                        f"Modification du document "
                        f"{document.nom_fichier}"
                    ),
                )

                messages.success(
                    request,
                    "Document modifié avec succès."
                )

                return redirect("documents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = DocumentForm(
            initial={
                "type_document": document.type_document,
                "statut": document.statut,
            }
        )

        form.fields["fichier"].required = False

    return render(
        request,
        "core/document_form.html",
        {
            "form": form,
            "titre": "Modifier le document",
        }
    )
