def adhesion_modifier(request, id_adhesion):
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

    if "ADHESION_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier une adhésion."
        )
        return redirect("adhesions")

    try:
        adhesion = Adhesion.objects.get(
            id_adhesion=id_adhesion
        )
    except Adhesion.DoesNotExist:
        messages.error(
            request,
            "Adhésion introuvable."
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

    if request.method == "POST":
        form = AdhesionForm(request.POST)

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                a.numero_adherent
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

                adhesion.id_adherent = adherent
                adhesion.id_contrat = contrat
               

                adhesion.date_debut = (
                    form.cleaned_data["date_debut"]
                )
                adhesion.date_fin = (
                    form.cleaned_data["date_fin"]
                )
                adhesion.statut = (
                    form.cleaned_data["statut"]
                )

                adhesion.save()

                messages.success(
                    request,
                    "Adhésion modifiée avec succès."
                )

                return redirect("adhesions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = AdhesionForm(
            initial={
                "id_adherent": str(
                    adhesion.id_adherent_id
                ),
                "id_contrat": str(
                    adhesion.id_contrat_id
                ),
                "numero_adhesion": adhesion.numero_adhesion,
                "date_debut": adhesion.date_debut,
                "date_fin": adhesion.date_fin,
                "statut": adhesion.statut,
            }
        )

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                a.numero_adherent
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
            "titre": "Modifier l'adhésion",
        }
    )
