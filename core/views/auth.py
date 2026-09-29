"""Vues d'authentification : connexion et déconnexion."""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from core.forms import LoginForm


def connexion(request):
    """Page de connexion à l'application."""
    # Si l'utilisateur est déjà connecté via Django ET a un id_utilisateur en session
    if (
        request.user.is_authenticated
        and request.session.get("id_utilisateur")
    ):
        return redirect("accueil")

    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            nom_utilisateur = form.cleaned_data["nom_utilisateur"]
            mot_de_passe = form.cleaned_data["mot_de_passe"]

            utilisateur = authenticate(
                request,
                username=nom_utilisateur,
                password=mot_de_passe,
            )

            if utilisateur is not None and utilisateur.statut == "ACTIF":
                login(request, utilisateur)

                # On pose AUSSI les variables de session custom pour que
                # les vues existantes (accueil, etc.) continuent de fonctionner.
                request.session["id_utilisateur"] = utilisateur.id_utilisateur
                request.session["nom_utilisateur"] = utilisateur.nom_utilisateur

                return redirect("accueil")

            messages.error(
                request,
                "Nom utilisateur ou mot de passe incorrect."
            )
    else:
        form = LoginForm()

    return render(
        request,
        "core/connexion.html",
        {"form": form}
    )


def deconnexion(request):
    """Déconnexion de l'utilisateur."""
    logout(request)
    return redirect("connexion")
