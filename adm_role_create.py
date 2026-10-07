def role_create(request):
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

    if "ROLE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un rôle."
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
        elif Role.objects.filter(code_role=code_role).exists():
            messages.error(
                request,
                "Ce code de rôle existe déjÃ ."
            )
        else:
            Role.objects.create(
                code_role=code_role,
                libelle=libelle,
                description=description or None,
                statut=statut
            )

            messages.success(
                request,
                "Rôle créé avec succès."
            )

            return redirect("roles")

    return render(
        request,
        "core/role_form.html",
        {
            "titre": "Nouveau rôle",
            "page": "roles",
        }
    )
