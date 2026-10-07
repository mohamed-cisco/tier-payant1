def adhesion_create(request):
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

    if "ADHESION_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer une adhésion."
        )
        return redirect("adhesions")

    adherents = (
        Adherent.objects
        .filter(statut="ACTIF")
        .order_by("numero_adherent")
    )

    contrats = (
        Contrat.objects
        .filter(statut="ACTIF")
        .select_related("id_souscripteur")
        .order_by("numero_contrat")
    )
    id_contrat_preselectionne = request.GET.get(
        "id_contrat",
        ""
    ).strip()

    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects
            .filter(
                id_contrat=id_contrat_preselectionne,
                statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )    
    id_contrat_preselectionne = request.GET.get(
        "id_contrat",
        ""
    ).strip()

    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects
            .filter(
                id_contrat=id_contrat_preselectionne,
                statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )

    if request.method == "POST":
        form = AdhesionForm(request.POST)

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                f"{a.numero_adherent}"
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]
        if contrat_preselectionne:
            form.initial["id_contrat"] = (
                str(contrat_preselectionne.id_contrat)
                
            )

        if form.is_valid():
            try:
                adherent = Adherent.objects.get(
                    id_adherent=form.cleaned_data["id_adherent"],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.get(
                    id_contrat=form.cleaned_data["id_contrat"],
                    statut="ACTIF"
                )

                Adhesion.objects.create(
                    id_adherent=adherent,
                    id_contrat=contrat,
                    numero_adhesion=_generer_numero_adhesion(),
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                messages.success(
                    request,
                    "Adhésion créée avec succès."
                )

                return redirect("adhesions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = AdhesionForm()

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                f"{a.numero_adherent}"
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

    return render(
        request,
        "core/adhesion_form.html",
        {
            "form": form,
            "titre": "Nouvelle adhésion",
            "contrat_preselectionne": contrat_preselectionne,
            "page": "adhesions",
        }
    )

