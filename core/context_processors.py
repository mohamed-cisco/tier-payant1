from .models import UtilisateurRole


def utilisateur_context(request):
    """Ajoute automatiquement l'utilisateur connecté et ses rôles au contexte de tous les templates."""
    id_utilisateur = request.session.get("id_utilisateur")
    if not id_utilisateur:
        return {}

    from .models import Utilisateur
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