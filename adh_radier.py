def adhesion_radier(request, id_adhesion):
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

    if "ADHESION_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une adhésion."
        )
        return redirect("adhesions")

    try:
        adhesion = Adhesion.objects.get(
            id_adhesion=id_adhesion
        )
    except Adhesion.DoesNotExist:
        messages.error(
            request,
            "Adhésion introuvable."
        )
        return redirect("adhesions")

    if request.method == "POST":
        adhesion.statut = "RADIE"
        adhesion.save()

        messages.success(
            request,
            "Adhésion radiée avec succès."
        )

    return redirect("adhesions")
