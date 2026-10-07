def reglement_create(request):
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

    if "REGLEMENT_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de créer un règlement.")
        return redirect("reglements")

    factures = (
        Facture.objects
        .filter(Q(statut="VALIDEE") | Q(statut="PARTIELLEMENT_PAYEE"))
        .select_related("id_prestataire")
        .order_by("-id_facture")
    )

    # Calculer le reste à payer pour chaque facture
    for f in factures:
        total_regle = (
            Reglement.objects
            .filter(id_facture=f, statut="VALIDEE")
            .aggregate(total=Sum("montant"))["total"]
            or 0
        )
        f.reste_a_payer = f.montant_valide - total_regle

    if request.method == "POST":
        form = ReglementForm(request.POST)
        print("=" * 50)
        print("🔍 [DEBUG] POST reçu")
        print("🔍 [DEBUG] Données POST :", dict(request.POST))
        print("🔍 [DEBUG] Form data :", form.data)

        form.fields["id_facture"].choices = [
            (
                str(f.id_facture),
                f"{f.numero_facture} - {f.id_prestataire.raison_sociale} - "
                f"Reste à payer : {f.reste_a_payer} DA"
            )
            for f in factures
        ]

        if form.is_valid():
            print("🔍 [DEBUG] Formulaire VALIDE")
            print("🔍 [DEBUG] cleaned_data :", form.cleaned_data)
            try:
                facture = Facture.objects.get(
                    id_facture=form.cleaned_data["id_facture"]
                )

                if facture.statut not in ["VALIDEE", "PARTIELLEMENT_PAYEE"]:
                    messages.error(request, "Cette facture ne peut plus être réglée.")
                    return redirect("reglements")

                montant = form.cleaned_data["montant"]

                montant_deja_regle = (
                    Reglement.objects
                    .filter(id_facture=facture, statut="VALIDEE")
                    .aggregate(total=Sum("montant"))["total"]
                    or 0
                )

                reste_a_payer = facture.montant_valide - montant_deja_regle

                if reste_a_payer <= 0:
                    messages.error(request, "Cette facture est déjà entièrement réglée.")
                    return render(
                        request,
                        "core/reglement_form.html",
                        {
                            "form": form,
                            "titre": "Nouveau règlement",
                            "factures": factures,
                        }
                    )

                if montant > reste_a_payer:
                    messages.error(
                        request,
                        f"Le montant du règlement ne peut pas dépasser "
                        f"le reste à payer de {reste_a_payer} DA."
                    )
                    return render(
                        request,
                        "core/reglement_form.html",
                        {
                            "form": form,
                            "titre": "Nouveau règlement",
                            "factures": factures,
                        }
                    )

                mode = form.cleaned_data["mode_reglement"]

                Reglement.objects.create(
                    id_facture=facture,
                    numero_reglement=_generer_numero_reglement(),
                    date_reglement=form.cleaned_data["date_reglement"],
                    montant=montant,
                    mode_reglement=mode,
                    reference_reglement=_generer_reference_reglement(mode),
                    statut="EN_ATTENTE",
                    observation=form.cleaned_data["observation"] or None,
                )

                messages.success(request, "Règlement créé avec succès.")
                return redirect("reglements")

            except Exception as e:
                messages.error(request, f"Erreur lors de la création du règlement : {e}")
                print("🔍 [DEBUG] ERREUR :", e)
    else:
        form = ReglementForm()

        form.fields["id_facture"].choices = [
            (
                str(f.id_facture),
                f"{f.numero_facture} - {f.id_prestataire.raison_sociale} - "
                f"Reste à payer : {f.reste_a_payer} DA"
            )
            for f in factures
        ]

    return render(
        request,
        "core/reglement_form.html",
        {
            "form": form,
            "titre": "Nouveau règlement",
            "factures": factures,
        }
    )


