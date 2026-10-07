

def garantie_create(request):
    """Créer une nouvelle garantie."""
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
        .values_list("id_permission__code_permission", flat=True)
    )

    if "GARANTIE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer une garantie."
        )
        return redirect("garanties")

    if request.method == "POST":
        form = GarantieForm(request.POST)

        if form.is_valid():
            try:
                Garantie.objects.create(
                    code_garantie=_generer_code_garantie(),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"] or None,
                    statut=form.cleaned_data["statut"],
                )

                messages.success(request, "Garantie créée avec succès.")
                return redirect("garanties")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )
    else:
        form = GarantieForm()

    return render(
        request,
        "core/garantie_form.html",
        {
            "form": form,
            "titre": "Nouvelle garantie",
        }
    )


def garantie_modifier(request, id_garantie):
    """Modifier une garantie existante."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    try:
        garantie = Garantie.objects.get(id_garantie=id_garantie)
    except Garantie.DoesNotExist:
        messages.error(request, "Garantie introuvable.")
        return redirect("garanties")

    if request.method == "POST":
        form = GarantieForm(request.POST)

        if form.is_valid():
            try:
                garantie.libelle = form.cleaned_data["libelle"]
                garantie.description = form.cleaned_data["description"] or None
                garantie.statut = form.cleaned_data["statut"]
                garantie.save()

                messages.success(request, "Garantie modifiée avec succès.")
                return redirect("garanties")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )
    else:
        form = GarantieForm(
            initial={
                "code_garantie": garantie.code_garantie,
                "libelle": garantie.libelle,
                "description": garantie.description,
                "statut": garantie.statut,
            }
        )

    return render(
        request,
        "core/garantie_form.html",
        {
            "form": form,
            "titre": "Modifier la garantie",
        }
    )


def garantie_radier(request, id_garantie):
    """Radier une garantie."""
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
        .values_list("id_permission__code_permission", flat=True)
    )

    if "GARANTIE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une garantie."
        )
        return redirect("garanties")

    try:
        garantie = Garantie.objects.get(id_garantie=id_garantie)
    except Garantie.DoesNotExist:
        messages.error(request, "Garantie introuvable.")
        return redirect("garanties")

    if request.method == "POST":
        garantie.statut = "RADIE"
        garantie.save()

        messages.success(request, "Garantie radiée avec succès.")

    return redirect("garanties")
