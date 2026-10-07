def role_detail(request, id_role):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions_utilisateur = set(
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

    if "ROLE_VIEW" not in permissions_utilisateur:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les rôles."
        )
        return redirect("accueil")

    try:
        role = Role.objects.get(id_role=id_role)
    except Role.DoesNotExist:
        messages.error(
            request,
            "Rôle introuvable."
        )
        return redirect("roles")

    permissions_role = (
        RolePermission.objects
        .filter(
            id_role=role,
            id_permission__statut="ACTIF"
        )
        .select_related("id_permission")
        .order_by("id_permission__code_permission")
    )

    return render(
        request,
        "core/role_detail.html",
        {
            "role": role,
            "permissions_role": permissions_role,
            "page": "roles",
        }
    )
