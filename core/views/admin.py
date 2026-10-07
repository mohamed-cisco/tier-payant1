# core/views/admin.py
"""
Vues d'administration : utilisateurs, rôles, audit.

Fonctions :
- utilisateurs : liste
- utilisateur_create : créer
- utilisateur_modifier : modifier
- utilisateur_roles : gérer rôles
- roles : liste
- role_create : créer
- role_detail : détail
- role_permissions : permissions
- role_modifier : modifier
- audit_logs : journal d'audit
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import (
    UtilisateurForm,
    
)
from core.models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    Utilisateur,
    UtilisateurRole,
)
from core.views.dashboard import enregistrer_audit
from core.views.decorators import session_utilisateur_required

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
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
    )

    if "USER_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les utilisateurs."
        )
        return redirect("accueil")

    utilisateurs = Utilisateur.objects.all().order_by(
        "nom",
        "prenom"
    )

    return render(
        request,
        "core/utilisateurs.html",
        {
            "utilisateur": utilisateur,
            "utilisateurs": utilisateurs,
            "permissions": permissions,
            "page": "utilisateurs",
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
            "Vous n'avez pas l'autorisation de créer un utilisateur."
        )
        return redirect("utilisateurs")

    if request.method == "POST":
        form = UtilisateurForm(request.POST)

        if form.is_valid():
                        # Créer l'objet SANS sauvegarder
            nouvel_utilisateur = Utilisateur(
                nom_utilisateur=form.cleaned_data["nom_utilisateur"],
                nom=form.cleaned_data["nom"],
                prenom=form.cleaned_data["prenom"],
                email=form.cleaned_data["email"] or None,
                telephone=form.cleaned_data["telephone"] or None,
                statut=form.cleaned_data["statut"],
                is_active=True,
                date_creation=timezone.now(),
            )

            # Utiliser set_password (met à jour password ET mot_de_passe_hash)
            nouvel_utilisateur.set_password(
                form.cleaned_data["mot_de_passe"]
            )
            nouvel_utilisateur.mot_de_passe_hash = nouvel_utilisateur.password
            nouvel_utilisateur.save()

            messages.success(
                request,
                "Utilisateur créé avec succès."
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
            "page": "utilisateurs",
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
                utilisateur.set_password(mot_de_passe)
                utilisateur.mot_de_passe_hash = utilisateur.password

            utilisateur.save()

            messages.success(
                request,
                "Utilisateur modifié avec succès."
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
            "Vous n'avez pas l'autorisation de modifier les rôles."
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

        # Désactiver les rôles actuellement actifs
        UtilisateurRole.objects.filter(
            id_utilisateur=utilisateur,
            statut="ACTIF"
        ).update(
            statut="INACTIF",
            date_fin=timezone.now().date()
        )

        # Ajouter les rôles sélectionnés
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
            "Les rôles de l'utilisateur ont été modifiés avec succès."
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
            "page": "utilisateurs",
        }
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
            "Vous n'avez pas l'autorisation de consulter les rôles."
        )
        return redirect("accueil")

    roles = Role.objects.all().order_by("libelle")

    return render(
        request,
        "core/roles.html",
        {
            "roles": roles,
"permissions": permissions,
"page": "roles",       # ← AJOUTE
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
            "Vous n'avez pas l'autorisation de créer un rôle."
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
                "Le code du rôle et le libellé sont obligatoires."
            )
        elif Role.objects.filter(code_role=code_role).exists():
            messages.error(
                request,
                "Ce code de rôle existe déjÃ ."
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
                "Rôle créé avec succès."
            )

            return redirect("roles")

    return render(
        request,
        "core/role_form.html",
        {
            "titre": "Nouveau rôle",
            "page": "roles",
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
            "Vous n'avez pas l'autorisation de consulter les rôles."
        )
        return redirect("accueil")

    try:
        role = Role.objects.get(id_role=id_role)
    except Role.DoesNotExist:
        messages.error(
            request,
            "Rôle introuvable."
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
            "page": "roles",
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
            "Vous n'avez pas l'autorisation de gérer les permissions."
        )
        return redirect("roles")

    try:
        role = Role.objects.get(id_role=id_role)
    except Role.DoesNotExist:
        messages.error(
            request,
            "Rôle introuvable."
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
            "Permissions du rôle mises Ã  jour avec succès."
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
            "page": "roles",
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
            "Vous n'avez pas l'autorisation de modifier un rôle."
        )
        return redirect("roles")

    try:
        role = Role.objects.get(id_role=id_role)
    except Role.DoesNotExist:
        messages.error(
            request,
            "Rôle introuvable."
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
                "Le code du rôle et le libellé sont obligatoires."
            )
        elif Role.objects.filter(
            code_role=code_role
        ).exclude(
            id_role=id_role
        ).exists():
            messages.error(
                request,
                "Ce code de rôle existe déjÃ ."
            )
        else:
            role.code_role = code_role
            role.libelle = libelle
            role.description = description or None
            role.statut = statut
            role.save()

            messages.success(
                request,
                "Rôle modifié avec succès."
            )

            return redirect("roles")

    return render(
        request,
        "core/role_form.html",
        {
            "titre": "Modifier le rôle",
            "role": role,
        }
    )
@session_utilisateur_required



def audit_logs(request):
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

    if "AUDIT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les journaux d'audit."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    module = request.GET.get("module", "").strip()
    type_action = request.GET.get("type_action", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    audits = (
        AuditLog.objects
        .select_related("id_utilisateur")
        .all()
        .order_by("-date_action", "-id_audit")
    )

    if recherche:
        from django.db.models import Q

        audits = audits.filter(
            Q(module__icontains=recherche)
            | Q(table_cible__icontains=recherche)
            | Q(description__icontains=recherche)
            | Q(type_action__icontains=recherche)
            | Q(adresse_ip__icontains=recherche)
            | Q(poste__icontains=recherche)
        )

    if module:
        audits = audits.filter(module=module)

    if type_action:
        audits = audits.filter(type_action=type_action)

    if date_debut:
        audits = audits.filter(date_action__date__gte=date_debut)

    if date_fin:
        audits = audits.filter(date_action__date__lte=date_fin)

    modules = (
        AuditLog.objects
        .exclude(module__isnull=True)
        .exclude(module="")
        .values_list("module", flat=True)
        .distinct()
        .order_by("module")
    )

    types_action = (
        AuditLog.objects
        .exclude(type_action__isnull=True)
        .exclude(type_action="")
        .values_list("type_action", flat=True)
        .distinct()
        .order_by("type_action")
    )

    return render(
        request,
        "core/audit.html",
        {
            "audits": audits,
            "permissions": permissions,
            "recherche": recherche,
            "module": module,
            "type_action": type_action,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "modules": modules,
            "types_action": types_action,
            "page": "audit",
        }
    )
