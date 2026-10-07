def utilisateurs(request):
    
    utilisateur = request.utilisateur
    id_utilisateur = utilisateur.id_utilisateur

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

    if "USER_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les utilisateurs."
        )
        return redirect("accueil")

    utilisateurs = Utilisateur.objects.all().order_by(
        "nom",
        "prenom"
    )

    return render(
        request,
        "core/utilisateurs.html",
        {
            "utilisateur": utilisateur,
            "utilisateurs": utilisateurs,
            "permissions": permissions,
            "page": "utilisateurs",
        }
    )


