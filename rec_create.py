def recours_create(request):
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

    if "RECOURS_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un recours."
        )
        return redirect("recours")

    if request.method == "POST":
        form = RecoursForm(request.POST)

        if form.is_valid():
            recours_obj = form.save(commit=False)

            recours_obj.numero_recours = _generer_numero_recours()

            recours_obj.statut = "EN_ATTENTE"

            recours_obj.utilisateur_creation = (
                request.session.get("nom_utilisateur")
            )

            recours_obj.save()

            messages.success(
                request,
                "Le recours a été créé avec succès."
            )

            return redirect("recours")

    else:
        form = RecoursForm()

    return render(
        request,
        "core/recours_form.html",
        {
            "form": form,
            "permissions": permissions,
            "page": "recours",
        }
    )
