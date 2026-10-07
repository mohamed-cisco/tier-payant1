def role_modifier(request, id_role):
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

    if "ROLE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un rôle."
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

    if request.method == "POST":
        code_role = request.POST.get("code_role", "").strip()
        libelle = request.POST.get("libelle", "").strip()
        description = request.POST.get("description", "").strip()
        statut = request.POST.get("statut", "ACTIF")

        if not code_role or not libelle:
            messages.error(
                request,
                "Le code du rôle et le libellé sont obligatoires."
            )
        elif Role.objects.filter(
            code_role=code_role
        ).exclude(
            id_role=id_role
        ).exists():
            messages.error(
                request,
                "Ce code de rôle existe déjÃ ."
            )
        else:
            role.code_role = code_role
            role.libelle = libelle
            role.description = description or None
            role.statut = statut
            role.save()

            messages.success(
                request,
                "Rôle modifié avec succès."
            )

            return redirect("roles")

    return render(
        request,
        "core/role_form.html",
        {
            "titre": "Modifier le rôle",
            "role": role,
        }
    )
@session_utilisateur_required
