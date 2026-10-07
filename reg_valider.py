def reglement_valider(request, id_reglement):
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
    

    if "REGLEMENT_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider un règlement."
        )
        return redirect("reglements")

    try:
        reglement = Reglement.objects.get(
            id_reglement=id_reglement
        )
    except Reglement.DoesNotExist:
        messages.error(
            request,
            "Règlement introuvable."
        )
        return redirect("reglements")

    if request.method == "POST":

        if reglement.statut != "EN_ATTENTE":
            messages.error(
                request,
                "Ce règlement a déjÃ  été traité."
            )
            return redirect("reglements")

        reglement.statut = "VALIDEE"
        reglement.save()

        facture = reglement.id_facture

        montant_total_regle = (
              Reglement.objects
              .filter(
                  id_facture=facture,
                  statut="VALIDEE"
              )
              .aggregate(total=Sum("montant"))["total"]
              or 0
          )

        # Mettre à jour le statut de la facture selon le montant réglé
        if montant_total_regle >= facture.montant_valide:
            facture.statut = "PAYEE"
        elif montant_total_regle > 0:
            facture.statut = "PARTIELLEMENT_PAYEE"

        facture.save()

        messages.success(
            request,
            f"Règlement validé avec succès. "
            f"Facture {facture.numero_facture} : {facture.statut}."
        )

    return redirect("reglements")


