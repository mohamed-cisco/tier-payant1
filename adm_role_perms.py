def role_permissions(request, id_role):
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

    if "ROLE_PERMISSION" not in permissions_utilisateur:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de gérer les permissions."
        )
        return redirect("roles")

    try:
        role = Role.objects.get(id_role=id_role)
    except Role.DoesNotExist:
        messages.error(
            request,
            "Rôle introuvable."
        )
        return redirect("roles")

    permissions = Permission.objects.filter(
        statut="ACTIF"
    ).order_by(
        "module",
        "libelle"
    )

    permissions_role = set(
        RolePermission.objects
        .filter(
            id_role=role
        )
        .values_list(
            "id_permission_id",
            flat=True
        )
    )

    if request.method == "POST":

        permissions_selectionnees = request.POST.getlist(
            "permissions"
        )

        RolePermission.objects.filter(
            id_role=role
        ).delete()

        for id_permission in permissions_selectionnees:
            try:
                permission = Permission.objects.get(
                    id_permission=int(id_permission),
                    statut="ACTIF"
                )

                RolePermission.objects.create(
                    id_role=role,
                    id_permission=permission
                )

            except (Permission.DoesNotExist, ValueError):
                continue

        messages.success(
            request,
            "Permissions du rôle mises Ã  jour avec succès."
        )

        return redirect(
            "role_permissions",
            id_role=role.id_role
        )

    return render(
        request,
        "core/role_permissions.html",
        {
            "role": role,
            "permissions": permissions,
            "permissions_role": permissions_role,
            "page": "roles",
        }
    )
