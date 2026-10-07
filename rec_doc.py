def recours_document_create(request, id_recours):
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
            "Vous n'avez pas l'autorisation d'ajouter une pièce jointe."
        )
        return redirect(
            "recours_detail",
            id_recours=id_recours
        )

    try:
        recours_obj = Recours.objects.get(
            id_recours=id_recours
        )
    except Recours.DoesNotExist:
        messages.error(
            request,
            "Recours introuvable."
        )
        return redirect("recours")

    if request.method == "POST":

        form = DocumentForm(
            request.POST,
            request.FILES
        )

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

                    type_document = (
                        form.cleaned_data["type_document"]
                        or getattr(
                            fichier,
                            "content_type",
                            None
                        )
                        or "INCONNU"
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=type_document,
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    RecoursDocument.objects.create(
                        id_recours=recours_obj,
                        id_document=document,
                        type_document=type_document,
                        date_ajout=timezone.now(),
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
                            f"Recours : {recours_obj.numero_recours}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="RATTACHEMENT_DOCUMENT",
                        module="RECOURS",
                        table_cible="recours_document",
                        id_enregistrement=recours_obj.id_recours,
                        nouvelle_valeur=(
                            f"Document : {document.nom_fichier}, "
                            f"Recours : {recours_obj.numero_recours}"
                        ),
                        description=(
                            f"Rattachement du document "
                            f"{document.nom_fichier} au recours "
                            f"{recours_obj.numero_recours}"
                        ),
                    )

                messages.success(
                    request,
                    "Le document a été ajouté au recours avec succès."
                )

                return redirect(
                    "recours_detail",
                    id_recours=id_recours
                )

            except Exception as e:

                messages.error(
                    request,
                    f"Erreur lors du dépôt du document : {str(e)}"
                )

    else:

        form = DocumentForm()

    return render(
    request,
    "core/recours_document_form.html",
    {
        "form": form,
        "recours": recours_obj,
        "permissions": permissions,
        "page": "recours",
    }
)

