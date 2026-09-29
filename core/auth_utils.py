"""Fonctions utilitaires pour l'authentification.

Pendant la transition entre le système custom (session) et Django auth,
on expose des helpers qui fonctionnent avec les deux.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def utilisateur_courant(request):
    """Retourne l'Utilisateur connecté, ou None.

    Utilise d'abord Django auth (request.user),
    puis fallback sur la session custom pour compatibilité.
    """
    # 1. Priorité à Django auth
    if request.user.is_authenticated:
        return request.user

    # 2. Fallback session custom (héritage)
    id_utilisateur = request.session.get("id_utilisateur")
    if not id_utilisateur:
        return None

    from .models import Utilisateur
    try:
        return Utilisateur.objects.get(id_utilisateur=id_utilisateur)
    except Utilisateur.DoesNotExist:
        return None


def session_utilisateur_required(view_func):
    """Décorateur : exige qu'un utilisateur soit connecté.

    Compatible avec l'ancien système (session) et le nouveau (Django).
    Redirige vers /connexion/ si non connecté.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        utilisateur = utilisateur_courant(request)

        if utilisateur is None:
            messages.warning(
                request,
                "Vous devez être connecté pour accéder à cette page."
            )
            return redirect("connexion")

        # On attache l'utilisateur à la requête pour y accéder facilement
        request.utilisateur = utilisateur

        return view_func(request, *args, **kwargs)

    return wrapper