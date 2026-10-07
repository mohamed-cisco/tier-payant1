def facture_valider(request, id_facture):
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

    if "FACTURE_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider une facture."
        )
        return redirect("factures")

    try:
        facture = Facture.objects.get(
            id_facture=id_facture
        )
    except Facture.DoesNotExist:
        messages.error(
            request,
            "Facture introuvable."
        )
        return redirect("factures")

    if request.method == "POST":

        if facture.statut != "EN_ATTENTE":
            messages.error(
                request,
                "Cette facture a déjÃ  été traitée."
            )
            return redirect("factures")

        facture.statut = "VALIDEE"
        facture.date_validation = timezone.now()
        facture.utilisateur_validation = str(
            request.session.get("id_utilisateur")
        )
        facture.save()

        # Validation des détails de la facture
        DetailFacture.objects.filter(
            id_facture=facture
        ).update(
            statut="VALIDEE"
        )

        messages.success(
            request,
            "Facture validée avec succès."
        )

    return redirect("factures")
