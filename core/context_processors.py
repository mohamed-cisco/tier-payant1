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


def version_context(request):
    """Ajoute la version dans tous les templates."""
    try:
        from core.version import VERSION, get_date_version, get_nom_version

        return {
            "VERSION": VERSION,
            "DATE_VERSION": get_date_version(),
            "NOM_VERSION": get_nom_version(),
        }
    except ImportError:
        return {
            "VERSION": "1.0.0",
            "DATE_VERSION": "2026-01-01",
            "NOM_VERSION": "Version initiale",
        }