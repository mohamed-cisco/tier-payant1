"""Vues de gestion des rôles et permissions."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.auth_utils import session_utilisateur_required
from core.models import (
    Permission,
    Role,
    RolePermission,
)


def roles(request):
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

    if "ROLE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les rÃ´les."
        )
        return redirect("accueil")

    roles = Role.objects.all().order_by("libelle")

    return render(
        request,
        "core/roles.html",
        {
            "roles": roles,
"permissions": permissions,
        }
    )
def role_create(request):
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

    if "ROLE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er un rÃ´le."
        )
        return redirect("roles")

    if request.method == "POST":
        code_role = request.POST.get("code_role", "").strip()
        libelle = request.POST.get("libelle", "").strip()
        description = request.POST.get("description", "").strip()
        statut = request.POST.get("statut", "ACTIF")

        if not code_role or not libelle:
            messages.error(
                request,
                "Le code du rÃ´le et le libellÃ© sont obligatoires."
            )
        elif Role.objects.filter(code_role=code_role).exists():
            messages.error(
                request,
                "Ce code de rÃ´le existe dÃ©jÃ ."
            )
        else:
            Role.objects.create(
                code_role=code_role,
                libelle=libelle,
                description=description or None,
                statut=statut
            )

            messages.success(
                request,
                "RÃ´le crÃ©Ã© avec succÃ¨s."
            )

            return redirect("roles")

    return render(
        request,
        "core/role_form.html",
        {
            "titre": "Nouveau rÃ´le",
        }
    )
def role_detail(request, id_role):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions_utilisateur = set(
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

    if "ROLE_VIEW" not in permissions_utilisateur:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les rÃ´les."
        )
        return redirect("accueil")

    try:
        role = Role.objects.get(id_role=id_role)
    except Role.DoesNotExist:
        messages.error(
            request,
            "RÃ´le introuvable."
        )
        return redirect("roles")

    permissions_role = (
        RolePermission.objects
        .filter(
            id_role=role,
            id_permission__statut="ACTIF"
        )
        .select_related("id_permission")
        .order_by("id_permission__code_permission")
    )

    return render(
        request,
        "core/role_detail.html",
        {
            "role": role,
            "permissions_role": permissions_role,
        }
    )
def role_permissions(request, id_role):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions_utilisateur = set(
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

    if "ROLE_PERMISSION" not in permissions_utilisateur:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de gÃ©rer les permissions."
        )
        return redirect("roles")

    try:
        role = Role.objects.get(id_role=id_role)
    except Role.DoesNotExist:
        messages.error(
            request,
            "RÃ´le introuvable."
        )
        return redirect("roles")

    permissions = Permission.objects.filter(
        statut="ACTIF"
    ).order_by(
        "module",
        "libelle"
    )

    permissions_role = set(
        RolePermission.objects
        .filter(
            id_role=role
        )
        .values_list(
            "id_permission_id",
            flat=True
        )
    )

    if request.method == "POST":

        permissions_selectionnees = request.POST.getlist(
            "permissions"
        )

        RolePermission.objects.filter(
            id_role=role
        ).delete()

        for id_permission in permissions_selectionnees:
            try:
                permission = Permission.objects.get(
                    id_permission=int(id_permission),
                    statut="ACTIF"
                )

                RolePermission.objects.create(
                    id_role=role,
                    id_permission=permission
                )

            except (Permission.DoesNotExist, ValueError):
                continue

        messages.success(
            request,
            "Permissions du rÃ´le mises Ã  jour avec succÃ¨s."
        )

        return redirect(
            "role_permissions",
            id_role=role.id_role
        )

    return render(
        request,
        "core/role_permissions.html",
        {
            "role": role,
            "permissions": permissions,
            "permissions_role": permissions_role,
        }
    )
def role_modifier(request, id_role):
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

    if "ROLE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un rÃ´le."
        )
        return redirect("roles")

    try:
        role = Role.objects.get(id_role=id_role)
    except Role.DoesNotExist:
        messages.error(
            request,
            "RÃ´le introuvable."
        )
        return redirect("roles")

    if request.method == "POST":
        code_role = request.POST.get("code_role", "").strip()
        libelle = request.POST.get("libelle", "").strip()
        description = request.POST.get("description", "").strip()
        statut = request.POST.get("statut", "ACTIF")

        if not code_role or not libelle:
            messages.error(
                request,
                "Le code du rÃ´le et le libellÃ© sont obligatoires."
            )
        elif Role.objects.filter(
            code_role=code_role
        ).exclude(
            id_role=id_role
        ).exists():
            messages.error(
                request,
                "Ce code de rÃ´le existe dÃ©jÃ ."
            )
        else:
            role.code_role = code_role
            role.libelle = libelle
            role.description = description or None
            role.statut = statut
            role.save()

            messages.success(
                request,
                "RÃ´le modifiÃ© avec succÃ¨s."
            )

            return redirect("roles")

    return render(
        request,
        "core/role_form.html",
        {
            "titre": "Modifier le rÃ´le",
            "role": role,
        }
    )
