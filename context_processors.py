from .models import Utilisateur, UtilisateurRole


def utilisateur_context(request):
    """Ajoute l'utilisateur connecté et ses rôles à tous les templates."""
    id_utilisateur = request.session.get("id_utilisateur")
    if not id_utilisateur:
        return {}

    try:
        utilisateur = Utilisateur.objects.get(id_utilisateur=id_utilisateur)
    except Utilisateur.DoesNotExist:
        return {}

    roles = (
        UtilisateurRole.objects
        .filter(id_utilisateur=utilisateur, statut="ACTIF")
        .select_related("id_role")
    )

    return {
        "utilisateur": utilisateur,
        "roles": roles,
    }