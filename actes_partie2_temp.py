def acte_create(request):
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

    if "ACTE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un acte."
        )
        return redirect("actes")

    types_prestation = (
        TypePrestation.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    if request.method == "POST":
        form = ActeForm(request.POST)

        form.fields["id_type_prestation"].choices = [
            (
                str(t.id_type_prestation),
                t.libelle
            )
            for t in types_prestation
        ]

        if form.is_valid():
            try:
                type_prestation = TypePrestation.objects.get(
                    id_type_prestation=form.cleaned_data["id_type_prestation"],
                    statut="ACTIF"
                )

                Acte.objects.create(
                    id_type_prestation=type_prestation,
                    code_acte=_generer_code_acte(),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"] or None,
                    unite=form.cleaned_data["unite"] or None,
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Acte créé avec succès."
                )

                return redirect("actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = ActeForm()

        form.fields["id_type_prestation"].choices = [
            (
                str(t.id_type_prestation),
                t.libelle
            )
            for t in types_prestation
        ]

    return render(
        request,
        "core/acte_form.html",
        {
            "form": form,
            "titre": "Nouvel acte",
        }
    )
def acte_modifier(request, id_acte):
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

    if "ACTE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un acte."
        )
        return redirect("actes")

    try:
        acte = Acte.objects.get(id_acte=id_acte)
    except Acte.DoesNotExist:
        messages.error(
            request,
            "Acte introuvable."
        )
        return redirect("actes")

    if request.method == "POST":
        form = ActeForm(request.POST)

        if form.is_valid():
            try:
                acte.id_type_prestation_id = form.cleaned_data["id_type_prestation"]
                acte.libelle = form.cleaned_data["libelle"]
                acte.description = form.cleaned_data["description"] or None
                acte.unite = form.cleaned_data["unite"] or None
                acte.statut = form.cleaned_data["statut"]

                acte.save()

                messages.success(
                    request,
                    "Acte modifié avec succès."
                )
                return redirect("actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = ActeForm(
            initial={
                "id_type_prestation": acte.id_type_prestation_id,
                "code_acte": acte.code_acte,
                "libelle": acte.libelle,
                "description": acte.description,
                "unite": acte.unite,
                "statut": acte.statut,
            }
       
            )
        types_prestation = (
            TypePrestation.objects
            .filter(statut="ACTIF")
            .order_by("libelle")
        )

        form.fields["id_type_prestation"].choices = [
    (
        str(t.id_type_prestation),
        t.libelle
    )
    for t in types_prestation
]
    return render(
        request,
        "core/acte_form.html",
        {
            "form": form,
            "titre": "Modifier un acte",
        }
    )
def acte_radier(request, id_acte):
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

    if "ACTE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un acte."
        )
        return redirect("actes")

    try:
        acte = Acte.objects.get(id_acte=id_acte)
    except Acte.DoesNotExist:
        messages.error(
            request,
            "Acte introuvable."
        )
        return redirect("actes")

    if request.method == "POST":
        acte.statut = "INACTIF"
        acte.save()

        messages.success(
            request,
            "Acte radié avec succès."
        )

    return redirect("actes")

def garantie_actes(request):
