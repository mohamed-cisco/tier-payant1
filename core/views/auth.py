# core/views/auth.py
"""
Vues d'authentification : connexion et déconnexion.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from core.forms import LoginForm


def connexion(request):
    """Page de connexion utilisateur."""
    # Si déjà connecté
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

                # Variables de session custom
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
    """Déconnexion utilisateur."""
    logout(request)
    return redirect("connexion")