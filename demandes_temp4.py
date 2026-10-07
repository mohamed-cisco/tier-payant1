def demande_tp_valider(request, id_demande):
    """
    Valide une demande TP et crée la PEC automatiquement.
    
    Utilise le module centralisé core.services.calculs pour TOUS les calculs.
    """
    # ============================================================
    # 1. VÉRIFICATIONS
    # ============================================================
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

    if "DEMANDE_VALIDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de valider une demande.")
        return redirect("demandes_tp")

    # ============================================================
    # 2. RÉCUPÉRATION DE LA DEMANDE
    # ============================================================
    try:
        demande = (
            DemandeTp.objects
            .select_related(
                "id_personne_beneficiaire",
                "id_contrat",
                "id_prestataire",
            )
            .get(id_demande=id_demande)
        )
    except DemandeTp.DoesNotExist:
        messages.error(request, "Demande de tiers payant introuvable.")
        return redirect("demandes_tp")

    if demande.statut != "EN_ATTENTE":
        messages.error(request, "Cette demande n'est plus en attente de validation.")
        return redirect("demande_tp_details", id_demande=demande.id_demande)

    # ============================================================
    # 3. CALCUL VIA LE MODULE CENTRALISÉ
    # ============================================================
    from core.services.calculs import calculer_pour_demande

    resultats = calculer_pour_demande(demande)

    # Vérifier que la demande a des actes
    if resultats["nb_actes"] == 0:
        messages.error(request, "Impossible de valider une demande sans acte.")
        return redirect("demande_tp_details", id_demande=demande.id_demande)

    # Afficher les erreurs éventuelles
    if resultats["erreurs"]:
        for erreur in resultats["erreurs"]:
            messages.warning(request, erreur)

    # ============================================================
    # 4. TRAITEMENT DU POST
    # ============================================================
    if request.method == "POST":
        # Bloquer si un acte a une erreur critique
        if resultats["erreurs"]:
            messages.error(
                request,
                "La demande ne peut pas être validée car un acte "
                "n'a pas de garantie applicable."
            )
            return redirect("demande_tp_valider", id_demande=demande.id_demande)

        try:
            # 4.1 — Générer le numéro de PEC
            numero_pec = _generer_numero_pec()

            # 4.2 — Créer la PEC
            pec = PriseEnCharge.objects.create(
                numero_pec=numero_pec,
                id_demande=demande,
                date_pec=timezone.now(),
                montant_demande=resultats["total_demande"],
                montant_accepte=resultats["total_accepte"],
                montant_rejete=resultats["total_rejete"],
                statut="EN_ATTENTE",
                date_expiration=timezone.now().date() + timedelta(days=30),
                utilisateur_validation=str(id_utilisateur),
            )

            # 4.3 — Mettre à jour le statut de la demande
            demande.statut = "ACCEPTEE"
            demande.date_decision = timezone.now()
            demande.save()

            # 4.4 — Audit
            enregistrer_audit(
                request=request,
                type_action="VALIDATION",
                module="DEMANDES TP",
                table_cible="demande_tp",
                id_enregistrement=demande.id_demande,
                ancienne_valeur="Statut : EN_ATTENTE",
                nouvelle_valeur=f"Statut : ACCEPTEE, PEC : {pec.numero_pec}",
                description=(
                    f"Validation de la demande {demande.numero_demande} "
                    f"et création de la PEC {pec.numero_pec}"
                ),
            )

            # 4.5 — Message de succès
            messages.success(
                request,
                f"✅ Demande {demande.numero_demande} validée. "
                f"PEC {pec.numero_pec} créée avec succès."
            )

            # 4.6 — Rediriger vers la PEC
            return redirect("prise_en_charge_details", id_pec=pec.id_pec)

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la création de la prise en charge : {e}"
            )
            return redirect("demande_tp_details", id_demande=demande.id_demande)

    # ============================================================
    # 5. AFFICHAGE (GET)
    # ============================================================
    return render(
        request,
        "core/demande_tp_valider.html",
        {
            "demande": demande,
            "calculs": resultats["calculs"],
            "montant_accepte_total": resultats["total_accepte"],
            "montant_rejete_total": resultats["total_rejete"],
            "erreurs": resultats["erreurs"],
        }
    )


