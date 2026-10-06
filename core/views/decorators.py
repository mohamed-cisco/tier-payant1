# core/views/decorators.py
"""
Décorateurs personnalisés pour les vues.
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from core.models import UtilisateurRole


def session_utilisateur_required(view_func):
    """
    Décorateur qui vérifie que l'utilisateur est connecté.
    
    Si connecté :
        - Ajoute request.utilisateur
        - Ajoute request.roles
        - Ajoute request.permissions
    Sinon :
        - Redirige vers connexion
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Vérifier la session
        id_utilisateur = request.session.get("id_utilisateur")

        if not id_utilisateur:
            messages.error(request, "Veuillez vous connecter.")
            return redirect("connexion")

        # Récupérer l'utilisateur
        try:
            from core.models import Utilisateur
            utilisateur = Utilisateur.objects.get(id_utilisateur=id_utilisateur)
        except Utilisateur.DoesNotExist:
            messages.error(request, "Utilisateur introuvable.")
            return redirect("connexion")

        if utilisateur.statut != "ACTIF":
            messages.error(request, "Compte inactif.")
            return redirect("connexion")

        # Récupérer les rôles
        roles = (
            UtilisateurRole.objects
            .filter(id_utilisateur=utilisateur, statut="ACTIF")
            .select_related("id_role")
        )

        # Récupérer les permissions
        from core.models import RolePermission
        permissions = set(
            RolePermission.objects
            .filter(
                id_role__utilisateurrole__id_utilisateur=utilisateur,
                id_role__utilisateurrole__statut="ACTIF",
                id_permission__statut="ACTIF"
            )
            .values_list("id_permission__code_permission", flat=True)
        )

        # Ajouter à la requête
        request.utilisateur = utilisateur
        request.roles = roles
        request.permissions = permissions

        return view_func(request, *args, **kwargs)

    return wrapper