def demande_tp_detail_create(request, id_demande):
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

    if "DEMANDE_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation d'ajouter un détail à une demande.")
        return redirect("demandes_tp")

    try:
        demande = DemandeTp.objects.get(id_demande=id_demande)
    except DemandeTp.DoesNotExist:
        messages.error(request, "Demande de tiers payant introuvable.")
        return redirect("demandes_tp")

    # Récupérer tous les actes actifs
    actes = Acte.objects.filter(statut="ACTIF").order_by("libelle")

    def _remplir_choices(form):
        """Remplit les choices des champs du formulaire."""
        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
            for a in actes
        ]

        # Si un acte est déjà sélectionné, charger ses sous-actes
        id_acte_selectionne = None
        if request.method == "POST":
            id_acte_selectionne = request.POST.get("id_acte")
        else:
            id_acte_selectionne = request.GET.get("id_acte")

        if id_acte_selectionne:
            sous_actes = (
                SousActe.objects
                .filter(id_acte_id=id_acte_selectionne, statut="ACTIF")
                .order_by("libelle")
            )
            form.fields["id_sous_acte"].choices = [
                (str(s.id_sous_acte), f"{s.code_sous_acte} - {s.libelle}")
                for s in sous_actes
            ]
        else:
            form.fields["id_sous_acte"].choices = []

    if request.method == "POST":
        form = DemandeTpDetailForm(request.POST)
        _remplir_choices(form)

        if form.is_valid():
            try:
                acte = Acte.objects.get(
                    id_acte=form.cleaned_data["id_acte"],
                    statut="ACTIF"
                )
                sous_acte = SousActe.objects.get(
                    id_sous_acte=form.cleaned_data["id_sous_acte"],
                    statut="ACTIF"
                )
                # Le prestataire est hérité de la demande
                prestataire = demande.id_prestataire

                # Vérifier que l'acte est couvert par une garantie active du contrat
                acte_couvert = (
                    GarantieActe.objects
                    .filter(
                        id_acte=acte,
                        statut="ACTIF",
                        id_garantie__contratgarantie__id_contrat=demande.id_contrat,
                        id_garantie__contratgarantie__statut="ACTIF",
                    )
                    .exists()
                )

                if not acte_couvert:
                    messages.error(
                        request,
                        "Cet acte n'est pas couvert par une garantie active "
                        "du contrat de cette demande."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                            "page": "demandes_tp",
                        }
                    )

                # Récupérer le tarif applicable
                date_aujourdhui = timezone.now().date()
                tarif = (
                    TarifSousActe.objects
                    .filter(
                        id_sous_acte=sous_acte,
                        id_prestataire=prestataire,
                        statut="ACTIF",
                        date_debut__lte=date_aujourdhui,
                    )
                    .filter(
                        Q(date_fin__isnull=True) | Q(date_fin__gte=date_aujourdhui)
                    )
                    .order_by("-date_debut")
                    .first()
                )

                if not tarif:
                    messages.error(
                        request,
                        "Aucun tarif actif pour ce sous-acte chez ce prestataire."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                        }
                    )

                quantite = form.cleaned_data["quantite"]
                montant_unitaire = tarif.montant
                montant_total = quantite * montant_unitaire

                # Créer le détail
                DemandeTpDetail.objects.create(
                    id_demande=demande,
                    id_acte=acte,
                    id_sous_acte=sous_acte,
                    quantite=quantite,
                    montant_unitaire=montant_unitaire,
                    montant_total=montant_total,
                    observation=form.cleaned_data["observation"] or None,
                )

                # Recalculer le montant total de la demande
                total_details = (
                    DemandeTpDetail.objects
                    .filter(id_demande=demande)
                    .aggregate(total=Sum("montant_total"))["total"]
                    or Decimal("0.00")
                )
                demande.montant_demande = total_details
                demande.save(update_fields=["montant_demande"])

                messages.success(request, "Acte ajouté à la demande avec succès.")
                return redirect("demande_tp_details", id_demande=demande.id_demande)

            except Exception as e:
                messages.error(request, f"Erreur lors de l'ajout de l'acte : {e}")
    else:
        form = DemandeTpDetailForm(initial={
            "id_acte": request.GET.get("id_acte", ""),
            "id_sous_acte": request.GET.get("id_sous_acte", ""),
        })
        _remplir_choices(form)

    # ⬅️ LE RETURN FINAL — OBLIGATOIRE
    return render(
        request,
        "core/demande_tp_detail_form.html",
        {
            "form": form,
            "demande": demande,
            "titre": "Ajouter un acte à la demande",
            "page": "demandes_tp",
        }
    )

def _remplir_choices(form):
        """Remplit les choices des champs du formulaire."""
        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
            for a in actes
        ]

        # Si un acte est déjà sélectionné, charger ses sous-actes
        id_acte_selectionne = None
        if request.method == "POST":
            id_acte_selectionne = request.POST.get("id_acte")
        else:
            id_acte_selectionne = request.GET.get("id_acte")

        if id_acte_selectionne:
            sous_actes = (
                SousActe.objects
                .filter(id_acte_id=id_acte_selectionne, statut="ACTIF")
                .order_by("libelle")
            )
            form.fields["id_sous_acte"].choices = [
                (str(s.id_sous_acte), f"{s.code_sous_acte} - {s.libelle}")
                for s in sous_actes
            ]
        else:
            form.fields["id_sous_acte"].choices = []

        if request.method == "POST":
            form = DemandeTpDetailForm(request.POST)
        _remplir_choices(form)

        if form.is_valid():
            try:
                acte = Acte.objects.get(
                    id_acte=form.cleaned_data["id_acte"],
                    statut="ACTIF"
                )
                sous_acte = SousActe.objects.get(
                    id_sous_acte=form.cleaned_data["id_sous_acte"],
                    statut="ACTIF"
                )
                # ✅ Le prestataire est hérité de la demande
                prestataire = demande.id_prestataire

                # Vérifier que l'acte est couvert par une garantie active du contrat
                acte_couvert = (
                    GarantieActe.objects
                    .filter(
                        id_acte=acte,
                        statut="ACTIF",
                        id_garantie__contratgarantie__id_contrat=demande.id_contrat,
                        id_garantie__contratgarantie__statut="ACTIF",
                    )
                    .exists()
                )

                if not acte_couvert:
                    messages.error(
                        request,
                        "Cet acte n'est pas couvert par une garantie active "
                        "du contrat de cette demande."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                            "page": "demandes_tp"
                        }
                    )

                                # Récupérer le tarif applicable
                date_aujourdhui = timezone.now().date()
                tarif = (
                    TarifSousActe.objects
                    .filter(
                        id_sous_acte=sous_acte,
                        id_prestataire=prestataire,
                        statut="ACTIF",
                        date_debut__lte=date_aujourdhui,
                    )
                    .filter(
                        Q(date_fin__isnull=True) | Q(date_fin__gte=date_aujourdhui)
                    )
                    .order_by("-date_debut")
                    .first()
                )

                if not tarif:
                    messages.error(
                        request,
                        f"Aucun tarif actif pour ce sous-acte chez ce prestataire."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                        }
                    )

                quantite = form.cleaned_data["quantite"]
                montant_unitaire = tarif.montant
                montant_total = quantite * montant_unitaire

                # Créer le détail
                DemandeTpDetail.objects.create(
                    id_demande=demande,
                    id_acte=acte,
                    id_sous_acte=sous_acte,
                    quantite=quantite,
                    montant_unitaire=montant_unitaire,
                    montant_total=montant_total,
                    observation=form.cleaned_data["observation"] or None,
                )

                # Recalculer le montant total de la demande
                total_details = (
                    DemandeTpDetail.objects
                    .filter(id_demande=demande)
                    .aggregate(total=Sum("montant_total"))["total"]
                    or Decimal("0.00")
                )
                demande.montant_demande = total_details
                demande.save(update_fields=["montant_demande"])

                messages.success(
                    request,
                    "Acte ajouté à la demande avec succès."
                )
                return redirect(
                    "demande_tp_details",
                    id_demande=demande.id_demande
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de l'ajout de l'acte : {e}"
                )

            else:
             form = DemandeTpDetailForm(initial={
               "id_acte": request.GET.get("id_acte", ""),
               "id_sous_acte": request.GET.get("id_sous_acte", ""),
})
        _remplir_choices(form)

        return render(
        request,
        "core/demande_tp_detail_form.html",
        {
            "form": form,
            "demande": demande,
            "titre": "Ajouter un acte à la demande",
        }
    )
