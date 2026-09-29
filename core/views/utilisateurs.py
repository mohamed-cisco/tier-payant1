"""Vues de gestion des utilisateurs et de leurs rôles."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.auth_utils import session_utilisateur_required
from core.forms import UtilisateurForm
from core.models import (
    Role,
    RolePermission,
    Utilisateur,
    UtilisateurRole,
)


@session_utilisateur_required
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
        .values_list("id_permission__code_permission", flat=True)
    )

    if "USER_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les utilisateurs."
        )
        return redirect("accueil")

    utilisateurs_liste = Utilisateur.objects.all().order_by("nom", "prenom")

    return render(
        request,
        "core/utilisateurs.html",
        {
            "utilisateur": utilisateur,
            "permissions": permissions,
            "utilisateurs": utilisateurs_liste,
        }
    )
def utilisateur_create(request):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

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

    if "USER_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er un utilisateur."
        )
        return redirect("utilisateurs")

    if request.method == "POST":
        form = UtilisateurForm(request.POST)

        if form.is_valid():
            Utilisateur.objects.create(
                nom_utilisateur=form.cleaned_data["nom_utilisateur"],
                mot_de_passe_hash=make_password(
                    form.cleaned_data["mot_de_passe"]
                ),
                nom=form.cleaned_data["nom"],
                prenom=form.cleaned_data["prenom"],
                email=form.cleaned_data["email"] or None,
                telephone=form.cleaned_data["telephone"] or None,
                statut=form.cleaned_data["statut"],
                date_creation=timezone.now()
            )

            messages.success(
                request,
                "Utilisateur crÃ©Ã© avec succÃ¨s."
            )

            return redirect("utilisateurs")

    else:
        form = UtilisateurForm()

    return render(
        request,
        "core/utilisateur_form.html",
        {
            "form": form,
            "titre": "Nouvel utilisateur",
        }
    )


def utilisateur_modifier(request, id_utilisateur):
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
            "Vous n'avez pas l'autorisation de modifier un utilisateur."
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

    if request.method == "POST":
        form = UtilisateurForm(
            request.POST,
            instance=utilisateur
        )

        if form.is_valid():
            utilisateur.nom_utilisateur = (
                form.cleaned_data["nom_utilisateur"]
            )

            utilisateur.nom = form.cleaned_data["nom"]
            utilisateur.prenom = form.cleaned_data["prenom"]
            utilisateur.email = (
                form.cleaned_data["email"] or None
            )
            utilisateur.telephone = (
                form.cleaned_data["telephone"] or None
            )
            utilisateur.statut = form.cleaned_data["statut"]

            mot_de_passe = form.cleaned_data["mot_de_passe"]

            if mot_de_passe:
                utilisateur.mot_de_passe_hash = make_password(
                    mot_de_passe
                )

            utilisateur.save()

            messages.success(
                request,
                "Utilisateur modifiÃ© avec succÃ¨s."
            )

            return redirect("utilisateurs")

    else:
        form = UtilisateurForm(
            instance=utilisateur
        )

    return render(
        request,
        "core/utilisateur_form.html",
        {
            "form": form,
            "titre": "Modifier l'utilisateur",
        }
    )
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
            "Vous n'avez pas l'autorisation de modifier les rÃ´les."
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

        # DÃ©sactiver les rÃ´les actuellement actifs
        UtilisateurRole.objects.filter(
            id_utilisateur=utilisateur,
            statut="ACTIF"
        ).update(
            statut="INACTIF",
            date_fin=timezone.now().date()
        )

        # Ajouter les rÃ´les sÃ©lectionnÃ©s
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
            "Les rÃ´les de l'utilisateur ont Ã©tÃ© modifiÃ©s avec succÃ¨s."
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
        }
    )
