def utilisateur_roles(request, id_utilisateur):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_connecte = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_connecte,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
    )

    if "USER_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier les rôles."
        )
        return redirect("utilisateurs")

    try:
        utilisateur = Utilisateur.objects.get(
            id_utilisateur=id_utilisateur
        )
    except Utilisateur.DoesNotExist:
        messages.error(
            request,
            "Utilisateur introuvable."
        )
        return redirect("utilisateurs")

    roles = Role.objects.filter(
        statut="ACTIF"
    ).order_by("libelle")

    if request.method == "POST":
        roles_selectionnes = request.POST.getlist("roles")

        # Désactiver les rôles actuellement actifs
        UtilisateurRole.objects.filter(
            id_utilisateur=utilisateur,
            statut="ACTIF"
        ).update(
            statut="INACTIF",
            date_fin=timezone.now().date()
        )

        # Ajouter les rôles sélectionnés
        for id_role in roles_selectionnes:
            try:
                role = Role.objects.get(
                    id_role=id_role,
                    statut="ACTIF"
                )
            except Role.DoesNotExist:
                continue

            UtilisateurRole.objects.update_or_create(
                id_utilisateur=utilisateur,
                id_role=role,
                defaults={
                    "date_debut": timezone.now().date(),
                    "date_fin": None,
                    "statut": "ACTIF",
                }
            )

        messages.success(
            request,
            "Les rôles de l'utilisateur ont été modifiés avec succès."
        )

        return redirect("utilisateurs")

    roles_actuels = set(
        UtilisateurRole.objects
        .filter(
            id_utilisateur=utilisateur,
            statut="ACTIF"
        )
        .values_list(
            "id_role_id",
            flat=True
        )
    )

    return render(
        request,
        "core/utilisateur_roles.html",
        {
            "utilisateur": utilisateur,
            "roles": roles,
            "roles_actuels": roles_actuels,
            "page": "utilisateurs",
        }
    )
