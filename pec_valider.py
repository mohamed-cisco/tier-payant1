def prise_en_charge_valider(request, id_pec):
    """
    Valide la PEC et crée les consommations automatiquement.
    
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
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("prises_en_charge")

    # ============================================================
    # 2. RÉCUPÉRATION DE LA PEC
    # ============================================================
    try:
        pec = (
            PriseEnCharge.objects
            .select_related(
                "id_demande",
                "id_demande__id_personne_beneficiaire",
                "id_demande__id_contrat",
                "id_demande__id_prestataire",
            )
            .get(id_pec=id_pec)
        )
    except PriseEnCharge.DoesNotExist:
        messages.error(request, "PEC introuvable.")
        return redirect("prises_en_charge")

    if pec.statut != "EN_ATTENTE":
        messages.error(request, "Cette PEC a déjà été traitée.")
        return redirect("prise_en_charge_details", id_pec=pec.id_pec)

    # ============================================================
    # 3. CALCUL VIA LE MODULE CENTRALISÉ
    # ============================================================
    from core.services.calculs import calculer_pour_demande

    resultats = calculer_pour_demande(pec.id_demande)

    # Vérifier les erreurs
    if resultats["erreurs"]:
        for erreur in resultats["erreurs"]:
            messages.warning(request, erreur)

    # Si aucun acte → erreur
    if resultats["nb_actes"] == 0:
        messages.error(request, "Aucun acte à valider.")
        return redirect("prise_en_charge_details", id_pec=pec.id_pec)

    # ============================================================
    # 4. TRAITEMENT DU POST
    # ============================================================
    if request.method == "POST":
        try:
            # 4.1 — Mise à jour de la PEC
            pec.montant_demande = resultats["total_demande"]
            pec.montant_accepte = resultats["total_accepte"]
            pec.montant_rejete = resultats["total_rejete"]
            pec.statut = "ACCEPTEE"
            pec.utilisateur_validation = str(id_utilisateur)
            pec.save()

            # 4.2 — Créer les détails PEC + Consommations
            nb_consos = 0
            for calcul in resultats["calculs"]:
                detail = calcul["detail"]

                # Créer le détail PEC
                pec_detail = PriseEnChargeDetail.objects.create(
                    id_pec=pec,
                    id_detail_demande=detail,
                    id_acte=detail.id_acte,
                    quantite=detail.quantite,
                    montant_demande=calcul["montant_demande"],
                    montant_accorde=calcul["montant_accorde"],
                    montant_rejete=calcul["montant_rejete"],
                    taux_applique=calcul["taux"],
                    franchise_appliquee=calcul["franchise"],
                    statut="ACCEPTEE" if calcul["montant_accorde"] > 0 else "REJETEE",
                    motif_rejet=calcul["erreur"],
                )

                # Trouver l'adhésion active du bénéficiaire
                personne = pec.id_demande.id_personne_beneficiaire
                adhesion = _trouver_adhesion_active(personne, pec.id_demande.id_contrat)

                if not adhesion:
                    continue  # Pas d'adhésion → pas de consommation

                # Trouver la garantie
                garantie = None
                if calcul.get("garantie_acte"):
                    garantie = calcul["garantie_acte"].id_garantie

                if not garantie:
                    continue  # Pas de garantie → pas de consommation

                # Créer la consommation
                Consommation.objects.create(
                    id_detail_pec=pec_detail,
                    id_personne_beneficiaire=personne,
                    id_adhesion=adhesion,
                    id_acte=detail.id_acte,
                    id_sous_acte=detail.id_sous_acte,
                    id_garantie=garantie,
                    id_prestataire=pec.id_demande.id_prestataire,
                    date_prestation=timezone.now().date(),
                    exercice=timezone.now().year,
                    quantite=detail.quantite,
                    montant_base=calcul["montant_demande"],
                    montant_prise_en_charge=calcul["montant_accorde"],
                    montant_reste=calcul["montant_rejete"],
                    statut="VALIDEE",
                )
                nb_consos += 1

            # 4.3 — Audit
            enregistrer_audit(
                request=request,
                type_action="VALIDATION_PEC",
                module="PEC",
                table_cible="prise_en_charge",
                id_enregistrement=pec.id_pec,
                ancienne_valeur="Statut : EN_ATTENTE",
                nouvelle_valeur=f"Statut : ACCEPTEE, {nb_consos} consommation(s)",
                description=f"Validation de la PEC {pec.numero_pec} via moteur centralisé",
            )

            # 4.4 — Message de succès
            messages.success(
                request,
                f"✅ PEC {pec.numero_pec} validée. "
                f"{nb_consos} consommation(s) créée(s)."
            )

            return redirect("prise_en_charge_details", id_pec=pec.id_pec)

        except Exception as e:
            messages.error(request, f"Erreur lors de la validation : {e}")
            return redirect("prise_en_charge_details", id_pec=pec.id_pec)

    # ============================================================
    # 5. AFFICHAGE (GET)
    # ============================================================
    return render(
        request,
        "core/prise_en_charge_valider.html",
        {
            "pec": pec,
            "calculs": resultats["calculs"],
            "montant_accepte_total": resultats["total_accepte"],
            "montant_rejete_total": resultats["total_rejete"],
            "erreurs": resultats["erreurs"],
        }
    )


