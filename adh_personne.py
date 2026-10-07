def personne_create(request):
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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer une personne."
        )
        return redirect("adherents")

    if request.method == "POST":
        form = PersonneForm(request.POST)

        if form.is_valid():
            try:
                Personne.objects.create(
                    numero_personne=_generer_numero_personne(),
                    nom=form.cleaned_data["nom"],
                    prenom=form.cleaned_data["prenom"],
                    date_naissance=form.cleaned_data["date_naissance"],
                    sexe=form.cleaned_data["sexe"] or None,
                    adresse=form.cleaned_data["adresse"] or None,
                    telephone=form.cleaned_data["telephone"] or None,
                    email=form.cleaned_data["email"] or None,
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                messages.success(
                    request,
                    "Personne créée avec succès."
                )

                return redirect("personne_create")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = PersonneForm()

    return render(
        request,
        "core/personne_form.html",
        {
            "form": form,
            "titre": "Nouvelle personne",
            "page": "adherents",
        }
    )

