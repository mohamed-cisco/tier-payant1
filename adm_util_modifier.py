def utilisateur_modifier(request, id_utilisateur):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_connecte = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_connecte,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
    )

    if "USER_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un utilisateur."
        )
        return redirect("utilisateurs")

    try:
        utilisateur = Utilisateur.objects.get(
            id_utilisateur=id_utilisateur
        )
    except Utilisateur.DoesNotExist:
        messages.error(
            request,
            "Utilisateur introuvable."
        )
        return redirect("utilisateurs")

    if request.method == "POST":
        form = UtilisateurForm(
            request.POST,
            instance=utilisateur
        )

        if form.is_valid():
            utilisateur.nom_utilisateur = (
                form.cleaned_data["nom_utilisateur"]
            )
            utilisateur.nom = form.cleaned_data["nom"]
            utilisateur.prenom = form.cleaned_data["prenom"]
            utilisateur.email = (
                form.cleaned_data["email"] or None
            )
            utilisateur.telephone = (
                form.cleaned_data["telephone"] or None
            )
            utilisateur.statut = form.cleaned_data["statut"]

            mot_de_passe = form.cleaned_data["mot_de_passe"]

            if mot_de_passe:
                utilisateur.set_password(mot_de_passe)
                utilisateur.mot_de_passe_hash = utilisateur.password

            utilisateur.save()

            messages.success(
                request,
                "Utilisateur modifié avec succès."
            )

            return redirect("utilisateurs")

    else:
        form = UtilisateurForm(
            instance=utilisateur
        )

    return render(
        request,
        "core/utilisateur_form.html",
        {
            "form": form,
            "titre": "Modifier l'utilisateur",
        }
    )
