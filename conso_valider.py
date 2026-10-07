def consommation_valider(request, id_consommation):
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

    if "CONSOMMATION_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider une consommation."
        )
        return redirect("consommations")

    try:
        consommation = Consommation.objects.get(
            id_consommation=id_consommation
        )
    except Consommation.DoesNotExist:
        messages.error(
            request,
            "Consommation introuvable."
        )
        return redirect("consommations")

    if request.method == "POST":

        if consommation.statut != "A_TRAITER":
            messages.error(
                request,
                "Cette consommation a déjÃ  été traitée."
            )
            return redirect("consommations")

        consommation.statut = "VALIDEE"
        consommation.date_validation = timezone.now()
        consommation.save()

        messages.success(
            request,
            "Consommation validée avec succès."
        )

    return redirect("consommations")
