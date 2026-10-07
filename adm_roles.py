def roles(request):
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

    if "ROLE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les rôles."
        )
        return redirect("accueil")

    roles = Role.objects.all().order_by("libelle")

    return render(
        request,
        "core/roles.html",
        {
            "roles": roles,
"permissions": permissions,
"page": "roles",       # ← AJOUTE
        }
    )
