def contrat_radier(request, id_contrat):
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

    if "CONTRAT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un contrat."
        )
        return redirect("contrats")

    try:
        contrat = Contrat.objects.get(
            id_contrat=id_contrat
        )
    except Contrat.DoesNotExist:
        messages.error(
            request,
            "Contrat introuvable."
        )
        return redirect("contrats")

    if request.method == "POST":
        contrat.statut = "RADIE"
        contrat.date_modification = timezone.now()
        contrat.save()

        messages.success(
            request,
            "Contrat radié avec succès."
        )

    return redirect("contrats")


