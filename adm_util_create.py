def utilisateur_create(request):
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

    if "USER_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un utilisateur."
        )
        return redirect("utilisateurs")

    if request.method == "POST":
        form = UtilisateurForm(request.POST)

        if form.is_valid():
                        # Créer l'objet SANS sauvegarder
            nouvel_utilisateur = Utilisateur(
                nom_utilisateur=form.cleaned_data["nom_utilisateur"],
                nom=form.cleaned_data["nom"],
                prenom=form.cleaned_data["prenom"],
                email=form.cleaned_data["email"] or None,
                telephone=form.cleaned_data["telephone"] or None,
                statut=form.cleaned_data["statut"],
                is_active=True,
                date_creation=timezone.now(),
            )

            # Utiliser set_password (met à jour password ET mot_de_passe_hash)
            nouvel_utilisateur.set_password(
                form.cleaned_data["mot_de_passe"]
            )
            nouvel_utilisateur.mot_de_passe_hash = nouvel_utilisateur.password
            nouvel_utilisateur.save()

            messages.success(
                request,
                "Utilisateur créé avec succès."
            )

            return redirect("utilisateurs")

    else:
        form = UtilisateurForm()

    return render(
        request,
        "core/utilisateur_form.html",
        {
            "form": form,
            "titre": "Nouvel utilisateur",
            "page": "utilisateurs",
        }
    )


