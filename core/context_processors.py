def utilisateur_context(request):
    """Ajoute utilisateur, rôles et permissions à TOUS les templates."""
    id_utilisateur = request.session.get("id_utilisateur")
    if not id_utilisateur:
        return {}

    from .models import Utilisateur, UtilisateurRole, RolePermission

    try:
        utilisateur = Utilisateur.objects.get(id_utilisateur=id_utilisateur)
    except Utilisateur.DoesNotExist:
        return {}

    roles = list(
        UtilisateurRole.objects
        .filter(id_utilisateur=utilisateur, statut="ACTIF")
        .select_related("id_role")
    )

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    return {
        "utilisateur": utilisateur,
        "roles": roles,
        "permissions": permissions,
    }