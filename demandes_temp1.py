def demande_tp_create(request):
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
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("demandes_tp")

    contrats = (
        Contrat.objects.filter(statut="ACTIF")
        .select_related("id_souscripteur")
        .order_by("numero_contrat")
    )

    id_contrat_preselectionne = request.GET.get("id_contrat", "").strip()
    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects.filter(
                id_contrat=id_contrat_preselectionne, statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )

    id_contrat_beneficiaires = id_contrat_preselectionne

    if not id_contrat_beneficiaires:
        premier_contrat = contrats.first()
        if premier_contrat:
            id_contrat_beneficiaires = str(premier_contrat.id_contrat)

    if request.method == "POST":
        id_contrat_beneficiaires = request.POST.get("id_contrat", "").strip()

    personnes = Personne.objects.none()

    if id_contrat_beneficiaires:
        ids_adherents = (
            Adhesion.objects
            .filter(id_contrat=id_contrat_beneficiaires, statut="ACTIF")
            .values_list("id_adherent", flat=True)
        )

        ids_personnes_titulaires = (
            Adherent.objects
            .filter(id_adherent__in=ids_adherents, statut="ACTIF")
            .values_list("id_personne", flat=True)
        )

        ids_personnes_ayants_droit = (
            AyantDroit.objects
            .filter(id_adherent__in=ids_adherents, statut="ACTIF")
            .values_list("id_personne", flat=True)
        )

        ids_beneficiaires = list(ids_personnes_titulaires) + list(ids_personnes_ayants_droit)

        personnes = (
            Personne.objects
            .filter(id_personne__in=ids_beneficiaires, statut="ACTIF")
            .order_by("nom", "prenom")
        )

    prestataires = (
        Prestataire.objects.filter(statut="ACTIF").order_by("raison_sociale")
    )

    if request.method == "POST":
        form = DemandeTpForm(request.POST)
        form.fields["statut"].initial = "EN_ATTENTE"
        form.fields["statut"].widget = forms.HiddenInput()

        form.fields["id_personne_beneficiaire"].choices = [
            (str(p.id_personne), _libelle_beneficiaire(p)) for p in personnes
        ]

        form.fields["id_contrat"].choices = [
            (str(c.id_contrat), f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}")
            for c in contrats
        ]

        form.fields["id_prestataire"].choices = [
            (str(p.id_prestataire), f"{p.code_prestataire} - {p.raison_sociale}")
            for p in prestataires
        ]

        if form.is_valid():
            try:
                personne = Personne.objects.get(
                    id_personne=form.cleaned_data["id_personne_beneficiaire"],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.get(
                    id_contrat=form.cleaned_data["id_contrat"],
                    statut="ACTIF"
                )

                prestataire = Prestataire.objects.get(
                    id_prestataire=form.cleaned_data["id_prestataire"],
                    statut="ACTIF"
                )

                # Vérifier bénéficiaire rattaché
                titulaire_valide = Adhesion.objects.filter(
                    id_contrat=contrat,
                    id_adherent__id_personne=personne,
                    statut="ACTIF"
                ).exists()

                ayant_droit_valide = Adhesion.objects.filter(
                    id_contrat=contrat,
                    id_adherent__ayantdroit__id_personne=personne,
                    statut="ACTIF"
                ).exists()

                if not titulaire_valide and not ayant_droit_valide:
                    messages.error(
                        request,
                        "Le bénéficiaire sélectionné n'est pas rattaché "
                        "à une adhésion active de ce contrat."
                    )
                    return render(
                        request,
                        "core/demande_tp_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle demande",
                            "contrats": contrats,
                            "prestataires": prestataires,
                            "personnes": personnes,
                            "contrat_preselectionne": contrat_preselectionne,
                        }
                    )

                # Vérifier convention active
                date_demande = timezone.now().date()
                convention_active = Convention.objects.filter(
                    id_prestataire=prestataire,
                    statut="ACTIF",
                    date_debut__lte=date_demande
                ).filter(
                    Q(date_fin__isnull=True) | Q(date_fin__gte=date_demande)
                ).exists()

                if not convention_active:
                    messages.error(
                        request,
                        "Impossible de créer la demande TP : aucune convention "
                        "active avec ce prestataire à la date de la demande."
                    )
                    return render(
                        request,
                        "core/demande_tp_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle demande",
                            "contrats": contrats,
                            "prestataires": prestataires,
                            "personnes": personnes,
                            "contrat_preselectionne": contrat_preselectionne,
                        }
                    )

                # 🔍 DÉTECTION DE DOUBLON
                doublon = DemandeTp.objects.filter(
                    id_personne_beneficiaire=personne,
                    id_prestataire=prestataire,
                    date_demande__date=date_demande,
                    statut__in=["EN_ATTENTE", "ACCEPTEE"],
                ).first()

                if doublon and not request.POST.get("confirmer_doublon"):
                    messages.warning(
                        request,
                        f"⚠️ Une demande existe déjà aujourd'hui pour ce "
                        f"bénéficiaire chez ce prestataire : "
                        f"{doublon.numero_demande} "
                        f"({doublon.montant_demande} DA, statut {doublon.statut}). "
                        f"Cliquez à nouveau sur Enregistrer pour créer quand même."
                    )
                    return render(
                        request,
                        "core/demande_tp_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle demande",
                            "contrats": contrats,
                            "prestataires": prestataires,
                            "personnes": personnes,
                            "contrat_preselectionne": contrat_preselectionne,
                            "doublon_detecte": doublon,
                        }
                    )

                demande = DemandeTp.objects.create(
                    numero_demande=_generer_numero_demande(),
                    id_personne_beneficiaire=personne,
                    id_contrat=contrat,
                    id_prestataire=prestataire,
                    date_demande=timezone.now(),
                    montant_demande=Decimal("0.00"),
                    statut="EN_ATTENTE",
                    motif_rejet=form.cleaned_data["motif_rejet"] or None,
                    date_decision=None,
                    utilisateur_creation=str(request.session.get("id_utilisateur")),
                )
                                # 🔄 Créer la PEC automatiquement
                numero_pec = _generer_numero_pec()
                pec = PriseEnCharge.objects.create(
                    numero_pec=numero_pec,
                    id_demande=demande,
                    date_pec=timezone.now(),
                    montant_demande=Decimal("0.00"),
                    montant_accepte=Decimal("0.00"),
                    montant_rejete=Decimal("0.00"),
                    statut="EN_ATTENTE",   # ← En attente de validation
                    date_expiration=timezone.now().date() + timedelta(days=30),
                    utilisateur_validation=None,
                )

                # Passer la demande à ACCEPTEE (la PEC prend le relais)
                demande.statut = "ACCEPTEE"
                demande.date_decision = timezone.now()
                demande.save()

                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="DEMANDE TP",
                    table_cible="demande_tp",
                    id_enregistrement=demande.id_demande,
                    nouvelle_valeur=demande.numero_demande,
                    description=f"Création de la demande {demande.numero_demande}",
                )

                messages.success(
                    request,
                    f"Demande {demande.numero_demande} créée. "
                    f"PEC {numero_pec} générée automatiquement. "
                    f"Validez la PEC pour créer les consommations."
                )
                return redirect("prise_en_charge_details", id_pec=pec.id_pec)

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = DemandeTpForm()
        form.fields["statut"].initial = "EN_ATTENTE"
        form.fields["statut"].widget = forms.HiddenInput()

        form.fields["id_personne_beneficiaire"].choices = [
            (str(p.id_personne), _libelle_beneficiaire(p)) for p in personnes
        ]

        form.fields["id_contrat"].choices = [
            (str(c.id_contrat), f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}")
            for c in contrats
        ]

        if contrat_preselectionne:
            form.initial["id_contrat"] = str(contrat_preselectionne.id_contrat)

        form.fields["id_prestataire"].choices = [
            (str(p.id_prestataire), f"{p.code_prestataire} - {p.raison_sociale}")
            for p in prestataires
        ]

    return render(
        request,
        "core/demande_tp_form.html",
        {
            "form": form,
            "titre": "Nouvelle demande de Tiers Payant",
            "contrat_preselectionne": contrat_preselectionne,
            "page": "demandes_tp",
        }
    )
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
