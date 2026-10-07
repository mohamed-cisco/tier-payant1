def demande_tp_document_create(request, id_demande):
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

    if "DOCUMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter une pièce jointe."
        )
        return redirect(
            "demande_tp_details",
            id_demande=id_demande
        )

    try:
        demande = DemandeTp.objects.get(
            id_demande=id_demande
        )
    except DemandeTp.DoesNotExist:
        messages.error(
            request,
            "Demande de tiers payant introuvable."
        )
        return redirect("demandes_tp")

    if request.method == "POST":
        form = DocumentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            try:
                with transaction.atomic():

                    fichier = form.cleaned_data["fichier"]

                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    type_document = (
                        form.cleaned_data["type_document"]
                        or getattr(
                            fichier,
                            "content_type",
                            None
                        )
                        or "INCONNU"
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=type_document,
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    DemandeTpDocument.objects.create(
                        id_demande=demande,
                        id_document=document,
                        type_document=type_document,
                        date_ajout=timezone.now(),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="DEPOT_DOCUMENT",
                        module="DOCUMENT",
                        table_cible="document",
                        id_enregistrement=document.id_document,
                        nouvelle_valeur=(
                            f"Fichier : {document.nom_fichier}, "
                            f"Type : {document.type_document}, "
                            f"Demande : {demande.numero_demande}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="RATTACHEMENT_DOCUMENT",
                        module="DEMANDE TP",
                        table_cible="demande_tp_document",
                        id_enregistrement=demande.id_demande,
                        nouvelle_valeur=(
                            f"Document : {document.nom_fichier}, "
                            f"Demande : {demande.numero_demande}"
                        ),
                        description=(
                            f"Rattachement du document "
                            f"{document.nom_fichier} "
                            f"à la demande {demande.numero_demande}"
                        ),
                    )

                messages.success(
                    request,
                    "Pièce jointe ajoutée à la demande avec succès."
                )

                return redirect(
                    "demande_tp_details",
                    id_demande=demande.id_demande
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de l'ajout de la pièce jointe : {e}"
                )

    else:
        form = DocumentForm()

    return render(
        request,
        "core/demande_tp_document_form.html",
        {
            "form": form,
            "demande": demande,
            "titre": "Ajouter une pièce jointe",
            "page": "demandes_tp",
        }
    )
def _dates_periode_plafond(date_reference, periode):
    """
    Retourne la date de début et la date de fin
    de la période correspondant au plafond.
    """

    if periode == "JOUR":
        return date_reference, date_reference

    if periode == "MOIS":
        debut = date_reference.replace(day=1)

        if date_reference.month == 12:
            fin = date(date_reference.year + 1, 1, 1) - timedelta(days=1)
        else:
            fin = date(
                date_reference.year,
                date_reference.month + 1,
                1
            ) - timedelta(days=1)

        return debut, fin

    if periode == "TRIMESTRE":
        mois_debut = ((date_reference.month - 1) // 3) * 3 + 1

        debut = date(
            date_reference.year,
            mois_debut,
            1
        )

        if mois_debut == 10:
            fin = date(
                date_reference.year + 1,
                1,
                1
            ) - timedelta(days=1)
        else:
            fin = date(
                date_reference.year,
                mois_debut + 3,
                1
            ) - timedelta(days=1)

        return debut, fin

    if periode == "SEMESTRE":
        if date_reference.month <= 6:
            debut = date(date_reference.year, 1, 1)
            fin = date(date_reference.year, 7, 1) - timedelta(days=1)
        else:
            debut = date(date_reference.year, 7, 1)
            fin = date(
                date_reference.year + 1,
                1,
                1
            ) - timedelta(days=1)

        return debut, fin

    # ANNEE par défaut
    debut = date(date_reference.year, 1, 1)
    fin = date(
        date_reference.year + 1,
        1,
        1
    ) - timedelta(days=1)

    return debut, fin


def _get_adhesion_demande(demande):
    """
    Retrouve l'adhésion active correspondant
    à la personne bénéficiaire et au contrat de la demande.

    Cas possibles :
    - la personne est directement l'adhérent ;
    - la personne est un ayant droit.
    """

    personne = demande.id_personne_beneficiaire

    adherent = (
        Adherent.objects
        .filter(
            id_personne=personne,
            statut="ACTIF"
        )
        .first()
    )

    if not adherent:
        ayant_droit = (
            AyantDroit.objects
            .select_related("id_adherent")
            .filter(
                id_personne=personne,
                statut="ACTIF"
            )
            .first()
        )

        if ayant_droit:
            adherent = ayant_droit.id_adherent

    if not adherent:
        return None

    date_demande = demande.date_demande.date()

    return (
        Adhesion.objects
        .filter(
            id_adherent=adherent,
            id_contrat=demande.id_contrat,
            statut="ACTIF",
            date_debut__lte=date_demande,
        )
        .filter(
            Q(date_fin__isnull=True)
            | Q(date_fin__gte=date_demande)
        )
        .order_by("-date_debut")
        .first()
    )
def _appliquer_plafonds_demande(
    demande,
    detail,
    garantie_acte,
    montant_accorde,
):
    date_reference = demande.date_demande.date()

    plafonds = list(
        Plafond.objects
        .select_related(
            "id_garantie_acte",
            "id_garantie_acte__id_garantie",
            "id_garantie_acte__id_acte",
        )
        .filter(
            id_garantie_acte=garantie_acte,
            statut="ACTIF",
            date_debut__lte=date_reference,
        )
        .filter(
            Q(date_fin__isnull=True)
            | Q(date_fin__gte=date_reference)
        )
        .order_by(
            "-date_debut",
            "-id_plafond",
        )
    )

    # Aucun plafond configuré pour cet acte.
    if not plafonds:
        return montant_accorde, [], None, detail.quantite

    adhesion = None
    montant_courant = montant_accorde
    informations = []

    quantite_autorisee = detail.quantite or Decimal("0.00")

    for plafond in plafonds:

        # Pour un plafond adhérent, il faut retrouver
        # l'adhérent principal, y compris si le bénéficiaire
        # est un ayant droit.
        if plafond.niveau_application == "ADHERENT":

            if adhesion is None:
                adhesion = _get_adhesion_demande(demande)

            if not adhesion:
                return (
                    Decimal("0.00"),
                    informations,
                    (
                        "Impossible d'appliquer le plafond adhérent : "
                        "aucune adhésion active trouvée pour cette demande."
                    ),
                    Decimal("0.00"),
                )

        date_debut_periode, date_fin_periode = (
            _dates_periode_plafond(
                date_reference,
                plafond.periode,
            )
        )

        consommations = (
            Consommation.objects
            .filter(
                id_acte=garantie_acte.id_acte,
                id_garantie=garantie_acte.id_garantie,
                statut="VALIDEE",
                date_prestation__gte=date_debut_periode,
                date_prestation__lte=date_fin_periode,
            )
        )

        if plafond.niveau_application == "ADHERENT":

            consommations = consommations.filter(
                id_adhesion__id_adherent=adhesion.id_adherent
            )

        elif plafond.niveau_application == "PERSONNE":

            consommations = consommations.filter(
                id_personne_beneficiaire=(
                    demande.id_personne_beneficiaire
                )
            )

        elif plafond.niveau_application == "CONTRAT":

            consommations = consommations.filter(
                id_adhesion__id_contrat=demande.id_contrat
            )

        else:
            return (
                Decimal("0.00"),
                informations,
                (
                    f"Niveau d'application inconnu : "
                    f"{plafond.niveau_application}"
                ),
                Decimal("0.00"),
            )

        totaux = consommations.aggregate(
            montant_consomme=Sum("montant_prise_en_charge"),
            quantite_consommee=Sum("quantite"),
        )

        montant_consomme = (
            totaux["montant_consomme"]
            or Decimal("0.00")
        )

        quantite_consommee = (
            totaux["quantite_consommee"]
            or Decimal("0.00")
        )

        montant_avant = montant_courant
        quantite_avant = quantite_autorisee

        reste_montant = None
        reste_quantite = None

        # -------------------------------------------------
        # PLAFOND DE QUANTITE
        # -------------------------------------------------

        if (
            plafond.type_plafond in ("QUANTITE", "MIXTE")
            and plafond.quantite_max is not None
        ):

            reste_quantite = max(
                Decimal("0.00"),
                Decimal(plafond.quantite_max)
                - quantite_consommee,
            )

            quantite_autorisee = min(
                quantite_autorisee,
                reste_quantite,
            )

            # Recalcul financier sur la quantité réellement autorisée
            if detail.quantite and detail.quantite > 0:

                montant_unitaire = (
                    detail.montant_total
                    / detail.quantite
                )

                taux = (
                    garantie_acte.taux_prise_en_charge
                    or Decimal("0.00")
                )

                franchise = (
                    garantie_acte.franchise
                    or Decimal("0.00")
                )

                montant_couvert_quantite = (
                    montant_unitaire
                    * quantite_autorisee
                    * taux
                    / Decimal("100")
                )

                montant_courant = max(
                    Decimal("0.00"),
                    montant_couvert_quantite - franchise,
                )

        # -------------------------------------------------
        # PLAFOND DE MONTANT
        # -------------------------------------------------

        if (
            plafond.type_plafond in ("MONTANT", "MIXTE")
            and plafond.montant_max is not None
        ):

            reste_montant = max(
                Decimal("0.00"),
                Decimal(plafond.montant_max)
                - montant_consomme,
            )

            montant_courant = min(
                montant_courant,
                reste_montant,
            )

        informations.append({
            "plafond": plafond,
            "montant_consomme": montant_consomme,
            "quantite_consommee": quantite_consommee,
            "reste_montant": reste_montant,
            "reste_quantite": reste_quantite,
            "montant_avant": montant_avant,
            "montant_apres": montant_courant,
            "quantite_avant": quantite_avant,
            "quantite_apres": quantite_autorisee,
            "date_debut_periode": date_debut_periode,
            "date_fin_periode": date_fin_periode,
        })

    montant_courant = max(
        Decimal("0.00"),
        montant_courant,
    )

    return (
        montant_courant,
        informations,
        None,
        quantite_autorisee,
    )
