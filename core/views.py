from decimal import Decimal
from datetime import date, timedelta
import os
import hashlib

from django.core.files.storage import default_storage
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import FileResponse, JsonResponse
from django import forms
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncMonth
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .auth_utils import utilisateur_courant, session_utilisateur_required

from .forms import (
    LoginForm,
    UtilisateurForm,
    AdherentForm,
    SouscripteurForm,
    ContratForm,
    ContratGarantieForm,
    GarantieForm,
    ActeForm,
    SousActeForm,
    TarifSousActeForm,
    GarantieActeForm,
    AdhesionForm,
    PersonneForm,
    AyantDroitForm,
    PrestataireForm,
    DemandeTpForm,
    DemandeTpDetailForm,
    ConsommationForm,
    FactureForm,
    ReglementForm,
    RecoursForm,
    DecisionRecoursForm,
    DocumentForm,
    ConventionForm,
    PlafondForm,
    ImportAdherentForm,
    TypePrestationForm,
)
from .models import (
    Utilisateur,
    UtilisateurRole,
    RolePermission,
    Role,
    Permission,
    AuditLog,
    Personne,
    Adherent,
    Souscripteur,
    Contrat,
    Garantie,
    Acte,
    SousActe,
    TarifSousActe,
    TypePrestation,
    GarantieActe,
    Plafond,
    Adhesion,
    AyantDroit,
    Prestataire,
    Convention,
    Document,
    DemandeTp,
    DemandeTpDetail,
    DemandeTpDocument,
    PriseEnCharge,
    PriseEnChargeDetail,
    ContratGarantie,
    Consommation,
    Facture,
    DetailFacture,
    Reglement,
    Recours,
    DecisionRecours,
    RecoursDocument,
)

def enregistrer_audit(
    request,
    type_action,
    module,
    table_cible=None,
    id_enregistrement=None,
    ancienne_valeur=None,
    nouvelle_valeur=None,
    description=None,
):
    id_utilisateur = request.session.get("id_utilisateur")

    AuditLog.objects.create(
        id_utilisateur_id=id_utilisateur,
        date_action=timezone.now(),
        type_action=type_action,
        module=module,
        table_cible=table_cible,
        id_enregistrement=id_enregistrement,
        ancienne_valeur=ancienne_valeur,
        nouvelle_valeur=nouvelle_valeur,
        adresse_ip=request.META.get("REMOTE_ADDR"),
        poste=request.META.get("COMPUTERNAME"),
        description=description,
    )

@session_utilisateur_required
def accueil(request):
    
    utilisateur = request.utilisateur
    id_utilisateur = utilisateur.id_utilisateur

    roles = (
        UtilisateurRole.objects
        .filter(
            id_utilisateur=id_utilisateur,
            statut="ACTIF"
        )
        .select_related("id_role")
    )

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
        # =========================
    # STATISTIQUES DU TABLEAU DE BORD
    # =========================

    nombre_adherents = Adherent.objects.count()

    contrats_actifs = Contrat.objects.filter(
        statut="ACTIF"
    ).count()

    demandes_en_attente = DemandeTp.objects.filter(
        statut="EN_ATTENTE"
    ).count()

    factures_en_attente = Facture.objects.filter(
        statut="EN_ATTENTE"
    ).count()
    montant_factures_validees = (
    Facture.objects
    .filter(statut__in=["VALIDEE", "PAYEE"])
    .aggregate(total=Sum("montant_valide"))["total"]
    or 0
)

    montant_paye = (
        Reglement.objects
        .filter(statut="VALIDEE")
        .aggregate(total=Sum("montant"))["total"]
        or 0
    )

    reste_a_payer = montant_factures_validees - montant_paye

    adherents_actifs = Adherent.objects.filter(
        statut="ACTIF"
    ).count()

    demandes_acceptees = DemandeTp.objects.filter(
        statut="ACCEPTEE"
    ).count()

    factures_payees = Facture.objects.filter(
        statut="PAYEE"
    ).count()

    dernieres_demandes = DemandeTp.objects.order_by(
        "-date_demande"
    )[:5]

    dernieres_factures = Facture.objects.order_by(
        "-date_facture"
    )[:5]

    # =========================
    # DONNÉES GRAPHIQUE DEMANDES TP
    # =========================

    demandes_par_mois = (
        DemandeTp.objects
        .annotate(mois=TruncMonth("date_demande"))
        .values("mois")
        .annotate(total=Count("id_demande"))
        .order_by("mois")
    )

    graphique_labels = [
        item["mois"].strftime("%m/%Y")
        for item in demandes_par_mois
    ]

    graphique_demandes = [
        item["total"]
        for item in demandes_par_mois
    ]
    # =========================
    # RÉPARTITION PAR TYPE DE PRESTATION
    # =========================

    prestations_par_type = (
        DemandeTpDetail.objects
        .values("id_acte__id_type_prestation__libelle")
        .annotate(total=Count("id_detail"))
        .order_by("-total")
    )

    prestation_labels = [
        item["id_acte__id_type_prestation__libelle"]
        for item in prestations_par_type
    ]

    prestation_totaux = [
        item["total"]
        for item in prestations_par_type
    ]
    return render(
        request,
        "core/accueil.html",
        {
            "utilisateur": utilisateur,
            "roles": roles,
            "permissions": permissions,
            "nombre_adherents": nombre_adherents,
            "contrats_actifs": contrats_actifs,
            "demandes_en_attente": demandes_en_attente,
            "factures_en_attente": factures_en_attente,
            "montant_factures_validees": montant_factures_validees,
            "montant_paye": montant_paye,
            "reste_a_payer": reste_a_payer,
            "adherents_actifs": adherents_actifs,
            "demandes_acceptees": demandes_acceptees,
            "factures_payees": factures_payees, 
            "dernieres_demandes": dernieres_demandes,
            "dernieres_factures": dernieres_factures,
            "graphique_labels": graphique_labels,
            "graphique_demandes": graphique_demandes,
            "prestation_labels": prestation_labels,
            "prestation_totaux": prestation_totaux,
        }
    )
def connexion(request):
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

                # ⚠️ TRÈS IMPORTANT : on pose AUSSI les variables de session
                # custom pour que les vues existantes (accueil, etc.) continuent
                # de fonctionner.
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
    logout(request)
    return redirect("connexion")



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
@session_utilisateur_required
def adherents(request):
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

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les adh?rents."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    adherents = (
        Adherent.objects
        .select_related("id_personne")
        .all()
        .order_by("-id_adherent")
    )

    if recherche:
        from django.db.models import Q

        adherents = adherents.filter(
            Q(numero_adherent__icontains=recherche)
            | Q(id_personne__numero_personne__icontains=recherche)
            | Q(id_personne__nom__icontains=recherche)
            | Q(id_personne__prenom__icontains=recherche)
            | Q(id_personne__telephone__icontains=recherche)
        )

    if statut:
        adherents = adherents.filter(statut=statut)

    return render(
        request,
        "core/adherents.html",
        {
            "adherents": adherents,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )

def adherent_detail(request, id_adherent):
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

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter cet adh?rent."
        )
        return redirect("adherents")

    try:
        adherent = (
            Adherent.objects
            .select_related("id_personne")
            .get(id_adherent=id_adherent)
        )
    except Adherent.DoesNotExist:
        messages.error(
            request,
            "Adh?rent introuvable."
        )
        return redirect("adherents")

    ayants_droit = (
        AyantDroit.objects
        .select_related("id_personne")
        .filter(id_adherent=adherent)
        .order_by("id_ayant_droit")
    )

    return render(
        request,
        "core/adherent_detail.html",
        {
            "adherent": adherent,
            "ayants_droit": ayants_droit,
            "permissions": permissions,
        }
    )

def _generer_numero_adherent():
    annee = timezone.now().year
    prefixe = f"ADH-{annee}-"

    numeros = (
        Adherent.objects
        .filter(numero_adherent__startswith=prefixe)
        .values_list("numero_adherent", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    numero_adherent = f"{prefixe}{prochain:04d}"

    while Adherent.objects.filter(
        numero_adherent=numero_adherent
    ).exists():
        prochain += 1
        numero_adherent = f"{prefixe}{prochain:04d}"

    return numero_adherent

def _generer_numero_personne():
    annee = timezone.now().year
    prefixe = f"PERS-{annee}-"

    numeros = (
        Personne.objects
        .filter(numero_personne__startswith=prefixe)
        .values_list("numero_personne", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    numero_personne = f"{prefixe}{prochain:04d}"

    while Personne.objects.filter(
        numero_personne=numero_personne
    ).exists():
        prochain += 1
        numero_personne = f"{prefixe}{prochain:04d}"

    return numero_personne

def adherent_create(request):
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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un adhérent."
        )
        return redirect("adherents")

    if request.method == "POST":
        form = AdherentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    doublon = (
                        Adherent.objects
                        .filter(
                            statut="ACTIF",
                            id_personne__nom__iexact=form.cleaned_data["nom"].strip(),
                            id_personne__prenom__iexact=form.cleaned_data["prenom"].strip(),
                            id_personne__date_naissance=form.cleaned_data["date_naissance"],
                        )
                        .first()
                    )

                    if doublon:
                        messages.error(
                            request,
                            f"Cet adhérent existe déjà "
                            f"({doublon.numero_adherent})."
                        )
                        return render(
                            request,
                            "core/adherent_form.html",
                            {
                                "form": form,
                                "titre": "Nouvel adhérent",
                            }
                        )

                    personne = Personne.objects.create(
                        numero_personne=_generer_numero_personne(),
                        nom=form.cleaned_data["nom"].strip(),
                        prenom=form.cleaned_data["prenom"].strip(),
                        date_naissance=form.cleaned_data["date_naissance"],
                        sexe=form.cleaned_data["sexe"] or None,
                        adresse=form.cleaned_data["adresse"] or None,
                        telephone=form.cleaned_data["telephone"] or None,
                        email=form.cleaned_data["email"] or None,
                        statut=form.cleaned_data["statut"],
                        date_creation=timezone.now(),
                    )

                    adherent = Adherent.objects.create(
                        id_personne=personne,
                        numero_adherent=_generer_numero_adherent(),
                        statut=form.cleaned_data["statut"],
                        date_adhesion=form.cleaned_data["date_adhesion"],
                        date_creation=timezone.now(),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="CREATION",
                        module="ADHERENTS",
                        table_cible="adherent",
                        id_enregistrement=adherent.id_adherent,
                        nouvelle_valeur=(
                            f"Numéro adhérent : "
                            f"{adherent.numero_adherent}, "
                            f"Statut : {adherent.statut}"
                        ),
                        description=(
                            f"Création de l'adhérent "
                            f"{adherent.numero_adherent}"
                        ),
                    )

                messages.success(
                    request,
                    "Adhérent créé avec succès."
                )

                return redirect("adherents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = AdherentForm()

    return render(
        request,
        "core/adherent_form.html",
        {
            "form": form,
            "titre": "Nouvel adhérent",
        }
    )
def adherent_modifier(request, id_adherent):
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

    if "ADHERENT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un adhérent."
        )
        return redirect("adherents")

    try:
        adherent = (
            Adherent.objects
            .select_related("id_personne")
            .get(id_adherent=id_adherent)
        )
    except Adherent.DoesNotExist:
        messages.error(
            request,
            "Adhérent introuvable."
        )
        return redirect("adherents")

    personne = adherent.id_personne

    if request.method == "POST":
        form = AdherentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    doublon = (
                        Adherent.objects
                        .filter(
                            statut="ACTIF",
                            id_personne__nom__iexact=form.cleaned_data["nom"].strip(),
                            id_personne__prenom__iexact=form.cleaned_data["prenom"].strip(),
                            id_personne__date_naissance=form.cleaned_data["date_naissance"],
                        )
                        .exclude(id_adherent=adherent.id_adherent)
                        .first()
                    )

                    if doublon:
                        messages.error(
                            request,
                            f"Un autre adhérent existe déjà avec ces informations "
                            f"({doublon.numero_adherent})."
                        )
                    else:
                        personne.nom = form.cleaned_data["nom"].strip()
                        personne.prenom = form.cleaned_data["prenom"].strip()
                        personne.date_naissance = (
                            form.cleaned_data["date_naissance"]
                        )
                        personne.sexe = (
                            form.cleaned_data["sexe"] or None
                        )
                        personne.adresse = (
                            form.cleaned_data["adresse"] or None
                        )
                        personne.telephone = (
                            form.cleaned_data["telephone"] or None
                        )
                        personne.email = (
                            form.cleaned_data["email"] or None
                        )
                        personne.statut = form.cleaned_data["statut"]
                        personne.date_modification = timezone.now()
                        personne.save()

                        adherent.statut = form.cleaned_data["statut"]
                        adherent.date_adhesion = (
                            form.cleaned_data["date_adhesion"]
                        )
                        adherent.save()

                        messages.success(
                            request,
                            "Adhérent modifié avec succès."
                        )

                        return redirect("adherents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )
    else:
        form = AdherentForm(
            initial={
                "numero_adherent": adherent.numero_adherent,
                "numero_personne": personne.numero_personne,
                "nom": personne.nom,
                "prenom": personne.prenom,
                "date_naissance": personne.date_naissance,
                "sexe": personne.sexe,
                "adresse": personne.adresse,
                "telephone": personne.telephone,
                "email": personne.email,
                "date_adhesion": adherent.date_adhesion,
                "statut": adherent.statut,
            }
        )

    return render(
        request,
        "core/adherent_form.html",
        {
            "form": form,
            "titre": "Modifier l'adhérent",
        }
    )
def adherent_radier(request, id_adherent):
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

    if "ADHERENT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un adhÃ©rent."
        )
        return redirect("adherents")

    try:
        adherent = Adherent.objects.get(id_adherent=id_adherent)
    except Adherent.DoesNotExist:
        messages.error(
            request,
            "AdhÃ©rent introuvable."
        )
        return redirect("adherents")

    if request.method == "POST":
        try:
            adherent.statut = "RADIE"
            adherent.date_radiation = timezone.now().date()
            adherent.save()
            enregistrer_audit(
                request=request,
                type_action="RADIATION",
                module="ADHERENTS",
                table_cible="adherent",
                id_enregistrement=adherent.id_adherent,
                ancienne_valeur="Statut : ACTIF",
                nouvelle_valeur="Statut : RADIE",
                description=f"Radiation de l'adhérent {adherent.numero_adherent}",
            )

            messages.success(
                request,
                "AdhÃ©rent radiÃ© avec succÃ¨s."
            )

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la radiation : {e}"
            )

        return redirect("adherents")

    return render(
        request,
        "core/adherent_radier.html",
        {
            "adherent": adherent,
        }
    )
def souscripteurs(request):
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

    if "SOUSCRIPTEUR_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les souscripteurs."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    souscripteurs = (
        Souscripteur.objects
        .all()
        .order_by("raison_sociale")
    )

    if recherche:
        from django.db.models import Q

        souscripteurs = souscripteurs.filter(
            Q(code_souscripteur__icontains=recherche)
            | Q(raison_sociale__icontains=recherche)
            | Q(nif__icontains=recherche)
            | Q(telephone__icontains=recherche)
            | Q(email__icontains=recherche)
        )

    if statut:
        souscripteurs = souscripteurs.filter(
            statut=statut
        )

    return render(
        request,
        "core/souscripteurs.html",
        {
            "souscripteurs": souscripteurs,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )
def _generer_code_souscripteur():
    annee = timezone.now().year
    prefixe = f"SOUS-{annee}-"

    numeros = (
        Souscripteur.objects
        .filter(code_souscripteur__startswith=prefixe)
        .values_list("code_souscripteur", flat=True)
    )

    valeurs = []

    for code in numeros:
        try:
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code_souscripteur = f"{prefixe}{prochain:04d}"

    while Souscripteur.objects.filter(
        code_souscripteur=code_souscripteur
    ).exists():
        prochain += 1
        code_souscripteur = f"{prefixe}{prochain:04d}"

    return code_souscripteur

def souscripteur_create(request):
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

    if "SOUSCRIPTEUR_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er un souscripteur."
        )
        return redirect("souscripteurs")

    if request.method == "POST":
        form = SouscripteurForm(request.POST)

        if form.is_valid():
            try:
                Souscripteur.objects.create(
                    code_souscripteur=_generer_code_souscripteur(),
                    raison_sociale=form.cleaned_data["raison_sociale"],
                    type_souscripteur=form.cleaned_data["type_souscripteur"],
                    nif=form.cleaned_data["nif"] or None,
                    registre_commerce=form.cleaned_data["registre_commerce"] or None,
                    adresse=form.cleaned_data["adresse"] or None,
                    telephone=form.cleaned_data["telephone"] or None,
                    email=form.cleaned_data["email"] or None,
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                messages.success(
                    request,
                    "Souscripteur crÃ©Ã© avec succÃ¨s."
                )

                return redirect("souscripteurs")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = SouscripteurForm()

    return render(
        request,
        "core/souscripteur_form.html",
        {
            "form": form,
            "titre": "Nouveau souscripteur",
        }
    )
def souscripteur_modifier(request, id_souscripteur):
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

    if "SOUSCRIPTEUR_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un souscripteur."
        )
        return redirect("souscripteurs")

    try:
        souscripteur = Souscripteur.objects.get(
            id_souscripteur=id_souscripteur
        )
    except Souscripteur.DoesNotExist:
        messages.error(
            request,
            "Souscripteur introuvable."
        )
        return redirect("souscripteurs")

    if request.method == "POST":
        form = SouscripteurForm(request.POST)

        if form.is_valid():
            try:
                
                souscripteur.raison_sociale = (
                    form.cleaned_data["raison_sociale"]
                )
                souscripteur.type_souscripteur = (
                    form.cleaned_data["type_souscripteur"]
                )
                souscripteur.nif = (
                    form.cleaned_data["nif"] or None
                )
                souscripteur.registre_commerce = (
                    form.cleaned_data["registre_commerce"] or None
                )
                souscripteur.adresse = (
                    form.cleaned_data["adresse"] or None
                )
                souscripteur.telephone = (
                    form.cleaned_data["telephone"] or None
                )
                souscripteur.email = (
                    form.cleaned_data["email"] or None
                )
                souscripteur.statut = (
                    form.cleaned_data["statut"]
                )

                souscripteur.save()

                messages.success(
                    request,
                    "Souscripteur modifiÃ© avec succÃ¨s."
                )

                return redirect("souscripteurs")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = SouscripteurForm(
            initial={
                "code_souscripteur": souscripteur.code_souscripteur,
                "raison_sociale": souscripteur.raison_sociale,
                "type_souscripteur": souscripteur.type_souscripteur,
                "nif": souscripteur.nif,
                "registre_commerce": souscripteur.registre_commerce,
                "adresse": souscripteur.adresse,
                "telephone": souscripteur.telephone,
                "email": souscripteur.email,
                "statut": souscripteur.statut,
            }
        )

    return render(
        request,
        "core/souscripteur_form.html",
        {
            "form": form,
            "titre": "Modifier le souscripteur",
        }
    )


def souscripteur_radier(request, id_souscripteur):
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

    if "SOUSCRIPTEUR_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un souscripteur."
        )
        return redirect("souscripteurs")

    try:
        souscripteur = Souscripteur.objects.get(
            id_souscripteur=id_souscripteur
        )
    except Souscripteur.DoesNotExist:
        messages.error(
            request,
            "Souscripteur introuvable."
        )
        return redirect("souscripteurs")

    if request.method == "POST":
        souscripteur.statut = "RADIE"
        souscripteur.save()

        messages.success(
            request,
            "Souscripteur radiÃ© avec succÃ¨s."
        )

    return redirect("souscripteurs")
def contrats(request):
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

    if "CONTRAT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les contrats."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    contrats = (
        Contrat.objects
        .select_related("id_souscripteur")
        .all()
        .order_by("-id_contrat")
    )

    if recherche:
        from django.db.models import Q

        contrats = contrats.filter(
            Q(numero_contrat__icontains=recherche)
            | Q(id_souscripteur__code_souscripteur__icontains=recherche)
            | Q(id_souscripteur__raison_sociale__icontains=recherche)
            | Q(type_contrat__icontains=recherche)
        )

    if statut:
        contrats = contrats.filter(
            statut=statut
        )

    return render(
        request,
        "core/contrats.html",
        {
            "contrats": contrats,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )

def contrat_detail(request, id_contrat):
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

    if "CONTRAT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter ce contrat."
        )
        return redirect("contrats")

    try:
        contrat = (
            Contrat.objects
            .select_related("id_souscripteur")
            .get(id_contrat=id_contrat)
        )
    except Contrat.DoesNotExist:
        messages.error(
            request,
            "Contrat introuvable."
        )
        return redirect("contrats")

    garanties = (
        ContratGarantie.objects
        .select_related("id_garantie")
        .filter(id_contrat=contrat)
        .order_by("id_contrat_garantie")
    )
    adhesions = (
    Adhesion.objects
    .select_related("id_adherent", "id_adherent__id_personne")
    .filter(id_contrat=contrat)
    .order_by("id_adhesion")
)
    demandes_tp = (
        DemandeTp.objects
        .select_related(
            "id_personne_beneficiaire",
            "id_prestataire",
        )
        .filter(id_contrat=contrat)
        .order_by("-id_demande")
    )

    return render(
        request,
        "core/contrat_detail.html",
        {
            "contrat": contrat,
            "garanties": garanties,
            "adhesions": adhesions,
            "demandes_tp": demandes_tp,
            "permissions": permissions,
        }
    )
def contrat_garantie_create(request, id_contrat):
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
    if "CONTRAT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter une garantie Ã  un contrat."
        )
        return redirect("contrats")

    contrat = (
        Contrat.objects
        .filter(
            id_contrat=id_contrat,
            statut="ACTIF"
        )
        .select_related("id_souscripteur")
        .first()
    )

    if not contrat:
        messages.error(
            request,
            "Contrat invalide ou introuvable."
        )
        return redirect("contrats")

    garanties = (
        Garantie.objects
        .filter(statut="ACTIF")
        .order_by("code_garantie")
    )

    if request.method == "POST":
        form = ContratGarantieForm(request.POST)

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        if form.is_valid():
            try:
                garantie = Garantie.objects.get(
                    id_garantie=form.cleaned_data["id_garantie"],
                    statut="ACTIF"
                )

                ContratGarantie.objects.create(
                    id_contrat=contrat,
                    id_garantie=garantie,
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Garantie ajoutÃ©e au contrat avec succÃ¨s."
                )

                return redirect(
                    "contrat_detail",
                    id_contrat=contrat.id_contrat
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = ContratGarantieForm()

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

    return render(
        request,
        "core/contrat_garantie_form.html",
        {
            "form": form,
            "contrat": contrat,
            "permissions": permissions,
        }
    )

def _generer_numero_contrat():
    annee = timezone.now().year
    prefixe = f"CTR-{annee}-"

    numeros = (
        Contrat.objects
        .filter(numero_contrat__startswith=prefixe)
        .values_list("numero_contrat", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    numero_contrat = f"{prefixe}{prochain:04d}"

    while Contrat.objects.filter(
        numero_contrat=numero_contrat
    ).exists():
        prochain += 1
        numero_contrat = f"{prefixe}{prochain:04d}"

    return numero_contrat

def contrat_create(request):
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

    if "CONTRAT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er un contrat."
        )
        return redirect("contrats")

    souscripteurs = Souscripteur.objects.filter(
        statut="ACTIF"
    ).order_by("raison_sociale")

    if request.method == "POST":
        form = ContratForm(request.POST)

        form.fields["id_souscripteur"].choices = [
            (
                str(s.id_souscripteur),
                f"{s.code_souscripteur} - {s.raison_sociale}"
            )
            for s in souscripteurs
        ]

        if form.is_valid():
            try:
                souscripteur = Souscripteur.objects.get(
                    id_souscripteur=form.cleaned_data["id_souscripteur"],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.create(
                    id_souscripteur=souscripteur,
                    numero_contrat=_generer_numero_contrat(),
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    type_contrat=form.cleaned_data["type_contrat"],
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                    objet=form.cleaned_data["objet"] or None,
                    date_signature=form.cleaned_data["date_signature"],
                    date_modification=None,
                )

                # Lier automatiquement toutes les garanties actives à ce contrat
                garanties_actives = Garantie.objects.filter(statut="ACTIF")

                for garantie in garanties_actives:
                    ContratGarantie.objects.get_or_create(
                        id_contrat=contrat,
                        id_garantie=garantie,
                        defaults={
                            "date_debut": contrat.date_debut,
                            "date_fin": contrat.date_fin,
                            "statut": "ACTIF",
                        }
                    )

                messages.success(
                    request,
                    f"Contrat créé avec succès. "
                    f"{garanties_actives.count()} garanties liées automatiquement."
                )

                return redirect("contrats")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = ContratForm()

        form.fields["id_souscripteur"].choices = [
            (
                str(s.id_souscripteur),
                f"{s.code_souscripteur} - {s.raison_sociale}"
            )
            for s in souscripteurs
        ]

    return render(
        request,
        "core/contrat_form.html",
        {
            "form": form,
            "titre": "Nouveau contrat",
        }
    )

def contrat_modifier(request, id_contrat):
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
    if "CONTRAT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un contrat."
        )
        return redirect("contrats")

    try:
        contrat = Contrat.objects.get(
            id_contrat=id_contrat
        )
    except Contrat.DoesNotExist:
        messages.error(
            request,
            "Contrat introuvable."
        )
        return redirect("contrats")

    souscripteurs = Souscripteur.objects.filter(
        statut="ACTIF"
    ).order_by("raison_sociale")

    if request.method == "POST":
        form = ContratForm(request.POST)

        form.fields["id_souscripteur"].choices = [
            (
                str(s.id_souscripteur),
                f"{s.code_souscripteur} - {s.raison_sociale}"
            )
            for s in souscripteurs
        ]

        if form.is_valid():
            try:
                souscripteur = Souscripteur.objects.get(
                    id_souscripteur=form.cleaned_data["id_souscripteur"],
                    statut="ACTIF"
                )

                contrat.id_souscripteur = souscripteur
                contrat.date_debut = form.cleaned_data["date_debut"]
                contrat.date_fin = form.cleaned_data["date_fin"]
                contrat.type_contrat = form.cleaned_data["type_contrat"]
                contrat.statut = form.cleaned_data["statut"]
                contrat.objet = form.cleaned_data["objet"] or None
                contrat.date_signature = form.cleaned_data["date_signature"]
                contrat.date_modification = timezone.now()

                contrat.save()

                messages.success(
                    request,
                    "Contrat modifiÃ© avec succÃ¨s."
                )

                return redirect("contrats")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = ContratForm(
            initial={
                "numero_contrat": contrat.numero_contrat,
                "id_souscripteur": str(
                    contrat.id_souscripteur_id
                ),
                "date_debut": contrat.date_debut,
                "date_fin": contrat.date_fin,
                "type_contrat": contrat.type_contrat,
                "statut": contrat.statut,
                "objet": contrat.objet,
                "date_signature": contrat.date_signature,
            }
        )

        form.fields["id_souscripteur"].choices = [
            (
                str(s.id_souscripteur),
                f"{s.code_souscripteur} - {s.raison_sociale}"
            )
            for s in souscripteurs
        ]

    return render(
        request,
        "core/contrat_form.html",
        {
            "form": form,
            "titre": "Modifier le contrat",
        }
    )

def contrat_radier(request, id_contrat):
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

    if "CONTRAT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un contrat."
        )
        return redirect("contrats")

    try:
        contrat = Contrat.objects.get(
            id_contrat=id_contrat
        )
    except Contrat.DoesNotExist:
        messages.error(
            request,
            "Contrat introuvable."
        )
        return redirect("contrats")

    if request.method == "POST":
        contrat.statut = "RADIE"
        contrat.date_modification = timezone.now()
        contrat.save()

        messages.success(
            request,
            "Contrat radiÃ© avec succÃ¨s."
        )

    return redirect("contrats")


def garanties(request):
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

    if "GARANTIE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les garanties."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    garanties = (
        Garantie.objects
        .all()
        .order_by("-id_garantie")
    )

    if recherche:
        from django.db.models import Q

        garanties = garanties.filter(
            Q(code_garantie__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        garanties = garanties.filter(
            statut=statut
        )

    return render(
        request,
        "core/garanties.html",
        {
            "garanties": garanties,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )

def garantie_detail(request, id_garantie):
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

    if "GARANTIE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter cette garantie."
        )
        return redirect("garanties")

    try:
        garantie = Garantie.objects.get(
            id_garantie=id_garantie
        )
    except Garantie.DoesNotExist:
        messages.error(
            request,
            "Garantie introuvable."
        )
        return redirect("garanties")

    actes = (
        GarantieActe.objects
        .select_related("id_acte")
        .filter(id_garantie=garantie)
        .order_by("id_garantie_acte")
    )

    return render(
        request,
        "core/garantie_detail.html",
        {
            "garantie": garantie,
            "actes": actes,
            "permissions": permissions,
        }
    )
def _generer_code_garantie():
    annee = timezone.now().year
    prefixe = f"GAR-{annee}-"

    codes = (
        Garantie.objects
        .filter(code_garantie__startswith=prefixe)
        .values_list("code_garantie", flat=True)
    )

    valeurs = []

    for code in codes:
        try:
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code_garantie = f"{prefixe}{prochain:04d}"

    while Garantie.objects.filter(
        code_garantie=code_garantie
    ).exists():
        prochain += 1
        code_garantie = f"{prefixe}{prochain:04d}"

    return code_garantie

def garantie_create(request):
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

    if "GARANTIE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er une garantie."
        )
        return redirect("garanties")

    if request.method == "POST":
        form = GarantieForm(request.POST)

        if form.is_valid():
            try:
                Garantie.objects.create(
                    code_garantie=_generer_code_garantie(),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"] or None,
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Garantie crÃ©Ã©e avec succÃ¨s."
                )

                return redirect("garanties")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = GarantieForm()

    return render(
        request,
        "core/garantie_form.html",
        {
            "form": form,
            "titre": "Nouvelle garantie",
        }
    )
def garantie_modifier(request, id_garantie):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    try:
        garantie = Garantie.objects.get(
            id_garantie=id_garantie
        )
    except Garantie.DoesNotExist:
        messages.error(
            request,
            "Garantie introuvable."
        )
        return redirect("garanties")

    if request.method == "POST":
        form = GarantieForm(request.POST)

        if form.is_valid():
            try:
                
                garantie.libelle = (
                    form.cleaned_data["libelle"]
                )
                garantie.description = (
                    form.cleaned_data["description"] or None
                )
                garantie.statut = (
                    form.cleaned_data["statut"]
                )

                garantie.save()

                messages.success(
                    request,
                    "Garantie modifiÃ©e avec succÃ¨s."
                )

                return redirect("garanties")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = GarantieForm(
            initial={
                "code_garantie": garantie.code_garantie,
                "libelle": garantie.libelle,
                "description": garantie.description,
                "statut": garantie.statut,
            }
        )

    return render(
        request,
        "core/garantie_form.html",
        {
            "form": form,
            "titre": "Modifier la garantie",
        }
    )

def garantie_radier(request, id_garantie):
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

    if "GARANTIE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une garantie."
        )
        return redirect("garanties")

    try:
        garantie = Garantie.objects.get(
            id_garantie=id_garantie
        )
    except Garantie.DoesNotExist:
        messages.error(
            request,
            "Garantie introuvable."
        )
        return redirect("garanties")

    if request.method == "POST":
        garantie.statut = "RADIE"
        garantie.save()

        messages.success(
            request,
            "Garantie radiÃ©e avec succÃ¨s."
        )

    return redirect("garanties")

def actes(request):
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

    if "ACTE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les actes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    actes = (
        Acte.objects
        .select_related("id_type_prestation")
        .all()
        .order_by("-id_acte")
    )

    if recherche:
        from django.db.models import Q

        actes = actes.filter(
            Q(code_acte__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        actes = actes.filter(statut=statut)

    return render(
        request,
        "core/actes.html",
        {
            "actes": actes,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )

def acte_detail(request, id_acte):
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

    if "ACTE_VIEW" not in permissions:
        return redirect("accueil")

    acte = get_object_or_404(
        Acte.objects.select_related("id_type_prestation"),
        id_acte=id_acte
    )

    sous_actes = (
        SousActe.objects
        .filter(id_acte=acte)
        .order_by("libelle")
    )

    return render(
        request,
        "core/acte_detail.html",
        {
            "acte": acte,
            "sous_actes": sous_actes,
            "permissions": permissions,
        }
    )

def sous_actes(request):
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

    if "ACTE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les sous-actes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()
    id_acte = request.GET.get("id_acte", "").strip()

    sous_actes = (
        SousActe.objects
        .select_related("id_acte")
        .all()
        .order_by("-id_sous_acte")
    )

    if recherche:
        sous_actes = sous_actes.filter(
            Q(code_sous_acte__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        sous_actes = sous_actes.filter(statut=statut)

    if id_acte:
        sous_actes = sous_actes.filter(id_acte_id=id_acte)

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    return render(
        request,
        "core/sous_actes.html",
        {
            "sous_actes": sous_actes,
            "actes": actes,
            "recherche": recherche,
            "statut": statut,
            "id_acte": id_acte,
            "permissions": permissions,
        }
    )

def _generer_code_acte():
    annee = timezone.now().year
    prefixe = f"ACT-{annee}-"

    codes = (
        Acte.objects
        .filter(code_acte__startswith=prefixe)
        .values_list("code_acte", flat=True)
    )

    valeurs = []

    for code in codes:
        try:
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code_acte = f"{prefixe}{prochain:04d}"

    while Acte.objects.filter(
        code_acte=code_acte
    ).exists():
        prochain += 1
        code_acte = f"{prefixe}{prochain:04d}"

    return code_acte

def _generer_code_sous_acte():
    annee = timezone.now().year
    prefixe = f"SA-{annee}-"

    codes = (
        SousActe.objects
        .filter(code_sous_acte__startswith=prefixe)
        .values_list("code_sous_acte", flat=True)
    )

    valeurs = []

    for code in codes:
        try:
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code_sous_acte = f"{prefixe}{prochain:04d}"

    while SousActe.objects.filter(
        code_sous_acte=code_sous_acte
    ).exists():
        prochain += 1
        code_sous_acte = f"{prefixe}{prochain:04d}"

    return code_sous_acte

def sous_acte_create(request):
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

    if "ACTE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un sous-acte."
        )
        return redirect("sous_actes")

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    if request.method == "POST":
        form = SousActeForm(request.POST)

        form.fields["id_acte"].choices = [
            (
                acte.id_acte,
                f"{acte.code_acte} - {acte.libelle}"
            )
            for acte in actes
        ]

        if form.is_valid():
            id_acte = form.cleaned_data["id_acte"]
            code_sous_acte = _generer_code_sous_acte()

            sous_acte = SousActe.objects.create(
                id_acte_id=id_acte,
                code_sous_acte=code_sous_acte,
                libelle=form.cleaned_data["libelle"],
                description=form.cleaned_data["description"],
                unite=form.cleaned_data["unite"],
                statut="ACTIF",
            )

            messages.success(
                request,
                f"Sous-acte {sous_acte.code_sous_acte} créé avec succès."
            )

            return redirect("sous_actes")

    else:
        id_acte_preselectionne = request.GET.get("id_acte", "").strip()

        form = SousActeForm(
            initial={
                "id_acte": id_acte_preselectionne
            }
        )

    form.fields["id_acte"].choices = [
        (
            acte.id_acte,
            f"{acte.code_acte} - {acte.libelle}"
        )
        for acte in actes
    ]

    return render(
        request,
        "core/sous_acte_form.html",
        {
            "form": form,
            "titre": "Nouveau sous-acte",
            "permissions": permissions,
        }
    )

def sous_acte_modifier(request, id_sous_acte):
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

    if "ACTE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un sous-acte."
        )
        return redirect("sous_actes")

    try:
        sous_acte = SousActe.objects.get(
            id_sous_acte=id_sous_acte
        )
    except SousActe.DoesNotExist:
        messages.error(
            request,
            "Sous-acte introuvable."
        )
        return redirect("sous_actes")

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )
    id_acte_preselectionne = request.GET.get("id_acte", "").strip()
    if request.method == "POST":
          form = SousActeForm(request.POST)

          form.fields["id_acte"].choices = [
            (
                acte.id_acte,
                f"{acte.code_acte} - {acte.libelle}"
            )
            for acte in actes
        ]

    if form.is_valid():
            id_acte = form.cleaned_data["id_acte"]
            code_sous_acte = _generer_code_sous_acte()

            sous_acte = SousActe.objects.create(
                id_acte_id=id_acte,
                code_sous_acte=code_sous_acte,
                libelle=form.cleaned_data["libelle"],
                description=form.cleaned_data["description"],
                unite=form.cleaned_data["unite"],
                statut="ACTIF",
            )

            messages.success(
                request,
                f"Sous-acte {sous_acte.code_sous_acte} créé avec succès."
            )

            return redirect("sous_actes")

    else:
        id_acte_preselectionne = request.GET.get("id_acte", "").strip()

        form = SousActeForm(
            initial={
                "id_acte": id_acte_preselectionne
            }
        )

        form.fields["id_acte"].choices = [
            (
                acte.id_acte,
                f"{acte.code_acte} - {acte.libelle}"
            )
            for acte in actes
        ]

    return render(
        request,
        "core/sous_acte_form.html",
        {
            "form": form,
            "titre": "Modifier le sous-acte",
            "permissions": permissions,
        }
    )

def sous_acte_radier(request, id_sous_acte):
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

    if "ACTE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un sous-acte."
        )
        return redirect("sous_actes")

    try:
        sous_acte = SousActe.objects.get(
            id_sous_acte=id_sous_acte
        )
    except SousActe.DoesNotExist:
        messages.error(
            request,
            "Sous-acte introuvable."
        )
        return redirect("sous_actes")

    if request.method == "POST":
        sous_acte.statut = "INACTIF"
        sous_acte.save()

        messages.success(
            request,
            "Sous-acte radié avec succès."
        )

    return redirect("sous_actes")

def tarif_sous_acte_create(request):
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

    if "ACTE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un tarif de sous-acte."
        )
        return redirect("tarifs_sous_actes")

    sous_actes = (
        SousActe.objects
        .filter(statut="ACTIF")
        .select_related("id_acte")
        .order_by("libelle")
    )

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    if request.method == "POST":

        form = TarifSousActeForm(request.POST)

        form.fields["id_sous_acte"].choices = [
            (
                sous_acte.id_sous_acte,
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        form.fields["id_prestataire"].choices = [
            (
                prestataire.id_prestataire,
                f"{prestataire.code_prestataire} - {prestataire.raison_sociale}"
            )
            for prestataire in prestataires
        ]
        

        if form.is_valid():

            id_sous_acte = form.cleaned_data["id_sous_acte"]
            id_prestataire = form.cleaned_data["id_prestataire"]
            montant = form.cleaned_data["montant"]
            date_debut = form.cleaned_data["date_debut"]
            date_fin = form.cleaned_data["date_fin"]

            if date_fin and date_fin < date_debut:
                form.add_error(
                    "date_fin",
                    "La date de fin doit être supérieure ou égale à la date de début."
                )
            else:

                tarifs_existants = TarifSousActe.objects.filter(
                    id_sous_acte_id=id_sous_acte,
                    id_prestataire_id=id_prestataire
                )

                # Recherche d'une période qui chevauche la nouvelle période.
                if date_fin:
                    tarifs_existants = tarifs_existants.filter(
                        date_debut__lte=date_fin
                    ).filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_debut)
                    )
                else:
                    tarifs_existants = tarifs_existants.filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_debut)
                    )

                if tarifs_existants.exists():

                    messages.error(
                        request,
                        "Impossible de créer ce tarif : "
                        "une autre période tarifaire existe déjà "
                        "pour ce sous-acte et ce prestataire."
                    )

                else:

                    tarif = TarifSousActe.objects.create(
                        id_sous_acte_id=id_sous_acte,
                        id_prestataire_id=id_prestataire,
                        montant=montant,
                        date_debut=date_debut,
                        date_fin=date_fin,
                        statut="ACTIF",
                    )

                    messages.success(
                        request,
                        f"Tarif {tarif.montant} créé avec succès."
                    )

                    return redirect("tarifs_sous_actes")
            

    else:

        form = TarifSousActeForm()

        form.fields["id_sous_acte"].choices = [
            (
                sous_acte.id_sous_acte,
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        form.fields["id_prestataire"].choices = [
            (
                prestataire.id_prestataire,
                f"{prestataire.code_prestataire} - {prestataire.raison_sociale}"
            )
            for prestataire in prestataires
        ]

    return render(
        request,
        "core/tarif_sous_acte_form.html",
        {
            "form": form,
            "titre": "Nouveau tarif sous-acte",
            "permissions": permissions,
        }
    )

def tarif_sous_acte_modifier(request, id_tarif_sous_acte):
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

    if "ACTE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un tarif de sous-acte."
        )
        return redirect("tarifs_sous_actes")

    try:
        tarif = TarifSousActe.objects.get(
            id_tarif_sous_acte=id_tarif_sous_acte
        )
    except TarifSousActe.DoesNotExist:
        messages.error(
            request,
            "Tarif sous-acte introuvable."
        )
        return redirect("tarifs_sous_actes")

    sous_actes = (
        SousActe.objects
        .filter(statut="ACTIF")
        .select_related("id_acte")
        .order_by("libelle")
    )

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    if request.method == "POST":

        form = TarifSousActeForm(request.POST)

        form.fields["id_sous_acte"].choices = [
            (
                sous_acte.id_sous_acte,
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        form.fields["id_prestataire"].choices = [
            (
                prestataire.id_prestataire,
                f"{prestataire.code_prestataire} - {prestataire.raison_sociale}"
            )
            for prestataire in prestataires
        ]

        if form.is_valid():

            id_sous_acte = form.cleaned_data["id_sous_acte"]
            id_prestataire = form.cleaned_data["id_prestataire"]
            montant = form.cleaned_data["montant"]
            date_debut = form.cleaned_data["date_debut"]
            date_fin = form.cleaned_data["date_fin"]

            if date_fin and date_fin < date_debut:

                form.add_error(
                    "date_fin",
                    "La date de fin doit être supérieure ou égale à la date de début."
                )

            else:

                tarifs_existants = (
                    TarifSousActe.objects
                    .filter(
                        id_sous_acte_id=id_sous_acte,
                        id_prestataire_id=id_prestataire
                    )
                    .exclude(
                        id_tarif_sous_acte=id_tarif_sous_acte
                    )
                )

                if date_fin:

                    tarifs_existants = tarifs_existants.filter(
                        date_debut__lte=date_fin
                    ).filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_debut)
                    )

                else:

                    tarifs_existants = tarifs_existants.filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_debut)
                    )

                if tarifs_existants.exists():

                    messages.error(
                        request,
                        "Impossible de modifier ce tarif : "
                        "une autre période tarifaire existe déjà "
                        "pour ce sous-acte et ce prestataire."
                    )

                else:

                    tarif.id_sous_acte_id = id_sous_acte
                    tarif.id_prestataire_id = id_prestataire
                    tarif.montant = montant
                    tarif.date_debut = date_debut
                    tarif.date_fin = date_fin

                    tarif.save()

                    messages.success(
                        request,
                        "Tarif sous-acte modifié avec succès."
                    )

                    return redirect("tarifs_sous_actes")

    else:

        form = TarifSousActeForm(
            initial={
                "id_sous_acte": tarif.id_sous_acte_id,
                "id_prestataire": tarif.id_prestataire_id,
                "montant": tarif.montant,
                "date_debut": tarif.date_debut,
                "date_fin": tarif.date_fin,
                "statut": tarif.statut,
            }
        )

        form.fields["id_sous_acte"].choices = [
            (
                sous_acte.id_sous_acte,
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        form.fields["id_prestataire"].choices = [
            (
                prestataire.id_prestataire,
                f"{prestataire.code_prestataire} - {prestataire.raison_sociale}"
            )
            for prestataire in prestataires
        ]

    return render(
        request,
        "core/tarif_sous_acte_form.html",
        {
            "form": form,
            "titre": "Modifier le tarif sous-acte",
            "permissions": permissions,
        }
    )

def tarif_sous_acte_radier(request, id_tarif_sous_acte):
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

    if "ACTE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un tarif de sous-acte."
        )
        return redirect("tarifs_sous_actes")

    try:
        tarif = TarifSousActe.objects.get(
            id_tarif_sous_acte=id_tarif_sous_acte
        )
    except TarifSousActe.DoesNotExist:
        messages.error(
            request,
            "Tarif sous-acte introuvable."
        )
        return redirect("tarifs_sous_actes")

    if request.method == "POST":
        tarif.statut = "INACTIF"
        tarif.save()

        messages.success(
            request,
            "Tarif sous-acte radié avec succès."
        )

    return redirect("tarifs_sous_actes")

def tarifs_sous_actes(request):
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

    if "ACTE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les tarifs des sous-actes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    id_sous_acte = request.GET.get("id_sous_acte", "").strip()
    id_prestataire = request.GET.get("id_prestataire", "").strip()
    statut = request.GET.get("statut", "").strip()

    tarifs = (
        TarifSousActe.objects
        .select_related(
            "id_sous_acte",
            "id_sous_acte__id_acte",
            "id_prestataire"
        )
        .all()
        .order_by("-id_tarif_sous_acte")
    )

    if recherche:
        tarifs = tarifs.filter(
            Q(id_sous_acte__code_sous_acte__icontains=recherche)
            | Q(id_sous_acte__libelle__icontains=recherche)
            | Q(id_sous_acte__id_acte__code_acte__icontains=recherche)
            | Q(id_sous_acte__id_acte__libelle__icontains=recherche)
            | Q(id_prestataire__code_prestataire__icontains=recherche)
            | Q(id_prestataire__raison_sociale__icontains=recherche)
        )

    if id_sous_acte:
        tarifs = tarifs.filter(
            id_sous_acte_id=id_sous_acte
        )

    if id_prestataire:
        tarifs = tarifs.filter(
            id_prestataire_id=id_prestataire
        )

    if statut:
        tarifs = tarifs.filter(
            statut=statut
        )

    sous_actes = (
        SousActe.objects
        .filter(statut="ACTIF")
        .select_related("id_acte")
        .order_by("libelle")
    )

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    return render(
        request,
        "core/tarifs_sous_actes.html",
        {
            "tarifs": tarifs,
            "sous_actes": sous_actes,
            "prestataires": prestataires,
            "recherche": recherche,
            "id_sous_acte": id_sous_acte,
            "id_prestataire": id_prestataire,
            "statut": statut,
            "permissions": permissions,
        }
    )

def acte_create(request):
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

    if "ACTE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un acte."
        )
        return redirect("actes")

    types_prestation = (
        TypePrestation.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    if request.method == "POST":
        form = ActeForm(request.POST)

        form.fields["id_type_prestation"].choices = [
            (
                str(t.id_type_prestation),
                t.libelle
            )
            for t in types_prestation
        ]

        if form.is_valid():
            try:
                type_prestation = TypePrestation.objects.get(
                    id_type_prestation=form.cleaned_data["id_type_prestation"],
                    statut="ACTIF"
                )

                Acte.objects.create(
                    id_type_prestation=type_prestation,
                    code_acte=_generer_code_acte(),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"] or None,
                    unite=form.cleaned_data["unite"] or None,
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Acte créé avec succès."
                )

                return redirect("actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = ActeForm()

        form.fields["id_type_prestation"].choices = [
            (
                str(t.id_type_prestation),
                t.libelle
            )
            for t in types_prestation
        ]

    return render(
        request,
        "core/acte_form.html",
        {
            "form": form,
            "titre": "Nouvel acte",
        }
    )
def acte_modifier(request, id_acte):
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

    if "ACTE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un acte."
        )
        return redirect("actes")

    try:
        acte = Acte.objects.get(id_acte=id_acte)
    except Acte.DoesNotExist:
        messages.error(
            request,
            "Acte introuvable."
        )
        return redirect("actes")

    if request.method == "POST":
        form = ActeForm(request.POST)

        if form.is_valid():
            try:
                acte.id_type_prestation_id = form.cleaned_data["id_type_prestation"]
                acte.libelle = form.cleaned_data["libelle"]
                acte.description = form.cleaned_data["description"] or None
                acte.unite = form.cleaned_data["unite"] or None
                acte.statut = form.cleaned_data["statut"]

                acte.save()

                messages.success(
                    request,
                    "Acte modifié avec succès."
                )
                return redirect("actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = ActeForm(
            initial={
                "id_type_prestation": acte.id_type_prestation_id,
                "code_acte": acte.code_acte,
                "libelle": acte.libelle,
                "description": acte.description,
                "unite": acte.unite,
                "statut": acte.statut,
            }
       
            )
        types_prestation = (
            TypePrestation.objects
            .filter(statut="ACTIF")
            .order_by("libelle")
        )

        form.fields["id_type_prestation"].choices = [
    (
        str(t.id_type_prestation),
        t.libelle
    )
    for t in types_prestation
]
    return render(
        request,
        "core/acte_form.html",
        {
            "form": form,
            "titre": "Modifier un acte",
        }
    )
def acte_radier(request, id_acte):
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

    if "ACTE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un acte."
        )
        return redirect("actes")

    try:
        acte = Acte.objects.get(id_acte=id_acte)
    except Acte.DoesNotExist:
        messages.error(
            request,
            "Acte introuvable."
        )
        return redirect("actes")

    if request.method == "POST":
        acte.statut = "INACTIF"
        acte.save()

        messages.success(
            request,
            "Acte radié avec succès."
        )

    return redirect("actes")

def garantie_actes(request):
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

    if "GARANTIE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les associations garantie-acte."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    id_garantie = request.GET.get("id_garantie", "").strip()

    garantie_actes = (
        GarantieActe.objects
        .select_related("id_garantie", "id_acte", "id_acte__id_type_prestation")
        .all()
        .order_by("-id_garantie_acte")
    )

    if recherche:
        from django.db.models import Q

        garantie_actes = garantie_actes.filter(
            Q(id_garantie__code_garantie__icontains=recherche)
            | Q(id_garantie__libelle__icontains=recherche)
            | Q(id_acte__code_acte__icontains=recherche)
            | Q(id_acte__libelle__icontains=recherche)
        )

    if id_garantie:
        garantie_actes = garantie_actes.filter(
            id_garantie=id_garantie
        )

    garanties = (
        Garantie.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    return render(
        request,
        "core/garantie_actes.html",
        {
            "garantie_actes": garantie_actes,
            "garanties": garanties,
            "recherche": recherche,
            "id_garantie": id_garantie,
            "permissions": permissions,
        }
    )
def garantie_acte_create(request):
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

    if "GARANTIE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'associer un acte Ã  une garantie."
        )
        return redirect("garantie_actes")

    garanties = (
        Garantie.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )
    id_acte_preselectionne = request.GET.get("id_acte", "").strip()
    id_garantie_preselectionne = request.GET.get(
        "id_garantie",
        ""
    ).strip()

    garantie_preselectionnee = None

    if id_garantie_preselectionne:
        garantie_preselectionnee = (
            Garantie.objects
            .filter(
                id_garantie=id_garantie_preselectionne,
                statut="ACTIF"
            )
            .first()
        )

    if request.method == "POST":
        form = GarantieActeForm(request.POST)

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (
                str(a.id_acte),
                f"{a.code_acte} - {a.libelle}"
            )
            for a in actes
        ]

        if form.is_valid():
            try:
                garantie = Garantie.objects.get(
                    id_garantie=form.cleaned_data["id_garantie"],
                    statut="ACTIF"
                )

                acte = Acte.objects.get(
                    id_acte=form.cleaned_data["id_acte"],
                    statut="ACTIF"
                )

                GarantieActe.objects.create(
                    id_garantie=garantie,
                    id_acte=acte,
                    taux_prise_en_charge=form.cleaned_data[
                        "taux_prise_en_charge"
                    ],
                    franchise=form.cleaned_data["franchise"],
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Association garantie-acte crÃ©Ã©e avec succÃ¨s."
                )

                return redirect("garantie_actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = GarantieActeForm()

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (
                str(a.id_acte),
                f"{a.code_acte} - {a.libelle}"
            )
            for a in actes
        ]
        if garantie_preselectionnee:
            form.initial["id_garantie"] = (
                str(garantie_preselectionnee.id_garantie)
            )

    return render(
        request,
        "core/garantie_acte_form.html",
        {
            "form": form,
            "titre": "Associer un acte Ã  une garantie",
            "garantie_preselectionnee": garantie_preselectionnee,
        }
    )

def garantie_acte_modifier(request, id_garantie_acte):
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

    if "GARANTIE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier une association garantie-acte."
        )
        return redirect("garantie_actes")

    try:
        garantie_acte = GarantieActe.objects.get(
            id_garantie_acte=id_garantie_acte
        )
    except GarantieActe.DoesNotExist:
        messages.error(
            request,
            "Association garantie-acte introuvable."
        )
        return redirect("garantie_actes")

    garanties = (
        Garantie.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )
    id_acte_preselectionne = request.GET.get("id_acte", "").strip()

    if request.method == "POST":
        form = GarantieActeForm(request.POST)

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (
                str(a.id_acte),
                f"{a.code_acte} - {a.libelle}"
            )
            for a in actes
        ]

        if form.is_valid():
            try:
                garantie_acte.id_garantie_id = (
                    form.cleaned_data["id_garantie"]
                )
                garantie_acte.id_acte_id = (
                    form.cleaned_data["id_acte"]
                )
                garantie_acte.taux_prise_en_charge = (
                    form.cleaned_data["taux_prise_en_charge"]
                )
                garantie_acte.franchise = (
                    form.cleaned_data["franchise"]
                )
                garantie_acte.date_debut = (
                    form.cleaned_data["date_debut"]
                )
                garantie_acte.date_fin = (
                    form.cleaned_data["date_fin"]
                )
                garantie_acte.statut = (
                    form.cleaned_data["statut"]
                )

                garantie_acte.save()

                messages.success(
                    request,
                    "Association garantie-acte modifiée avec succès."
                )
                return redirect("garantie_actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = GarantieActeForm(
            initial={
                "id_garantie": str(
                    garantie_acte.id_garantie_id
                ),
                "id_acte": str(
                    garantie_acte.id_acte_id
                ),
                "taux_prise_en_charge":
                    garantie_acte.taux_prise_en_charge,
                "franchise":
                    garantie_acte.franchise,
                "date_debut":
                    garantie_acte.date_debut,
                "date_fin":
                    garantie_acte.date_fin,
                "statut":
                    garantie_acte.statut,
            }
        )

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (
                str(a.id_acte),
                f"{a.code_acte} - {a.libelle}"
            )
            for a in actes
        ]

    return render(
        request,
        "core/garantie_acte_form.html",
        {
            "form": form,
            "titre": "Modifier l'association garantie-acte",
        }
    )
def garantie_acte_radier(request, id_garantie_acte):
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

    if "GARANTIE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une association garantie-acte."
        )
        return redirect("garantie_actes")

    try:
        garantie_acte = GarantieActe.objects.get(
            id_garantie_acte=id_garantie_acte
        )
    except GarantieActe.DoesNotExist:
        messages.error(
            request,
            "Association garantie-acte introuvable."
        )
        return redirect("garantie_actes")

    if request.method == "POST":
        garantie_acte.statut = "RADIE"
        garantie_acte.save()

        messages.success(
            request,
            "Association garantie-acte radiÃ©e avec succÃ¨s."
        )

    return redirect("garantie_actes")
def adhesions(request):
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

    if "ADHESION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les adhÃ©sions."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    adhesions = (
        Adhesion.objects
        .select_related(
            "id_adherent",
            "id_adherent__id_personne",
            "id_contrat",
            "id_contrat__id_souscripteur",
        )
        .all()
        .order_by("-id_adhesion")
    )
    adhesions = (
        Adhesion.objects
        .select_related(
            "id_adherent",
            "id_adherent__id_personne",
            "id_contrat",
            "id_contrat__id_souscripteur",
        )
        .all()
        .order_by("-id_adhesion")
    )
    
    if recherche:
        from django.db.models import Q

        adhesions = adhesions.filter(
            Q(numero_adhesion__icontains=recherche)
            | Q(
                id_adherent__numero_adherent__icontains=recherche
            )
            | Q(
                id_contrat__numero_contrat__icontains=recherche
            )
            | Q(
                id_contrat__id_souscripteur__raison_sociale__icontains=recherche
            )
        )

    if statut:
        adhesions = adhesions.filter(
            statut=statut
        )

    return render(
        request,
        "core/adhesions.html",
        {
            "adhesions": adhesions,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )
def _generer_numero_adhesion():
    annee = timezone.now().year
    prefixe = f"ADHES-{annee}-"

    numeros = (
        Adhesion.objects
        .filter(numero_adhesion__startswith=prefixe)
        .values_list("numero_adhesion", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    numero_adhesion = f"{prefixe}{prochain:04d}"

    while Adhesion.objects.filter(
        numero_adhesion=numero_adhesion
    ).exists():
        prochain += 1
        numero_adhesion = f"{prefixe}{prochain:04d}"

    return numero_adhesion

def adhesion_create(request):
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

    if "ADHESION_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er une adhÃ©sion."
        )
        return redirect("adhesions")

    adherents = (
        Adherent.objects
        .filter(statut="ACTIF")
        .order_by("numero_adherent")
    )

    contrats = (
        Contrat.objects
        .filter(statut="ACTIF")
        .select_related("id_souscripteur")
        .order_by("numero_contrat")
    )
    id_contrat_preselectionne = request.GET.get(
        "id_contrat",
        ""
    ).strip()

    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects
            .filter(
                id_contrat=id_contrat_preselectionne,
                statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )    
    id_contrat_preselectionne = request.GET.get(
        "id_contrat",
        ""
    ).strip()

    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects
            .filter(
                id_contrat=id_contrat_preselectionne,
                statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )

    if request.method == "POST":
        form = AdhesionForm(request.POST)

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                f"{a.numero_adherent}"
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]
        if contrat_preselectionne:
            form.initial["id_contrat"] = (
                str(contrat_preselectionne.id_contrat)
                
            )

        if form.is_valid():
            try:
                adherent = Adherent.objects.get(
                    id_adherent=form.cleaned_data["id_adherent"],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.get(
                    id_contrat=form.cleaned_data["id_contrat"],
                    statut="ACTIF"
                )

                Adhesion.objects.create(
                    id_adherent=adherent,
                    id_contrat=contrat,
                    numero_adhesion=_generer_numero_adhesion(),
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                messages.success(
                    request,
                    "AdhÃ©sion crÃ©Ã©e avec succÃ¨s."
                )

                return redirect("adhesions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = AdhesionForm()

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                f"{a.numero_adherent}"
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

    return render(
        request,
        "core/adhesion_form.html",
        {
            "form": form,
            "titre": "Nouvelle adhÃ©sion",
            "contrat_preselectionne": contrat_preselectionne,
        }
    )

def adhesion_modifier(request, id_adhesion):
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

    if "ADHESION_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier une adhÃ©sion."
        )
        return redirect("adhesions")

    try:
        adhesion = Adhesion.objects.get(
            id_adhesion=id_adhesion
        )
    except Adhesion.DoesNotExist:
        messages.error(
            request,
            "AdhÃ©sion introuvable."
        )
        return redirect("adhesions")

    adherents = (
        Adherent.objects
        .filter(statut="ACTIF")
        .order_by("numero_adherent")
    )

    contrats = (
        Contrat.objects
        .filter(statut="ACTIF")
        .select_related("id_souscripteur")
        .order_by("numero_contrat")
    )

    if request.method == "POST":
        form = AdhesionForm(request.POST)

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                a.numero_adherent
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

        if form.is_valid():
            try:
                adherent = Adherent.objects.get(
                    id_adherent=form.cleaned_data["id_adherent"],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.get(
                    id_contrat=form.cleaned_data["id_contrat"],
                    statut="ACTIF"
                )

                adhesion.id_adherent = adherent
                adhesion.id_contrat = contrat
               

                adhesion.date_debut = (
                    form.cleaned_data["date_debut"]
                )
                adhesion.date_fin = (
                    form.cleaned_data["date_fin"]
                )
                adhesion.statut = (
                    form.cleaned_data["statut"]
                )

                adhesion.save()

                messages.success(
                    request,
                    "AdhÃ©sion modifiÃ©e avec succÃ¨s."
                )

                return redirect("adhesions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = AdhesionForm(
            initial={
                "id_adherent": str(
                    adhesion.id_adherent_id
                ),
                "id_contrat": str(
                    adhesion.id_contrat_id
                ),
                "numero_adhesion": adhesion.numero_adhesion,
                "date_debut": adhesion.date_debut,
                "date_fin": adhesion.date_fin,
                "statut": adhesion.statut,
            }
        )

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                a.numero_adherent
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

    return render(
        request,
        "core/adhesion_form.html",
        {
            "form": form,
            "titre": "Modifier l'adhÃ©sion",
        }
    )
def adhesion_radier(request, id_adhesion):
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

    if "ADHESION_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une adhÃ©sion."
        )
        return redirect("adhesions")

    try:
        adhesion = Adhesion.objects.get(
            id_adhesion=id_adhesion
        )
    except Adhesion.DoesNotExist:
        messages.error(
            request,
            "AdhÃ©sion introuvable."
        )
        return redirect("adhesions")

    if request.method == "POST":
        adhesion.statut = "RADIE"
        adhesion.save()

        messages.success(
            request,
            "AdhÃ©sion radiÃ©e avec succÃ¨s."
        )

    return redirect("adhesions")
def adhesion_export_excel(request):

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

    if "ADHESION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les adhésions."
        )
        return redirect("adhesions")

    import openpyxl
    from openpyxl.styles import Font
    from django.http import HttpResponse

    adhesions_list = (
        Adhesion.objects
        .select_related(
            "id_adherent",
            "id_adherent__id_personne",
            "id_contrat",
            "id_contrat__id_souscripteur",
        )
        .all()
        .order_by("numero_adhesion")
    )

    workbook = openpyxl.Workbook()
    feuille = workbook.active
    feuille.title = "Adhesions"

    entetes = [
        "Numéro adhésion",
        "Numéro adhérent",
        "Nom",
        "Prénom",
        "Numéro contrat",
        "Souscripteur",
        "Date début",
        "Date fin",
        "Statut",
        "Date création",
    ]

    feuille.append(entetes)

    for cellule in feuille[1]:
        cellule.font = Font(bold=True)

    for adhesion in adhesions_list:

        personne = adhesion.id_adherent.id_personne
        contrat = adhesion.id_contrat
        souscripteur = contrat.id_souscripteur

        feuille.append([
            adhesion.numero_adhesion,
            adhesion.id_adherent.numero_adherent,
            personne.nom,
            personne.prenom,
            contrat.numero_contrat,
            souscripteur.raison_sociale,
            adhesion.date_debut,
            adhesion.date_fin,
            adhesion.statut,
            adhesion.date_creation,
        ])

    for colonne in feuille.columns:

        longueur_max = 0
        lettre_colonne = colonne[0].column_letter

        for cellule in colonne:

            try:
                longueur = (
                    len(str(cellule.value))
                    if cellule.value
                    else 0
                )

                if longueur > longueur_max:
                    longueur_max = longueur

            except Exception:
                pass

        feuille.column_dimensions[
            lettre_colonne
        ].width = min(longueur_max + 2, 50)

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response[
        "Content-Disposition"
    ] = 'attachment; filename="adhesions.xlsx"'

    workbook.save(response)

    return response

def personne_create(request):
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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er une personne."
        )
        return redirect("adherents")

    if request.method == "POST":
        form = PersonneForm(request.POST)

        if form.is_valid():
            try:
                Personne.objects.create(
                    numero_personne=_generer_numero_personne(),
                    nom=form.cleaned_data["nom"],
                    prenom=form.cleaned_data["prenom"],
                    date_naissance=form.cleaned_data["date_naissance"],
                    sexe=form.cleaned_data["sexe"] or None,
                    adresse=form.cleaned_data["adresse"] or None,
                    telephone=form.cleaned_data["telephone"] or None,
                    email=form.cleaned_data["email"] or None,
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                messages.success(
                    request,
                    "Personne crÃ©Ã©e avec succÃ¨s."
                )

                return redirect("personne_create")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = PersonneForm()

    return render(
        request,
        "core/personne_form.html",
        {
            "form": form,
            "titre": "Nouvelle personne",
        }
    )

def ayant_droits(request):
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

    if "AYANT_DROIT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les ayants droit."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    id_adherent = request.GET.get("id_adherent", "").strip()

    ayant_droits = (
        AyantDroit.objects
        .select_related(
            "id_personne",
            "id_adherent",
            "id_adherent__id_personne",
        )
        .all()
        .order_by("-id_ayant_droit")
    )

    if recherche:
        from django.db.models import Q

        ayant_droits = ayant_droits.filter(
            Q(id_personne__nom__icontains=recherche)
            | Q(id_personne__prenom__icontains=recherche)
            | Q(id_personne__numero_personne__icontains=recherche)
            | Q(id_adherent__numero_adherent__icontains=recherche)
            | Q(type_lien__icontains=recherche)
        )

    if id_adherent:
        ayant_droits = ayant_droits.filter(
            id_adherent=id_adherent
        )

    adherents = (
        Adherent.objects
        .filter(statut="ACTIF")
        .order_by("numero_adherent")
    )

    return render(
        request,
        "core/ayant_droits.html",
        {
            "ayant_droits": ayant_droits,
            "adherents": adherents,
            "recherche": recherche,
            "id_adherent": id_adherent,
            "permissions": permissions,
        }
    )

def ayant_droit_create(request):
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

    if "AYANT_DROIT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un ayant droit."
        )
        return redirect("ayant_droits")

    id_adherent_preselectionne = request.GET.get(
        "id_adherent",
        ""
    ).strip()

    adherent_preselectionne = None

    if id_adherent_preselectionne:
        adherent_preselectionne = (
            Adherent.objects
            .filter(
                id_adherent=id_adherent_preselectionne,
                statut="ACTIF"
            )
            .select_related("id_personne")
            .first()
        )

    if not adherent_preselectionne:
        messages.error(
            request,
            "Veuillez sélectionner un adhérent."
        )
        return redirect("adherents")

    if request.method == "POST":
        form = AyantDroitForm(
    request.POST,
    nom_adherent=adherent_preselectionne.id_personne.nom
)

        if form.is_valid():
            try:
                with transaction.atomic():

                    doublon = (
                        AyantDroit.objects
                        .filter(
                            id_adherent=adherent_preselectionne,
                            id_personne__nom__iexact=form.cleaned_data["nom"].strip(),
                            id_personne__prenom__iexact=form.cleaned_data["prenom"].strip(),
                            id_personne__date_naissance=form.cleaned_data["date_naissance"],
                            statut="ACTIF",
                        )
                        .first()
                    )

                    if doublon:
                        messages.error(
                            request,
                            "Cet ayant droit existe déjà pour cet adhérent."
                        )
                        return render(
                            request,
                            "core/ayant_droit_form.html",
                            {
                                "form": form,
                                "titre": "Nouvel ayant droit",
                                "adherent_preselectionne": adherent_preselectionne,
                            }
                        )

                    personne = Personne.objects.create(
                        numero_personne=_generer_numero_personne(),
                        nom=form.cleaned_data["nom"].strip(),
                        prenom=form.cleaned_data["prenom"].strip(),
                        date_naissance=form.cleaned_data["date_naissance"],
                        sexe=form.cleaned_data["sexe"] or None,
                        adresse=None,
                        telephone=None,
                        email=None,
                        statut=form.cleaned_data["statut"],
                        date_creation=timezone.now(),
                    )

                    AyantDroit.objects.create(
                        id_personne=personne,
                        id_adherent=adherent_preselectionne,
                        type_lien=form.cleaned_data["type_lien"],
                        date_debut=form.cleaned_data["date_debut"],
                        date_fin=form.cleaned_data["date_fin"],
                        statut=form.cleaned_data["statut"],
                    )

                messages.success(
                    request,
                    "Ayant droit créé avec succès."
                )

                return redirect(
                    "adherent_detail",
                    id_adherent=adherent_preselectionne.id_adherent
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création de l'ayant droit : {e}"
                )

    else:
        form = AyantDroitForm(
    initial={
        "id_adherent": str(
            adherent_preselectionne.id_adherent
        ),
        "statut": "ACTIF",
    },
    nom_adherent=adherent_preselectionne.id_personne.nom,
    date_adhesion=adherent_preselectionne.date_adhesion
)

    return render(
        request,
        "core/ayant_droit_form.html",
        {
            "form": form,
            "titre": "Nouvel ayant droit",
            "adherent_preselectionne": adherent_preselectionne,
        }
    )

                    
def ayant_droit_modifier(request, id_ayant_droit):
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

    if "AYANT_DROIT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un ayant droit."
        )
        return redirect("ayant_droits")

    try:
        ayant_droit = (
            AyantDroit.objects
            .select_related("id_personne", "id_adherent")
            .get(id_ayant_droit=id_ayant_droit)
        )
    except AyantDroit.DoesNotExist:
        messages.error(
            request,
            "Ayant droit introuvable."
        )
        return redirect("ayant_droits")

    personnes = (
        Personne.objects
        .filter(statut="ACTIF")
        .exclude(
            id_personne__in=Adherent.objects.values("id_personne")
        )
        .order_by("nom", "prenom")
    )

    adherents = (
        Adherent.objects
        .filter(statut="ACTIF")
        .order_by("numero_adherent")
    )

    if request.method == "POST":
        form = AyantDroitForm(
    request.POST,
    nom_adherent=adherent_preselectionne.id_personne.nom,
    date_adhesion=adherent_preselectionne.date_adhesion
)

        form.fields["id_adherent"].choices = [
        (
            str(adherent_preselectionne.id_adherent),
            adherent_preselectionne.numero_adherent
        )
    ]

        form.fields["id_personne"].choices = [
            (
                str(p.id_personne),
                f"{p.numero_personne or ''} - {p.nom} {p.prenom}"
            )
            for p in personnes
        ]

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                a.numero_adherent
            )
            for a in adherents
        ]

        if form.is_valid():
            try:
                personne = Personne.objects.get(
                    id_personne=form.cleaned_data["id_personne"],
                    statut="ACTIF"
                )

                adherent = Adherent.objects.get(
                    id_adherent=form.cleaned_data["id_adherent"],
                    statut="ACTIF"
                )

                ayant_droit.id_personne = personne
                ayant_droit.id_adherent = adherent
                ayant_droit.type_lien = form.cleaned_data["type_lien"]
                ayant_droit.date_debut = form.cleaned_data["date_debut"]
                ayant_droit.date_fin = form.cleaned_data["date_fin"]
                ayant_droit.statut = form.cleaned_data["statut"]

                ayant_droit.save()

                messages.success(
                    request,
                    "Ayant droit modifiÃ© avec succÃ¨s."
                )

                return redirect("ayant_droits")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = AyantDroitForm(
            initial={
                "id_personne": str(
                    ayant_droit.id_personne_id
                ),
                "id_adherent": str(
                    ayant_droit.id_adherent_id
                ),
                "type_lien": ayant_droit.type_lien,
                "date_debut": ayant_droit.date_debut,
                "date_fin": ayant_droit.date_fin,
                "statut": ayant_droit.statut,
            }
        )

        form.fields["id_personne"].choices = [
            (
                str(p.id_personne),
                f"{p.numero_personne or ''} - {p.nom} {p.prenom}"
            )
            for p in personnes
        ]

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                a.numero_adherent
            )
            for a in adherents
        ]

    return render(
        request,
        "core/ayant_droit_form.html",
        {
            "form": form,
            "titre": "Modifier l'ayant droit",
        }
    )
def ayant_droit_radier(request, id_ayant_droit):
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

    if "AYANT_DROIT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un ayant droit."
        )
        return redirect("ayant_droits")

    try:
        ayant_droit = AyantDroit.objects.get(
            id_ayant_droit=id_ayant_droit
        )
    except AyantDroit.DoesNotExist:
        messages.error(
            request,
            "Ayant droit introuvable."
        )
        return redirect("ayant_droits")

    if request.method == "POST":
        ayant_droit.statut = "RADIE"
        ayant_droit.save()

        messages.success(
            request,
            "Ayant droit radiÃ© avec succÃ¨s."
        )

def ayant_droit_export_excel(request):

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

    if "AYANT_DROIT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les ayants droit."
        )
        return redirect("ayant_droits")

    import openpyxl
    from openpyxl.styles import Font
    from django.http import HttpResponse

    ayant_droits_list = (
        AyantDroit.objects
        .select_related(
            "id_personne",
            "id_adherent",
            "id_adherent__id_personne",
        )
        .all()
        .order_by("id_ayant_droit")
    )

    workbook = openpyxl.Workbook()
    feuille = workbook.active
    feuille.title = "Ayants droits"

    entetes = [
        "Numéro ayant droit",
        "Numéro personne",
        "Nom",
        "Prénom",
        "Numéro adhérent",
        "Nom adhérent",
        "Type de lien",
        "Date début",
        "Date fin",
        "Statut",
    ]

    feuille.append(entetes)

    for cellule in feuille[1]:
        cellule.font = Font(bold=True)

    for ayant_droit in ayant_droits_list:

        personne = ayant_droit.id_personne
        adherent = ayant_droit.id_adherent
        personne_adherent = adherent.id_personne

        feuille.append([
            ayant_droit.id_ayant_droit,
            personne.numero_personne,
            personne.nom,
            personne.prenom,
            adherent.numero_adherent,
            f"{personne_adherent.nom} {personne_adherent.prenom}",
            ayant_droit.type_lien,
            ayant_droit.date_debut,
            ayant_droit.date_fin,
            ayant_droit.statut,
        ])

    for colonne in feuille.columns:

        longueur_max = 0
        lettre_colonne = colonne[0].column_letter

        for cellule in colonne:

            try:
                longueur = (
                    len(str(cellule.value))
                    if cellule.value
                    else 0
                )

                if longueur > longueur_max:
                    longueur_max = longueur

            except Exception:
                pass

        feuille.column_dimensions[
            lettre_colonne
        ].width = min(longueur_max + 2, 50)

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response[
        "Content-Disposition"
    ] = 'attachment; filename="ayants_droits.xlsx"'

    workbook.save(response)

    return response

    return redirect("ayant_droits")
def prestataires(request):
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

    if "PRESTATAIRE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les prestataires."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    type_prestataire = request.GET.get("type_prestataire", "").strip()
    statut = request.GET.get("statut", "").strip()

    prestataires = (
        Prestataire.objects
        .all()
        .order_by("raison_sociale")
    )

    if recherche:
        from django.db.models import Q

        prestataires = prestataires.filter(
            Q(code_prestataire__icontains=recherche)
            | Q(raison_sociale__icontains=recherche)
            | Q(nif__icontains=recherche)
            | Q(registre_commerce__icontains=recherche)
            | Q(telephone__icontains=recherche)
        )

    if type_prestataire:
        prestataires = prestataires.filter(
            type_prestataire=type_prestataire
        )

    if statut:
        prestataires = prestataires.filter(
            statut=statut
        )

    types_prestataire = [
        ("PHARMACIE", "Pharmacie"),
        ("MEDECIN", "MÃ©decin"),
        ("CLINIQUE", "Clinique"),
        ("LABORATOIRE", "Laboratoire"),
        ("CENTRE_RADIOLOGIE", "Centre de radiologie"),
        ("DENTAIRE", "Centre dentaire"),
        ("OPTIQUE", "Centre optique"),
        ("AUTRE", "Autre"),
    ]

    return render(
        request,
        "core/prestataires.html",
        {
            "prestataires": prestataires,
            "recherche": recherche,
            "type_prestataire": type_prestataire,
            "statut": statut,
            "types_prestataire": types_prestataire,
            "permissions": permissions,
        }
    )
def _generer_code_prestataire():
    annee = timezone.now().year
    prefixe = f"PREST-{annee}-"

    codes = (
        Prestataire.objects
        .filter(code_prestataire__startswith=prefixe)
        .values_list("code_prestataire", flat=True)
    )

    valeurs = []

    for code in codes:
        try:
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code_prestataire = f"{prefixe}{prochain:04d}"

    while Prestataire.objects.filter(
        code_prestataire=code_prestataire
    ).exists():
        prochain += 1
        code_prestataire = f"{prefixe}{prochain:04d}"

    return code_prestataire

def prestataire_create(request):
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

    if "PRESTATAIRE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er un prestataire."
        )
        return redirect("prestataires")

    if request.method == "POST":
        form = PrestataireForm(request.POST)

        if form.is_valid():
            try:
                Prestataire.objects.create(
                    code_prestataire=_generer_code_prestataire(),
                    raison_sociale=form.cleaned_data["raison_sociale"],
                    type_prestataire=form.cleaned_data["type_prestataire"],
                    nif=form.cleaned_data["nif"] or None,
                    registre_commerce=form.cleaned_data["registre_commerce"] or None,
                    adresse=form.cleaned_data["adresse"] or None,
                    telephone=form.cleaned_data["telephone"] or None,
                    email=form.cleaned_data["email"] or None,
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                messages.success(
                    request,
                    "Prestataire crÃ©Ã© avec succÃ¨s."
                )

                return redirect("prestataires")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = PrestataireForm()

    return render(
        request,
        "core/prestataire_form.html",
        {
            "form": form,
            "titre": "Nouveau prestataire",
        }
    )
def prestataire_modifier(request, id_prestataire):
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

    if "PRESTATAIRE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un prestataire."
        )
        return redirect("prestataires")

    try:
        prestataire = Prestataire.objects.get(
            id_prestataire=id_prestataire
        )
    except Prestataire.DoesNotExist:
        messages.error(
            request,
            "Prestataire introuvable."
        )
        return redirect("prestataires")

    if request.method == "POST":
        form = PrestataireForm(request.POST)

        if form.is_valid():
            try:
                
                prestataire.raison_sociale = (
                    form.cleaned_data["raison_sociale"]
                )
                prestataire.type_prestataire = (
                    form.cleaned_data["type_prestataire"]
                )
                prestataire.nif = (
                    form.cleaned_data["nif"] or None
                )
                prestataire.registre_commerce = (
                    form.cleaned_data["registre_commerce"] or None
                )
                prestataire.adresse = (
                    form.cleaned_data["adresse"] or None
                )
                prestataire.telephone = (
                    form.cleaned_data["telephone"] or None
                )
                prestataire.email = (
                    form.cleaned_data["email"] or None
                )
                prestataire.statut = (
                    form.cleaned_data["statut"]
                )

                prestataire.save()

                messages.success(
                    request,
                    "Prestataire modifiÃ© avec succÃ¨s."
                )

                return redirect("prestataires")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = PrestataireForm(
            initial={
                "code_prestataire": prestataire.code_prestataire,
                "raison_sociale": prestataire.raison_sociale,
                "type_prestataire": prestataire.type_prestataire,
                "nif": prestataire.nif,
                "registre_commerce": prestataire.registre_commerce,
                "adresse": prestataire.adresse,
                "telephone": prestataire.telephone,
                "email": prestataire.email,
                "statut": prestataire.statut,
            }
        )

    return render(
        request,
        "core/prestataire_form.html",
        {
            "form": form,
            "titre": "Modifier le prestataire",
        }
    )
def prestataire_radier(request, id_prestataire):
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

    if "PRESTATAIRE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un prestataire."
        )
        return redirect("prestataires")

    try:
        prestataire = Prestataire.objects.get(
            id_prestataire=id_prestataire
        )
    except Prestataire.DoesNotExist:
        messages.error(
            request,
            "Prestataire introuvable."
        )
        return redirect("prestataires")

    if request.method == "POST":
        prestataire.statut = "INACTIF"
        prestataire.save()

        messages.success(
            request,
            "Prestataire dÃ©sactivÃ© avec succÃ¨s."
        )

    return redirect("prestataires")
def conventions(request):
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

    if "CONVENTION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les conventions."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    conventions = (
        Convention.objects
        .select_related("id_prestataire")
        .all()
        .order_by("-date_debut", "numero_convention")
    )

    if recherche:
        conventions = conventions.filter(
            Q(numero_convention__icontains=recherche)
            | Q(id_prestataire__code_prestataire__icontains=recherche)
            | Q(id_prestataire__raison_sociale__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        conventions = conventions.filter(statut=statut)

    statuts = (
        Convention.objects
        .exclude(statut__isnull=True)
        .exclude(statut="")
        .values_list("statut", flat=True)
        .distinct()
        .order_by("statut")
    )

    return render(
        request,
        "core/conventions.html",
        {
            "conventions": conventions,
            "permissions": permissions,
            "recherche": recherche,
            "statut": statut,
            "statuts": statuts,
        }
    )
def _generer_numero_convention():
    annee = timezone.now().year
    prefixe = f"CONV-{annee}-"

    numeros = (
        Convention.objects
        .filter(numero_convention__startswith=prefixe)
        .values_list("numero_convention", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_convention = f"{prefixe}{prochain:04d}"

    while Convention.objects.filter(
        numero_convention=numero_convention
    ).exists():
        prochain += 1
        numero_convention = f"{prefixe}{prochain:04d}"

    return numero_convention

def convention_create(request):
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

    if "CONVENTION_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer une convention."
        )
        return redirect("conventions")

    if request.method == "POST":
        form = ConventionForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    convention = Convention.objects.create(
                        id_prestataire=form.cleaned_data["id_prestataire"],
                        numero_convention=_generer_numero_convention(),
                        date_debut=form.cleaned_data["date_debut"],
                        date_fin=form.cleaned_data["date_fin"],
                        statut=form.cleaned_data["statut"],
                        description=form.cleaned_data["description"] or None,
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="CREATION",
                        module="CONVENTION",
                        table_cible="convention",
                        id_enregistrement=convention.id_convention,
                        nouvelle_valeur=(
                            f"Numéro : {convention.numero_convention}, "
                            f"Prestataire : "
                            f"{convention.id_prestataire.raison_sociale}, "
                            f"Statut : {convention.statut}"
                        ),
                        description=(
                            f"Création de la convention "
                            f"{convention.numero_convention}"
                        ),
                    )

                messages.success(
                    request,
                    "Convention créée avec succès."
                )

                return redirect("conventions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création de la convention : {e}"
                )

    else:
        form = ConventionForm()

    return render(
        request,
        "core/convention_form.html",
        {
            "form": form,
            "titre": "Nouvelle convention",
        }
    )
def convention_modifier(request, id_convention):
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

    if "CONVENTION_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier une convention."
        )
        return redirect("conventions")

    try:
        convention = (
            Convention.objects
            .select_related("id_prestataire")
            .get(id_convention=id_convention)
        )
    except Convention.DoesNotExist:
        messages.error(
            request,
            "Convention introuvable."
        )
        return redirect("conventions")

    if request.method == "POST":
        form = ConventionForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    ancienne_valeur = (
                        f"Numéro : {convention.numero_convention}, "
                        f"Prestataire : "
                        f"{convention.id_prestataire.raison_sociale}, "
                        f"Date début : {convention.date_debut}, "
                        f"Date fin : {convention.date_fin}, "
                        f"Statut : {convention.statut}"
                    )

                    convention.id_prestataire = (
                        form.cleaned_data["id_prestataire"]
                    )
                    
                    convention.date_debut = (
                        form.cleaned_data["date_debut"]
                    )
                    convention.date_fin = (
                        form.cleaned_data["date_fin"]
                    )
                    convention.statut = (
                        form.cleaned_data["statut"]
                    )
                    convention.description = (
                        form.cleaned_data["description"] or None
                    )

                    convention.save()

                    nouvelle_valeur = (
                        f"Numéro : {convention.numero_convention}, "
                        f"Prestataire : "
                        f"{convention.id_prestataire.raison_sociale}, "
                        f"Date début : {convention.date_debut}, "
                        f"Date fin : {convention.date_fin}, "
                        f"Statut : {convention.statut}"
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="MODIFICATION",
                        module="CONVENTION",
                        table_cible="convention",
                        id_enregistrement=convention.id_convention,
                        ancienne_valeur=ancienne_valeur,
                        nouvelle_valeur=nouvelle_valeur,
                        description=(
                            f"Modification de la convention "
                            f"{convention.numero_convention}"
                        ),
                    )

                messages.success(
                    request,
                    "Convention modifiée avec succès."
                )

                return redirect("conventions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = ConventionForm(initial={
            "id_prestataire": convention.id_prestataire,
            "numero_convention": convention.numero_convention,
            "date_debut": convention.date_debut,
            "date_fin": convention.date_fin,
            "statut": convention.statut,
            "description": convention.description,
        })

    return render(
        request,
        "core/convention_form.html",
        {
            "form": form,
            "titre": "Modifier la convention",
        }
    )
def convention_cloturer(request, id_convention):
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

    if "CONVENTION_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de clôturer une convention."
        )
        return redirect("conventions")

    try:
        convention = Convention.objects.get(
            id_convention=id_convention
        )
    except Convention.DoesNotExist:
        messages.error(
            request,
            "Convention introuvable."
        )
        return redirect("conventions")

    if request.method == "POST":
        try:
            ancienne_valeur = f"Statut : {convention.statut}"

            convention.statut = "CLOTUREE"
            convention.date_fin = timezone.now().date()
            convention.save()

            enregistrer_audit(
                request=request,
                type_action="CLOTURE",
                module="CONVENTION",
                table_cible="convention",
                id_enregistrement=convention.id_convention,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=(
                    f"Statut : {convention.statut}, "
                    f"Date fin : {convention.date_fin}"
                ),
                description=(
                    f"Clôture de la convention "
                    f"{convention.numero_convention}"
                ),
            )

            messages.success(
                request,
                "Convention clôturée avec succès."
            )

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la clôture : {e}"
            )

        return redirect("conventions")

    return render(
        request,
        "core/convention_cloturer.html",
        {
            "convention": convention,
        }
    )
def plafond_create(request):
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

    if "PLAFOND_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un plafond."
        )
        return redirect("plafonds")

    garantie_actes = (
        GarantieActe.objects
        .select_related(
            "id_garantie",
            "id_acte",
        )
        .filter(statut="ACTIF")
        .order_by(
            "id_garantie__libelle",
            "id_acte__libelle",
        )
    )

    if request.method == "POST":
        form = PlafondForm(request.POST)

        form.fields["id_garantie_acte"].choices = [
            (
                str(ga.id_garantie_acte),
                f"{ga.id_garantie.code_garantie} - "
                f"{ga.id_garantie.libelle} / "
                f"{ga.id_acte.code_acte} - "
                f"{ga.id_acte.libelle}"
            )
            for ga in garantie_actes
        ]

        if form.is_valid():
            try:
                garantie_acte = GarantieActe.objects.get(
                    id_garantie_acte=form.cleaned_data[
                        "id_garantie_acte"
                    ],
                    statut="ACTIF",
                )

                plafond = Plafond.objects.create(
                    id_garantie_acte=garantie_acte,
                    type_plafond=form.cleaned_data["type_plafond"],
                    niveau_application=form.cleaned_data[
                        "niveau_application"
                    ],
                    periode=form.cleaned_data["periode"],
                    montant_max=form.cleaned_data["montant_max"],
                    quantite_max=form.cleaned_data["quantite_max"],
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                )

                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="PLAFOND",
                    table_cible="plafond",
                    id_enregistrement=plafond.id_plafond,
                    nouvelle_valeur=(
                        f"Garantie : "
                        f"{garantie_acte.id_garantie.libelle}, "
                        f"Acte : "
                        f"{garantie_acte.id_acte.libelle}, "
                        f"Type : {plafond.type_plafond}, "
                        f"Période : {plafond.periode}"
                    ),
                    description=(
                        f"Création du plafond "
                        f"{plafond.id_plafond}"
                    ),
                )

                messages.success(
                    request,
                    "Plafond créé avec succès."
                )

                return redirect("plafonds")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création du plafond : {e}"
                )

    else:
        form = PlafondForm()

        form.fields["id_garantie_acte"].choices = [
            (
                str(ga.id_garantie_acte),
                f"{ga.id_garantie.code_garantie} - "
                f"{ga.id_garantie.libelle} / "
                f"{ga.id_acte.code_acte} - "
                f"{ga.id_acte.libelle}"
            )
            for ga in garantie_actes
        ]

    return render(
        request,
        "core/plafond_form.html",
        {
            "form": form,
            "titre": "Nouveau plafond",
        }
    )
def plafond_modifier(request, id_plafond):
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

    if "PLAFOND_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un plafond."
        )
        return redirect("plafonds")

    try:
        plafond = (
            Plafond.objects
            .select_related(
                "id_garantie_acte",
                "id_garantie_acte__id_garantie",
                "id_garantie_acte__id_acte",
            )
            .get(id_plafond=id_plafond)
        )
    except Plafond.DoesNotExist:
        messages.error(
            request,
            "Plafond introuvable."
        )
        return redirect("plafonds")

    garantie_actes = (
        GarantieActe.objects
        .select_related(
            "id_garantie",
            "id_acte",
        )
        .filter(statut="ACTIF")
        .order_by(
            "id_garantie__libelle",
            "id_acte__libelle",
        )
    )

    if request.method == "POST":
        form = PlafondForm(request.POST)

        form.fields["id_garantie_acte"].choices = [
            (
                str(ga.id_garantie_acte),
                f"{ga.id_garantie.code_garantie} - "
                f"{ga.id_garantie.libelle} / "
                f"{ga.id_acte.code_acte} - "
                f"{ga.id_acte.libelle}"
            )
            for ga in garantie_actes
        ]

        if form.is_valid():
            try:
                ancienne_valeur = (
                    f"Garantie : "
                    f"{plafond.id_garantie_acte.id_garantie.libelle}, "
                    f"Acte : "
                    f"{plafond.id_garantie_acte.id_acte.libelle}, "
                    f"Type : {plafond.type_plafond}, "
                    f"Période : {plafond.periode}, "
                    f"Montant : {plafond.montant_max}, "
                    f"Quantité : {plafond.quantite_max}, "
                    f"Statut : {plafond.statut}"
                )

                garantie_acte = GarantieActe.objects.get(
                    id_garantie_acte=form.cleaned_data[
                        "id_garantie_acte"
                    ],
                    statut="ACTIF",
                )

                plafond.id_garantie_acte = garantie_acte
                plafond.type_plafond = form.cleaned_data["type_plafond"]
                plafond.niveau_application = (
                    form.cleaned_data["niveau_application"]
                )
                plafond.periode = form.cleaned_data["periode"]
                plafond.montant_max = form.cleaned_data["montant_max"]
                plafond.quantite_max = form.cleaned_data["quantite_max"]
                plafond.date_debut = form.cleaned_data["date_debut"]
                plafond.date_fin = form.cleaned_data["date_fin"]
                plafond.statut = form.cleaned_data["statut"]

                plafond.save()

                nouvelle_valeur = (
                    f"Garantie : "
                    f"{plafond.id_garantie_acte.id_garantie.libelle}, "
                    f"Acte : "
                    f"{plafond.id_garantie_acte.id_acte.libelle}, "
                    f"Type : {plafond.type_plafond}, "
                    f"Période : {plafond.periode}, "
                    f"Montant : {plafond.montant_max}, "
                    f"Quantité : {plafond.quantite_max}, "
                    f"Statut : {plafond.statut}"
                )

                enregistrer_audit(
                    request=request,
                    type_action="MODIFICATION",
                    module="PLAFOND",
                    table_cible="plafond",
                    id_enregistrement=plafond.id_plafond,
                    ancienne_valeur=ancienne_valeur,
                    nouvelle_valeur=nouvelle_valeur,
                    description=(
                        f"Modification du plafond "
                        f"{plafond.id_plafond}"
                    ),
                )

                messages.success(
                    request,
                    "Plafond modifié avec succès."
                )

                return redirect("plafonds")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = PlafondForm(
            initial={
                "id_garantie_acte": str(
                    plafond.id_garantie_acte_id
                ),
                "type_plafond": plafond.type_plafond,
                "niveau_application": plafond.niveau_application,
                "periode": plafond.periode,
                "montant_max": plafond.montant_max,
                "quantite_max": plafond.quantite_max,
                "date_debut": plafond.date_debut,
                "date_fin": plafond.date_fin,
                "statut": plafond.statut,
            }
        )

        form.fields["id_garantie_acte"].choices = [
            (
                str(ga.id_garantie_acte),
                f"{ga.id_garantie.code_garantie} - "
                f"{ga.id_garantie.libelle} / "
                f"{ga.id_acte.code_acte} - "
                f"{ga.id_acte.libelle}"
            )
            for ga in garantie_actes
        ]

    return render(
        request,
        "core/plafond_form.html",
        {
            "form": form,
            "titre": "Modifier le plafond",
        }
    )
def plafond_desactiver(request, id_plafond):
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

    if "PLAFOND_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de désactiver un plafond."
        )
        return redirect("plafonds")

    try:
        plafond = (
            Plafond.objects
            .select_related(
                "id_garantie_acte",
                "id_garantie_acte__id_garantie",
                "id_garantie_acte__id_acte",
            )
            .get(id_plafond=id_plafond)
        )
    except Plafond.DoesNotExist:
        messages.error(
            request,
            "Plafond introuvable."
        )
        return redirect("plafonds")

    if request.method == "POST":
        try:
            ancienne_valeur = (
                f"Garantie : "
                f"{plafond.id_garantie_acte.id_garantie.libelle}, "
                f"Acte : "
                f"{plafond.id_garantie_acte.id_acte.libelle}, "
                f"Statut : {plafond.statut}"
            )

            plafond.statut = "INACTIF"
            plafond.save()

            enregistrer_audit(
                request=request,
                type_action="DESACTIVATION",
                module="PLAFOND",
                table_cible="plafond",
                id_enregistrement=plafond.id_plafond,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur="Statut : INACTIF",
                description=(
                    f"Désactivation du plafond "
                    f"{plafond.id_plafond}"
                ),
            )

            messages.success(
                request,
                "Plafond désactivé avec succès."
            )

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la désactivation : {e}"
            )

        return redirect("plafonds")

    return render(
        request,
        "core/plafond_desactiver.html",
        {
            "plafond": plafond,
        }
    )
def plafonds(request):
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

    if "PLAFOND_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les plafonds."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    type_plafond = request.GET.get("type_plafond", "").strip()
    periode = request.GET.get("periode", "").strip()
    statut = request.GET.get("statut", "").strip()

    plafonds = (
        Plafond.objects
        .select_related(
            "id_garantie_acte",
            "id_garantie_acte__id_garantie",
            "id_garantie_acte__id_acte",
        )
        .all()
        .order_by(
            "id_garantie_acte__id_garantie__libelle",
            "id_garantie_acte__id_acte__libelle",
            "-date_debut",
        )
    )

    if recherche:
        plafonds = plafonds.filter(
            Q(
                id_garantie_acte__id_garantie__code_garantie__icontains=recherche
            )
            | Q(
                id_garantie_acte__id_garantie__libelle__icontains=recherche
            )
            | Q(
                id_garantie_acte__id_acte__code_acte__icontains=recherche
            )
            | Q(
                id_garantie_acte__id_acte__libelle__icontains=recherche
            )
        )

    if type_plafond:
        plafonds = plafonds.filter(
            type_plafond=type_plafond
        )

    if periode:
        plafonds = plafonds.filter(
            periode=periode
        )

    if statut:
        plafonds = plafonds.filter(
            statut=statut
        )

    return render(
        request,
        "core/plafonds.html",
        {
            "plafonds": plafonds,
            "permissions": permissions,
            "recherche": recherche,
            "type_plafond": type_plafond,
            "periode": periode,
            "statut": statut,
        }
    )
def document_create(request):
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

    if "DOCUMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de déposer un document."
        )
        return redirect("documents")

    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                with transaction.atomic():
                    fichier = form.cleaned_data["fichier"]

                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=(
                            form.cleaned_data["type_document"]
                            or getattr(fichier, "content_type", None)
                            or "INCONNU"
                        ),
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="DEPOT_DOCUMENT",
                        module="DOCUMENT",
                        table_cible="document",
                        id_enregistrement=document.id_document,
                        nouvelle_valeur=(
                            f"Fichier : {document.nom_fichier}, "
                            f"Type : {document.type_document}, "
                            f"Taille : {document.taille} octets, "
                            f"Statut : {document.statut}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                messages.success(
                    request,
                    "Document déposé avec succès."
                )

                return redirect("documents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors du dépôt du document : {e}"
                )

    else:
        form = DocumentForm()

    return render(
        request,
        "core/document_form.html",
        {
            "form": form,
            "titre": "Déposer un document",
        }
    )
def document_modifier(request, id_document):
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

    if "DOCUMENT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un document."
        )
        return redirect("documents")

    try:
        document = Document.objects.get(
            id_document=id_document
        )
    except Document.DoesNotExist:
        messages.error(
            request,
            "Document introuvable."
        )
        return redirect("documents")

    if request.method == "POST":
        form = DocumentForm(
            request.POST,
            request.FILES
        )

        form.fields["fichier"].required = False

        if form.is_valid():
            try:
                ancienne_valeur = (
                    f"Nom : {document.nom_fichier}, "
                    f"Type : {document.type_document}, "
                    f"Statut : {document.statut}"
                )

                fichier = form.cleaned_data.get("fichier")

                if fichier:
                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    document.nom_fichier = fichier.name
                    document.extension = (
                        extension or None
                    )
                    document.taille = fichier.size
                    document.emplacement = chemin
                    document.hash_fichier = (
                        hash_sha256.hexdigest()
                    )

                document.type_document = (
                    form.cleaned_data["type_document"]
                    or document.type_document
                )

                document.statut = (
                    form.cleaned_data["statut"]
                )

                document.save()

                nouvelle_valeur = (
                    f"Nom : {document.nom_fichier}, "
                    f"Type : {document.type_document}, "
                    f"Statut : {document.statut}"
                )

                enregistrer_audit(
                    request=request,
                    type_action="MODIFICATION",
                    module="DOCUMENT",
                    table_cible="document",
                    id_enregistrement=document.id_document,
                    ancienne_valeur=ancienne_valeur,
                    nouvelle_valeur=nouvelle_valeur,
                    description=(
                        f"Modification du document "
                        f"{document.nom_fichier}"
                    ),
                )

                messages.success(
                    request,
                    "Document modifié avec succès."
                )

                return redirect("documents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = DocumentForm(
            initial={
                "type_document": document.type_document,
                "statut": document.statut,
            }
        )

        form.fields["fichier"].required = False

    return render(
        request,
        "core/document_form.html",
        {
            "form": form,
            "titre": "Modifier le document",
        }
    )
def document_archiver(request, id_document):
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

    if "DOCUMENT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'archiver un document."
        )
        return redirect("documents")

    try:
        document = Document.objects.get(
            id_document=id_document
        )
    except Document.DoesNotExist:
        messages.error(
            request,
            "Document introuvable."
        )
        return redirect("documents")

    if request.method == "POST":
        try:
            ancienne_valeur = f"Statut : {document.statut}"

            document.statut = "ARCHIVE"
            document.save()

            enregistrer_audit(
                request=request,
                type_action="ARCHIVAGE",
                module="DOCUMENT",
                table_cible="document",
                id_enregistrement=document.id_document,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur="Statut : ARCHIVE",
                description=(
                    f"Archivage du document "
                    f"{document.nom_fichier}"
                ),
            )

            messages.success(
                request,
                "Document archivé avec succès."
            )

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de l'archivage : {e}"
            )

        return redirect("documents")

    return render(
        request,
        "core/document_archiver.html",
        {
            "document": document,
        }
    )
def document_ouvrir(request, id_document):
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

    if "DOCUMENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ouvrir ce document."
        )
        return redirect("documents")

    try:
        document = Document.objects.get(
            id_document=id_document
        )
    except Document.DoesNotExist:
        messages.error(
            request,
            "Document introuvable."
        )
        return redirect("documents")

    if not default_storage.exists(document.emplacement):
        messages.error(
            request,
            "Le fichier physique est introuvable."
        )
        return redirect("documents")

    fichier = default_storage.open(
        document.emplacement,
        "rb"
    )

    response = FileResponse(
        fichier,
        as_attachment=False,
        filename=document.nom_fichier
    )

    return response

def documents(request):
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

    if "DOCUMENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les documents."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    documents = (
        Document.objects
        .select_related("id_utilisateur")
        .all()
        .order_by("-date_depot")
    )

    if recherche:
        documents = documents.filter(
            Q(nom_fichier__icontains=recherche)
            | Q(type_document__icontains=recherche)
            | Q(extension__icontains=recherche)
            | Q(hash_fichier__icontains=recherche)
        )

    if statut:
        documents = documents.filter(statut=statut)

    statuts = (
        Document.objects
        .exclude(statut__isnull=True)
        .exclude(statut="")
        .values_list("statut", flat=True)
        .distinct()
        .order_by("statut")
    )

    return render(
        request,
        "core/documents.html",
        {
            "documents": documents,
            "permissions": permissions,
            "recherche": recherche,
            "statut": statut,
            "statuts": statuts,
        }
    )
def demandes_tp(request):
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

    if "DEMANDE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les demandes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    demandes = (
        DemandeTp.objects
        .select_related(
            "id_personne_beneficiaire",
            "id_contrat",
            "id_prestataire",
        )
        .all()
        .order_by("-id_demande")
    )

    if recherche:
        from django.db.models import Q

        demandes = demandes.filter(
            Q(numero_demande__icontains=recherche)
            | Q(
                id_personne_beneficiaire__nom__icontains=recherche
            )
            | Q(
                id_personne_beneficiaire__prenom__icontains=recherche
            )
            | Q(
                id_contrat__numero_contrat__icontains=recherche
            )
            | Q(
                id_prestataire__raison_sociale__icontains=recherche
            )
        )

    if statut:
        demandes = demandes.filter(
            statut=statut
        )

    statuts = [
        ("EN_ATTENTE", "En attente"),
        ("ACCEPTEE", "AcceptÃ©e"),
        ("REJETEE", "RejetÃ©e"),
        ("ANNULEE", "AnnulÃ©e"),
    ]

    return render(
        request,
        "core/demandes_tp.html",
        {
            "demandes": demandes,
            "recherche": recherche,
            "statut": statut,
            "statuts": statuts,
            "permissions": permissions,
        }
    )
def _libelle_beneficiaire(personne):
    try:
        adherent = personne.adherent

        if adherent.statut == "ACTIF":
            return (
                f"{adherent.numero_adherent} - "
                f"{personne.nom} {personne.prenom}"
            )
    except Adherent.DoesNotExist:
        pass

    try:
        ayant_droit = personne.ayantdroit

        if ayant_droit.statut == "ACTIF":
            return (
                f"{ayant_droit.id_adherent.numero_adherent} - "
                f"{personne.nom} {personne.prenom} "
                f"(Ayant droit)"
            )
    except AyantDroit.DoesNotExist:
        pass

    return f"{personne.nom} {personne.prenom}"
def _generer_numero_demande():
    annee = timezone.now().year
    prefixe = f"DTP-{annee}-"

    numeros = (
        DemandeTp.objects
        .filter(numero_demande__startswith=prefixe)
        .values_list("numero_demande", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_demande = f"{prefixe}{prochain:04d}"

    while DemandeTp.objects.filter(
        numero_demande=numero_demande
    ).exists():
        prochain += 1
        numero_demande = f"{prefixe}{prochain:04d}"

    return numero_demande

def demande_tp_create(request):
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

    if "DEMANDE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer une demande."
        )
        return redirect("demandes_tp")

        personnes = Personne.objects.none()

    contrats = (
        Contrat.objects
        .filter(statut="ACTIF")
        .select_related("id_souscripteur")
        .order_by("numero_contrat")
    )

    id_contrat_preselectionne = request.GET.get(
        "id_contrat",
        ""
    ).strip()

    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects
            .filter(
                id_contrat=id_contrat_preselectionne,
                statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )
        # Contrat utilisé pour charger les bénéficiaires
    id_contrat_beneficiaires = id_contrat_preselectionne

    # Si aucun contrat n'est passé dans l'URL,
    # sélectionner automatiquement le premier contrat actif
    if not id_contrat_beneficiaires:
        premier_contrat = contrats.first()

        if premier_contrat:
            id_contrat_beneficiaires = str(
                premier_contrat.id_contrat
            )

    # En POST, utiliser le contrat sélectionné
    if request.method == "POST":
        id_contrat_beneficiaires = request.POST.get(
            "id_contrat",
            ""
        ).strip()

    personnes = Personne.objects.none()

    if id_contrat_beneficiaires:
        ids_adherents = (
            Adhesion.objects
            .filter(
                id_contrat=id_contrat_beneficiaires,
                statut="ACTIF"
            )
            .values_list(
                "id_adherent",
                flat=True
            )
        )

        ids_personnes_titulaires = (
            Adherent.objects
            .filter(
                id_adherent__in=ids_adherents,
                statut="ACTIF"
            )
            .values_list(
                "id_personne",
                flat=True
            )
        )

        ids_personnes_ayants_droit = (
            AyantDroit.objects
            .filter(
                id_adherent__in=ids_adherents,
                statut="ACTIF"
            )
            .values_list(
                "id_personne",
                flat=True
            )
        )

        ids_beneficiaires = list(
            ids_personnes_titulaires
        ) + list(
            ids_personnes_ayants_droit
        )

        personnes = (
            Personne.objects
            .filter(
                id_personne__in=ids_beneficiaires,
                statut="ACTIF"
            )
            .order_by(
                "nom",
                "prenom"
            )
        )

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    if request.method == "POST":
        form = DemandeTpForm(request.POST)
        form.fields["statut"].initial = "EN_ATTENTE"
        form.fields["statut"].widget = forms.HiddenInput()

        form.fields["id_personne_beneficiaire"].choices = [
            (
                str(p.id_personne),
                _libelle_beneficiaire(p)
            )
            for p in personnes
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

        form.fields["id_prestataire"].choices = [
            (
                str(p.id_prestataire),
                f"{p.code_prestataire} - {p.raison_sociale}"
            )
            for p in prestataires
        ]

        if form.is_valid():
            try:
                personne = Personne.objects.get(
                    id_personne=form.cleaned_data[
                        "id_personne_beneficiaire"
                    ],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.get(
                    id_contrat=form.cleaned_data["id_contrat"],
                    statut="ACTIF"
                )
                beneficiaire = personne

                titulaire_valide = (
                    Adhesion.objects
                    .filter(
                        id_contrat=contrat,
                        id_adherent__id_personne=beneficiaire,
                        statut="ACTIF"
                    )
                    .exists()
                )

                ayant_droit_valide = (
                    Adhesion.objects
                    .filter(
                        id_contrat=contrat,
                        id_adherent__ayantdroit__id_personne=beneficiaire,
                        statut="ACTIF"
                    )
                    .exists()
                )

                if not titulaire_valide and not ayant_droit_valide:
                    messages.error(
                        request,
                        "Le bénéficiaire sélectionné n'est pas rattaché "
                        "à une adhésion active de ce contrat."
                    )

                    return render(
                        request,
                        "core/demande_tp_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle demande",
                            "contrats": contrats,
                            "prestataires": prestataires,
                            "personnes": personnes,
                            "contrat_preselectionne": contrat_preselectionne,
                        }
                    )

                prestataire = Prestataire.objects.get(
                    id_prestataire=form.cleaned_data["id_prestataire"],
                    statut="ACTIF"
                )
                date_demande = timezone.now().date()

                convention_active = Convention.objects.filter(
                  id_prestataire=prestataire,
                  statut="ACTIF",
                  date_debut__lte=date_demande
                ).filter(
                  Q(date_fin__isnull=True) |
                  Q(date_fin__gte=date_demande)
                ).exists()

                if not convention_active:
                  messages.error(
                  request,
                  "Impossible de créer la demande TP : "
                  "aucune convention active avec ce prestataire "
                  "à la date de la demande."
                )

                  return render(
                  request,
                  "core/demande_tp_form.html",
                 {
                       "form": form,
                       "titre": "Nouvelle demande",
                        "contrats": contrats,
                        "prestataires": prestataires,
                        "personnes": personnes,
                        "contrat_preselectionne": contrat_preselectionne,
                 }
                )

                DemandeTp.objects.create(
                    numero_demande=_generer_numero_demande(),
                    id_personne_beneficiaire=personne,
                    id_contrat=contrat,
                    id_prestataire=prestataire,
                    date_demande=timezone.now(),
                    montant_demande=form.cleaned_data["montant_demande"],
                    statut="EN_ATTENTE",
                    motif_rejet=form.cleaned_data["motif_rejet"] or None,
                    date_decision=None,
                    utilisateur_creation=str(
                        request.session.get("id_utilisateur")
                    ),
                )

                messages.success(
                    request,
                    "Demande de tiers payant créée avec succès."
                )

                return redirect("demandes_tp")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = DemandeTpForm()
        form.fields["statut"].initial = "EN_ATTENTE"
        form.fields["statut"].widget = forms.HiddenInput()

        form.fields["id_personne_beneficiaire"].choices = [
            (
                str(p.id_personne),
                _libelle_beneficiaire(p)
            )
            for p in personnes
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

        if contrat_preselectionne:
            form.initial["id_contrat"] = str(
                contrat_preselectionne.id_contrat
            )

        form.fields["id_prestataire"].choices = [
            (
                str(p.id_prestataire),
                f"{p.code_prestataire} - {p.raison_sociale}"
            )
            for p in prestataires
        ]

    return render(
        request,
        "core/demande_tp_form.html",
        {
            "form": form,
            "titre": "Nouvelle demande de Tiers Payant",
            "contrat_preselectionne": contrat_preselectionne,
        }
    )
def demande_tp_detail_create(request, id_demande):
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
        .values_list("id_permission__code_permission", flat=True)
    )

    if "DEMANDE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter un détail à une demande."
        )
        return redirect("demandes_tp")

    try:
        demande = DemandeTp.objects.get(id_demande=id_demande)
    except DemandeTp.DoesNotExist:
        messages.error(request, "Demande de tiers payant introuvable.")
        return redirect("demandes_tp")

    # Récupérer l'acte parent de la demande (via le 1er détail s'il existe)
    # Sinon, on charge tous les actes actifs
    actes = Acte.objects.filter(statut="ACTIF").order_by("libelle")

    def _remplir_choices(form):
        """Remplit les choices des champs du formulaire."""
    def _remplir_choices(form):
        """Remplit les choices des champs du formulaire."""
        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
            for a in actes
        ]

        # Si un acte est déjà sélectionné, charger ses sous-actes
        id_acte_selectionne = None
        if request.method == "POST":
            id_acte_selectionne = request.POST.get("id_acte")
        else:
            id_acte_selectionne = request.GET.get("id_acte")

        if id_acte_selectionne:
            sous_actes = (
                SousActe.objects
                .filter(id_acte_id=id_acte_selectionne, statut="ACTIF")
                .order_by("libelle")
            )
            form.fields["id_sous_acte"].choices = [
                (str(s.id_sous_acte), f"{s.code_sous_acte} - {s.libelle}")
                for s in sous_actes
            ]
        else:
            form.fields["id_sous_acte"].choices = []

        # Prestataires : si un sous-acte est sélectionné, ne charger que ceux avec tarif
        id_sous_acte_selectionne = None
        if request.method == "POST":
            id_sous_acte_selectionne = request.POST.get("id_sous_acte")
        else:
            id_sous_acte_selectionne = request.GET.get("id_sous_acte")
            # Auto-sélection du premier sous-acte si aucun dans l'URL
            if not id_sous_acte_selectionne and id_acte_selectionne:
                premier = (
                    SousActe.objects
                    .filter(id_acte_id=id_acte_selectionne, statut="ACTIF")
                    .order_by("libelle")
                    .first()
                )
                if premier:
                    id_sous_acte_selectionne = str(premier.id_sous_acte)
        if id_sous_acte_selectionne:
            date_aujourdhui = timezone.now().date()
            tarifs = (
                TarifSousActe.objects
                .filter(
                    id_sous_acte_id=id_sous_acte_selectionne,
                    statut="ACTIF",
                    date_debut__lte=date_aujourdhui,
                )
                .filter(
                    Q(date_fin__isnull=True) | Q(date_fin__gte=date_aujourdhui)
                )
                .select_related("id_prestataire")
            )
            vus = set()
            prestataires_choices = []
            for t in tarifs:
                if t.id_prestataire_id in vus:
                    continue
                vus.add(t.id_prestataire_id)
                p = t.id_prestataire
                prestataires_choices.append(
                    (str(p.id_prestataire), f"{p.code_prestataire} - {p.raison_sociale}")
                )
            prestataires_choices.sort(key=lambda x: x[1])
            form.fields["id_prestataire"].choices = prestataires_choices
        else:
            form.fields["id_prestataire"].choices = []

    if request.method == "POST":
        form = DemandeTpDetailForm(request.POST)
        _remplir_choices(form)

        if form.is_valid():
            try:
                acte = Acte.objects.get(
                    id_acte=form.cleaned_data["id_acte"],
                    statut="ACTIF"
                )
                sous_acte = SousActe.objects.get(
                    id_sous_acte=form.cleaned_data["id_sous_acte"],
                    statut="ACTIF"
                )
                prestataire = Prestataire.objects.get(
                    id_prestataire=form.cleaned_data["id_prestataire"],
                    statut="ACTIF"
                )

                # Vérifier que l'acte est couvert par une garantie active du contrat
                acte_couvert = (
                    GarantieActe.objects
                    .filter(
                        id_acte=acte,
                        statut="ACTIF",
                        id_garantie__contratgarantie__id_contrat=demande.id_contrat,
                        id_garantie__contratgarantie__statut="ACTIF",
                    )
                    .exists()
                )

                if not acte_couvert:
                    messages.error(
                        request,
                        "Cet acte n'est pas couvert par une garantie active "
                        "du contrat de cette demande."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                        }
                    )

                # Récupérer le tarif applicable
                date_aujourdhui = timezone.now().date()
                tarif = (
                    TarifSousActe.objects
                    .filter(
                        id_sous_acte=sous_acte,
                        id_prestataire=prestataire,
                        statut="ACTIF",
                        date_debut__lte=date_aujourdhui,
                    )
                    .filter(
                        Q(date_fin__isnull=True) | Q(date_fin__gte=date_aujourdhui)
                    )
                    .order_by("-date_debut")
                    .first()
                )

                if not tarif:
                    messages.error(
                        request,
                        f"Aucun tarif actif pour ce sous-acte chez ce prestataire."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                        }
                    )

                quantite = form.cleaned_data["quantite"]
                montant_unitaire = tarif.montant
                montant_total = quantite * montant_unitaire

                # Créer le détail
                DemandeTpDetail.objects.create(
                    id_demande=demande,
                    id_acte=acte,
                    id_sous_acte=sous_acte,
                    quantite=quantite,
                    montant_unitaire=montant_unitaire,
                    montant_total=montant_total,
                    observation=form.cleaned_data["observation"] or None,
                )

                # Recalculer le montant total de la demande
                total_details = (
                    DemandeTpDetail.objects
                    .filter(id_demande=demande)
                    .aggregate(total=Sum("montant_total"))["total"]
                    or Decimal("0.00")
                )
                demande.montant_demande = total_details
                demande.save(update_fields=["montant_demande"])

                messages.success(
                    request,
                    "Acte ajouté à la demande avec succès."
                )
                return redirect(
                    "demande_tp_details",
                    id_demande=demande.id_demande
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de l'ajout de l'acte : {e}"
                )

    else:
        form = DemandeTpDetailForm(initial={
               "id_acte": request.GET.get("id_acte", ""),
               "id_sous_acte": request.GET.get("id_sous_acte", ""),
})
        _remplir_choices(form)

    return render(
        request,
        "core/demande_tp_detail_form.html",
        {
            "form": form,
            "demande": demande,
            "titre": "Ajouter un acte à la demande",
        }
    )
def demande_tp_document_create(request, id_demande):
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

    if "DOCUMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter une pièce jointe."
        )
        return redirect(
            "demande_tp_details",
            id_demande=id_demande
        )

    try:
        demande = DemandeTp.objects.get(
            id_demande=id_demande
        )
    except DemandeTp.DoesNotExist:
        messages.error(
            request,
            "Demande de tiers payant introuvable."
        )
        return redirect("demandes_tp")

    if request.method == "POST":
        form = DocumentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            try:
                with transaction.atomic():

                    fichier = form.cleaned_data["fichier"]

                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    type_document = (
                        form.cleaned_data["type_document"]
                        or getattr(
                            fichier,
                            "content_type",
                            None
                        )
                        or "INCONNU"
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=type_document,
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    DemandeTpDocument.objects.create(
                        id_demande=demande,
                        id_document=document,
                        type_document=type_document,
                        date_ajout=timezone.now(),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="DEPOT_DOCUMENT",
                        module="DOCUMENT",
                        table_cible="document",
                        id_enregistrement=document.id_document,
                        nouvelle_valeur=(
                            f"Fichier : {document.nom_fichier}, "
                            f"Type : {document.type_document}, "
                            f"Demande : {demande.numero_demande}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="RATTACHEMENT_DOCUMENT",
                        module="DEMANDE TP",
                        table_cible="demande_tp_document",
                        id_enregistrement=demande.id_demande,
                        nouvelle_valeur=(
                            f"Document : {document.nom_fichier}, "
                            f"Demande : {demande.numero_demande}"
                        ),
                        description=(
                            f"Rattachement du document "
                            f"{document.nom_fichier} "
                            f"à la demande {demande.numero_demande}"
                        ),
                    )

                messages.success(
                    request,
                    "Pièce jointe ajoutée à la demande avec succès."
                )

                return redirect(
                    "demande_tp_details",
                    id_demande=demande.id_demande
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de l'ajout de la pièce jointe : {e}"
                )

    else:
        form = DocumentForm()

    return render(
        request,
        "core/demande_tp_document_form.html",
        {
            "form": form,
            "demande": demande,
            "titre": "Ajouter une pièce jointe",
        }
    )
def _dates_periode_plafond(date_reference, periode):
    """
    Retourne la date de début et la date de fin
    de la période correspondant au plafond.
    """

    if periode == "JOUR":
        return date_reference, date_reference

    if periode == "MOIS":
        debut = date_reference.replace(day=1)

        if date_reference.month == 12:
            fin = date(date_reference.year + 1, 1, 1) - timedelta(days=1)
        else:
            fin = date(
                date_reference.year,
                date_reference.month + 1,
                1
            ) - timedelta(days=1)

        return debut, fin

    if periode == "TRIMESTRE":
        mois_debut = ((date_reference.month - 1) // 3) * 3 + 1

        debut = date(
            date_reference.year,
            mois_debut,
            1
        )

        if mois_debut == 10:
            fin = date(
                date_reference.year + 1,
                1,
                1
            ) - timedelta(days=1)
        else:
            fin = date(
                date_reference.year,
                mois_debut + 3,
                1
            ) - timedelta(days=1)

        return debut, fin

    if periode == "SEMESTRE":
        if date_reference.month <= 6:
            debut = date(date_reference.year, 1, 1)
            fin = date(date_reference.year, 7, 1) - timedelta(days=1)
        else:
            debut = date(date_reference.year, 7, 1)
            fin = date(
                date_reference.year + 1,
                1,
                1
            ) - timedelta(days=1)

        return debut, fin

    # ANNEE par défaut
    debut = date(date_reference.year, 1, 1)
    fin = date(
        date_reference.year + 1,
        1,
        1
    ) - timedelta(days=1)

    return debut, fin


def _get_adhesion_demande(demande):
    """
    Retrouve l'adhésion active correspondant
    à la personne bénéficiaire et au contrat de la demande.

    Cas possibles :
    - la personne est directement l'adhérent ;
    - la personne est un ayant droit.
    """

    personne = demande.id_personne_beneficiaire

    adherent = (
        Adherent.objects
        .filter(
            id_personne=personne,
            statut="ACTIF"
        )
        .first()
    )

    if not adherent:
        ayant_droit = (
            AyantDroit.objects
            .select_related("id_adherent")
            .filter(
                id_personne=personne,
                statut="ACTIF"
            )
            .first()
        )

        if ayant_droit:
            adherent = ayant_droit.id_adherent

    if not adherent:
        return None

    date_demande = demande.date_demande.date()

    return (
        Adhesion.objects
        .filter(
            id_adherent=adherent,
            id_contrat=demande.id_contrat,
            statut="ACTIF",
            date_debut__lte=date_demande,
        )
        .filter(
            Q(date_fin__isnull=True)
            | Q(date_fin__gte=date_demande)
        )
        .order_by("-date_debut")
        .first()
    )
def _appliquer_plafonds_demande(
    demande,
    detail,
    garantie_acte,
    montant_accorde,
):
    date_reference = demande.date_demande.date()

    plafonds = list(
        Plafond.objects
        .select_related(
            "id_garantie_acte",
            "id_garantie_acte__id_garantie",
            "id_garantie_acte__id_acte",
        )
        .filter(
            id_garantie_acte=garantie_acte,
            statut="ACTIF",
            date_debut__lte=date_reference,
        )
        .filter(
            Q(date_fin__isnull=True)
            | Q(date_fin__gte=date_reference)
        )
        .order_by(
            "-date_debut",
            "-id_plafond",
        )
    )

    # Aucun plafond configuré pour cet acte.
    if not plafonds:
        return montant_accorde, [], None, detail.quantite

    adhesion = None
    montant_courant = montant_accorde
    informations = []

    quantite_autorisee = detail.quantite or Decimal("0.00")

    for plafond in plafonds:

        # Pour un plafond adhérent, il faut retrouver
        # l'adhérent principal, y compris si le bénéficiaire
        # est un ayant droit.
        if plafond.niveau_application == "ADHERENT":

            if adhesion is None:
                adhesion = _get_adhesion_demande(demande)

            if not adhesion:
                return (
                    Decimal("0.00"),
                    informations,
                    (
                        "Impossible d'appliquer le plafond adhérent : "
                        "aucune adhésion active trouvée pour cette demande."
                    ),
                    Decimal("0.00"),
                )

        date_debut_periode, date_fin_periode = (
            _dates_periode_plafond(
                date_reference,
                plafond.periode,
            )
        )

        consommations = (
            Consommation.objects
            .filter(
                id_acte=garantie_acte.id_acte,
                id_garantie=garantie_acte.id_garantie,
                statut="VALIDEE",
                date_prestation__gte=date_debut_periode,
                date_prestation__lte=date_fin_periode,
            )
        )

        if plafond.niveau_application == "ADHERENT":

            consommations = consommations.filter(
                id_adhesion__id_adherent=adhesion.id_adherent
            )

        elif plafond.niveau_application == "PERSONNE":

            consommations = consommations.filter(
                id_personne_beneficiaire=(
                    demande.id_personne_beneficiaire
                )
            )

        elif plafond.niveau_application == "CONTRAT":

            consommations = consommations.filter(
                id_adhesion__id_contrat=demande.id_contrat
            )

        else:
            return (
                Decimal("0.00"),
                informations,
                (
                    f"Niveau d'application inconnu : "
                    f"{plafond.niveau_application}"
                ),
                Decimal("0.00"),
            )

        totaux = consommations.aggregate(
            montant_consomme=Sum("montant_prise_en_charge"),
            quantite_consommee=Sum("quantite"),
        )

        montant_consomme = (
            totaux["montant_consomme"]
            or Decimal("0.00")
        )

        quantite_consommee = (
            totaux["quantite_consommee"]
            or Decimal("0.00")
        )

        montant_avant = montant_courant
        quantite_avant = quantite_autorisee

        reste_montant = None
        reste_quantite = None

        # -------------------------------------------------
        # PLAFOND DE QUANTITE
        # -------------------------------------------------

        if (
            plafond.type_plafond in ("QUANTITE", "MIXTE")
            and plafond.quantite_max is not None
        ):

            reste_quantite = max(
                Decimal("0.00"),
                Decimal(plafond.quantite_max)
                - quantite_consommee,
            )

            quantite_autorisee = min(
                quantite_autorisee,
                reste_quantite,
            )

            # Recalcul financier sur la quantité réellement autorisée
            if detail.quantite and detail.quantite > 0:

                montant_unitaire = (
                    detail.montant_total
                    / detail.quantite
                )

                taux = (
                    garantie_acte.taux_prise_en_charge
                    or Decimal("0.00")
                )

                franchise = (
                    garantie_acte.franchise
                    or Decimal("0.00")
                )

                montant_couvert_quantite = (
                    montant_unitaire
                    * quantite_autorisee
                    * taux
                    / Decimal("100")
                )

                montant_courant = max(
                    Decimal("0.00"),
                    montant_couvert_quantite - franchise,
                )

        # -------------------------------------------------
        # PLAFOND DE MONTANT
        # -------------------------------------------------

        if (
            plafond.type_plafond in ("MONTANT", "MIXTE")
            and plafond.montant_max is not None
        ):

            reste_montant = max(
                Decimal("0.00"),
                Decimal(plafond.montant_max)
                - montant_consomme,
            )

            montant_courant = min(
                montant_courant,
                reste_montant,
            )

        informations.append({
            "plafond": plafond,
            "montant_consomme": montant_consomme,
            "quantite_consommee": quantite_consommee,
            "reste_montant": reste_montant,
            "reste_quantite": reste_quantite,
            "montant_avant": montant_avant,
            "montant_apres": montant_courant,
            "quantite_avant": quantite_avant,
            "quantite_apres": quantite_autorisee,
            "date_debut_periode": date_debut_periode,
            "date_fin_periode": date_fin_periode,
        })

    montant_courant = max(
        Decimal("0.00"),
        montant_courant,
    )

    return (
        montant_courant,
        informations,
        None,
        quantite_autorisee,
    )
def demande_tp_details(request, id_demande):
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

    if "DEMANDE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les dÃ©tails de la demande."
        )
        return redirect("demandes_tp")

    try:
        demande = DemandeTp.objects.get(
            id_demande=id_demande
        )
    except DemandeTp.DoesNotExist:
        messages.error(
            request,
            "Demande de tiers payant introuvable."
        )
        return redirect("demandes_tp")

    details = (
        DemandeTpDetail.objects
        .select_related("id_acte")
        .filter(id_demande=demande)
        .order_by("id_detail")
    )
    documents_lies = (
    DemandeTpDocument.objects
    .select_related(
        "id_document",
        "id_document__id_utilisateur",
    )
    .filter(id_demande=demande)
    .order_by("-date_ajout")
    )

    pec_details = (
        PriseEnChargeDetail.objects
        .select_related(
            "id_pec",
            "id_acte",
            "id_detail_demande",
        )
        .filter(id_pec__id_demande=demande)
        .order_by("id_detail_pec")
    )

    consommations_existantes = set(
        Consommation.objects
        .filter(id_detail_pec__in=pec_details)
        .values_list("id_detail_pec_id", flat=True)
    )

    montant_total = sum(
        detail.montant_total for detail in details
    )

    return render(
        request,
        "core/demande_tp_details.html",
        {
            "demande": demande,
            "details": details,
            "documents_lies": documents_lies,
            "pec_details": pec_details,
            "montant_total": montant_total,
            "permissions": permissions,
            "consommations_existantes": consommations_existantes,
        }
    ) 
def _generer_numero_pec():
    annee = timezone.now().year
    prefixe = f"PEC-{annee}-"

    numeros = (
        PriseEnCharge.objects
        .filter(numero_pec__startswith=prefixe)
        .values_list("numero_pec", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_pec = f"{prefixe}{prochain:04d}"

    while PriseEnCharge.objects.filter(
        numero_pec=numero_pec
    ).exists():
        prochain += 1
        numero_pec = f"{prefixe}{prochain:04d}"

    return numero_pec
  
def demande_tp_valider(request, id_demande):
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

    if "DEMANDE_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider une demande."
        )
        return redirect("demandes_tp")

    try:
        demande = (
            DemandeTp.objects
            .select_related(
                "id_personne_beneficiaire",
                "id_contrat",
                "id_prestataire",
            )
            .get(id_demande=id_demande)
        )
    except DemandeTp.DoesNotExist:
        messages.error(
            request,
            "Demande de tiers payant introuvable."
        )
        return redirect("demandes_tp")

    if demande.statut != "EN_ATTENTE":
        messages.error(
            request,
            "Cette demande n'est plus en attente de validation."
        )
        return redirect(
            "demande_tp_details",
            id_demande=demande.id_demande
        )

    details = list(
        DemandeTpDetail.objects
        .select_related("id_acte")
        .filter(id_demande=demande)
        .order_by("id_detail")
    )

    if not details:
        messages.error(
            request,
            "Impossible de valider une demande sans acte."
        )
        return redirect(
            "demande_tp_details",
            id_demande=demande.id_demande
        )

    calculs = []
    montant_accepte_total = Decimal("0.00")
    montant_rejete_total = Decimal("0.00")

    for detail in details:

        try:
            garantie_acte = (
                GarantieActe.objects
                .filter(
                    id_acte=detail.id_acte,
                    statut="ACTIF",
                    date_debut__lte=demande.date_demande.date(),
                    id_garantie__contratgarantie__id_contrat=demande.id_contrat,
                    id_garantie__contratgarantie__statut="ACTIF",
                )
                .filter(
                    Q(date_fin__isnull=True)
                    | Q(date_fin__gte=demande.date_demande.date())
                )
                .order_by("-date_debut")
                .first()
            )

            if not garantie_acte:
                calculs.append({
                    "detail": detail,
                    "garantie_acte": None,
                    "montant_demande": detail.montant_total,
                    "montant_accorde": Decimal("0.00"),
                    "montant_rejete": detail.montant_total,
                    "taux": Decimal("0.00"),
                    "franchise": Decimal("0.00"),
                    "erreur": "Aucune garantie active trouvée.",
                })

                montant_rejete_total += detail.montant_total
                continue

            taux = (
                garantie_acte.taux_prise_en_charge
                or Decimal("0.00")
            )

            franchise = (
                garantie_acte.franchise
                or Decimal("0.00")
            )

            montant_couvert = (
                detail.montant_total * taux / Decimal("100")
            )

            montant_accorde = max(
                Decimal("0.00"),
                montant_couvert - franchise
            )

            # -------------------------------------------------
            # APPLICATION DU PLAFOND
            # -------------------------------------------------

            montant_accorde_avant_plafond = montant_accorde

            (
                montant_accorde,
                plafond_details,
                erreur_plafond,
                quantite_autorisee,
            ) = _appliquer_plafonds_demande(
                demande=demande,
                detail=detail,
                garantie_acte=garantie_acte,
                montant_accorde=montant_accorde,
            )

            montant_rejete = max(
                Decimal("0.00"),
                detail.montant_total - montant_accorde
           
            )
            montant_accepte_total += montant_accorde
            montant_rejete_total += montant_rejete

            calculs.append({
    "detail": detail,
    "garantie_acte": garantie_acte,
    "montant_demande": detail.montant_total,
    "montant_accorde": montant_accorde,
    "montant_rejete": montant_rejete,
    "montant_accorde_avant_plafond": (
        montant_accorde_avant_plafond
    ),
    "taux": taux,
    "franchise": franchise,
    "plafond_details": plafond_details,
    "quantite_autorisee": quantite_autorisee,
    "erreur": erreur_plafond,
})
        except Exception as e:
            messages.error(
                request,
                f"Erreur lors du calcul : {e}"
            )
            return redirect(
                "demande_tp_details",
                id_demande=demande.id_demande
            )

    if request.method == "POST":

        if any(c["erreur"] for c in calculs):
            messages.error(
                request,
                "La demande ne peut pas Ãªtre validÃ©e car un acte "
                "n'a pas de garantie applicable."
            )
            return redirect(
                "demande_tp_valider",
                id_demande=demande.id_demande
            )

        try:
            numero_pec = _generer_numero_pec()

            pec = PriseEnCharge.objects.create(
                numero_pec=numero_pec,
                id_demande=demande,
                date_pec=timezone.now(),
                montant_demande=demande.montant_demande,
                montant_accepte=montant_accepte_total,
                montant_rejete=montant_rejete_total,
                statut="ACCEPTEE",
                date_expiration=timezone.now().date() + timedelta(days=30),
                utilisateur_validation=str(
                    request.session.get("id_utilisateur")
                ),
            )

            for calcul in calculs:

                detail = calcul["detail"]

                PriseEnChargeDetail.objects.create(
                    id_pec=pec,
                    id_detail_demande=detail,
                    id_acte=detail.id_acte,
                    quantite=calcul["quantite_autorisee"],
                    montant_demande=calcul["montant_demande"],
                    montant_accorde=calcul["montant_accorde"],
                    montant_rejete=calcul["montant_rejete"],
                    taux_applique=calcul["taux"],
                    franchise_appliquee=calcul["franchise"],
                    statut="ACCEPTEE",
                    motif_rejet=None,
                )

            demande.statut = "ACCEPTEE"
            demande.date_decision = timezone.now()
            demande.save()
            enregistrer_audit(
                request=request,
                type_action="VALIDATION",
                module="DEMANDES TP",
                table_cible="demande_tp",
                id_enregistrement=demande.id_demande,
                ancienne_valeur="Statut : EN_ATTENTE",
                nouvelle_valeur=(
                    f"Statut : ACCEPTEE, "
                    f"PEC : {pec.numero_pec}"
                ),
                description=(
                    f"Validation de la demande "
                    f"{demande.id_demande} "
                    f"et création de la PEC {pec.numero_pec}"
                ),
            )

            messages.success(
                request,
                f"Demande validÃ©e. PEC {pec.numero_pec} crÃ©Ã©e avec succÃ¨s."
            )

            return redirect(
                "demande_tp_details",
                id_demande=demande.id_demande
            )

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la crÃ©ation de la prise en charge : {e}"
            )

    return render(
        request,
        "core/demande_tp_valider.html",
        {
            "demande": demande,
            "details": details,
            "calculs": calculs,
            "montant_accepte_total": montant_accepte_total,
            "montant_rejete_total": montant_rejete_total,
        }
    )
def consommation_create(request, id_detail_pec):
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

    if "CONSOMMATION_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er une consommation."
        )
        return redirect("consommations")

    try:
        detail_pec = (
            PriseEnChargeDetail.objects
            .select_related(
                "id_pec",
                "id_acte",
                "id_detail_demande",
            )
            .get(id_detail_pec=id_detail_pec)
        )
    except PriseEnChargeDetail.DoesNotExist:
        messages.error(
            request,
            "DÃ©tail de prise en charge introuvable."
        )
        return redirect("demandes_tp")

    if detail_pec.id_pec.statut != "ACCEPTEE":
        messages.error(
            request,
            "La prise en charge doit Ãªtre acceptÃ©e."
        )
        return redirect(
            "demande_tp_details",
            id_demande=detail_pec.id_pec.id_demande_id
        )

    consommation_existante = (
        Consommation.objects
        .filter(id_detail_pec=detail_pec)
        .first()
    )

    if consommation_existante:
        messages.error(
            request,
            "Une consommation existe dÃ©jÃ  pour ce dÃ©tail de prise en charge."
        )
        return redirect("consommations")

    if request.method == "POST":
        form = ConsommationForm(request.POST)

        form.fields["id_detail_pec"].choices = [
            (
                str(detail_pec.id_detail_pec),
                f"{detail_pec.id_pec.numero_pec} - "
                f"{detail_pec.id_acte.code_acte} - "
                f"{detail_pec.id_acte.libelle}"
            )
        ]

        sous_actes = (
            SousActe.objects
            .filter(
                id_acte=detail_pec.id_acte,
                statut="ACTIF"
            )
            .order_by("libelle")
        )

        form.fields["id_sous_acte"].choices = [
            (
                str(sous_acte.id_sous_acte),
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        if form.is_valid():
            
            try:
                date_prestation = form.cleaned_data["date_prestation"]
                quantite = form.cleaned_data["quantite"]

                id_sous_acte = form.cleaned_data["id_sous_acte"]

                tarif = (
                    TarifSousActe.objects
                    .filter(
                        id_sous_acte_id=id_sous_acte,
                        id_prestataire_id=detail_pec.id_pec.id_demande.id_prestataire_id,
                        statut="ACTIF",
                        date_debut__lte=date_prestation,
                    )
                    .filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_prestation)
                    )
                    .order_by("-date_debut")
                    .first()
                )

                if not tarif:
                    messages.error(
                        request,
                        "Aucun tarif actif trouvé pour ce sous-acte, "
                        "ce prestataire et cette date."
                    )
                    return render(
                        request,
                        "core/consommation_form.html",
                        {
                            "form": form,
                            "detail_pec": detail_pec,
                            "titre": "Nouvelle consommation",
                        }
                    )

                if (
                   detail_pec.id_pec.date_expiration
                   and date_prestation > detail_pec.id_pec.date_expiration
                ):
                   messages.error(
                      request,
                      "La prise en charge est expirée à la date de la prestation."
                  )
                   return render(
                       request,
                       "core/consommation_form.html",
                       {
                           "form": form,
                           "detail_pec": detail_pec,
                           "titre": "Nouvelle consommation",
                       }
                  )

                if quantite <= 0:
                    messages.error(
                        request,
                        "La quantitÃ© doit Ãªtre supÃ©rieure Ã  zÃ©ro."
                    )
                    return render(
                        request,
                        "core/consommation_form.html",
                        {
                            "form": form,
                            "detail_pec": detail_pec,
                            "titre": "Nouvelle consommation",
                        }
                    )

                if quantite > detail_pec.quantite:
                    messages.error(
                        request,
                        "La quantitÃ© ne peut pas dÃ©passer la quantitÃ© autorisÃ©e dans la PEC."
                    )
                    return render(
                        request,
                        "core/consommation_form.html",
                        {
                            "form": form,
                            "detail_pec": detail_pec,
                            "titre": "Nouvelle consommation",
                        }
                    )

                                # 1. Récupérer le bénéficiaire
                personne_beneficiaire = (
                    detail_pec.id_pec.id_demande.id_personne_beneficiaire
                )

                # 2. Récupérer l'adhésion active du bénéficiaire
                adherent = (
                    Adherent.objects
                    .filter(id_personne=personne_beneficiaire)
                    .first()
                )

                adhesion = None

                if adherent:
                    adhesion = (
                        Adhesion.objects
                        .filter(
                            id_adherent=adherent,
                            id_contrat=detail_pec.id_pec.id_demande.id_contrat,
                            statut="ACTIF",
                        )
                        .first()
                    )

                if not adhesion:
                    ayant_droit = (
                        AyantDroit.objects
                        .filter(id_personne=personne_beneficiaire)
                        .first()
                    )

                    if ayant_droit:
                        adhesion = (
                            Adhesion.objects
                            .filter(
                                id_adherent=ayant_droit.id_adherent,
                                id_contrat=detail_pec.id_pec.id_demande.id_contrat,
                                statut="ACTIF",
                            )
                            .first()
                        )

                if not adhesion:
                    messages.error(
                        request,
                        "Aucune adhésion active trouvée pour ce bénéficiaire et ce contrat."
                    )
                    return render(
                        request,
                        "core/consommation_form.html",
                        {
                            "form": form,
                            "detail_pec": detail_pec,
                            "titre": "Nouvelle consommation",
                        }
                    )

                # 3. Récupérer la garantie liée au contrat et à l'acte
                contrat = detail_pec.id_pec.id_demande.id_contrat

                contrat_garantie = (
                    ContratGarantie.objects
                    .filter(
                        id_contrat=contrat,
                        statut="ACTIF",
                        id_garantie__garantieacte__id_acte=detail_pec.id_acte,
                        id_garantie__garantieacte__statut="ACTIF",
                    )
                    .select_related("id_garantie")
                    .first()
                )

                garantie = None
                garantie_acte = None

                if contrat_garantie:
                    garantie = contrat_garantie.id_garantie

                    garantie_acte = (
                        GarantieActe.objects
                        .filter(
                            id_garantie=garantie,
                            id_acte=detail_pec.id_acte,
                            statut="ACTIF",
                        )
                        .first()
                    )

                if not garantie or not garantie_acte:
                    messages.error(
                        request,
                        "Aucune garantie active correspondant au contrat et à l'acte."
                    )
                    return render(
                        request,
                        "core/consommation_form.html",
                        {
                            "form": form,
                            "detail_pec": detail_pec,
                            "titre": "Nouvelle consommation",
                        }
                    )

                # 4. Calculer le montant de base
                montant_base = tarif.montant * quantite

                # 5. Calculer le montant pris en charge avec le taux et la franchise
                taux = garantie_acte.taux_prise_en_charge or Decimal("0.00")
                franchise = garantie_acte.franchise or Decimal("0.00")

                montant_prise_en_charge = (
                    montant_base * (taux / Decimal("100"))
                ) - franchise

                # Le montant pris en charge ne peut pas être négatif
                if montant_prise_en_charge < 0:
                    montant_prise_en_charge = Decimal("0.00")

                # Le montant pris en charge ne peut pas dépasser le montant de base
                if montant_prise_en_charge > montant_base:
                    montant_prise_en_charge = montant_base

                # Le montant pris en charge ne peut pas dépasser le montant accordé dans la PEC
                if montant_prise_en_charge > detail_pec.montant_accorde:
                    montant_prise_en_charge = detail_pec.montant_accorde

                # 6. Calculer le reste à payer
                montant_reste = montant_base - montant_prise_en_charge

                if montant_prise_en_charge <= 0:
                    messages.error(
                        request,
                        "Impossible de créer une consommation : le montant pris en charge est nul."
                    )
                    return redirect("consommations")
                
                # 7. Créer la consommation
                consommation = Consommation.objects.create(
                    id_detail_pec=detail_pec,
                    id_personne_beneficiaire=personne_beneficiaire,
                    id_adhesion=adhesion,
                    id_acte=detail_pec.id_acte,
                    id_sous_acte_id=id_sous_acte,
                    id_garantie=garantie,
                    id_prestataire=detail_pec.id_pec.id_demande.id_prestataire,
                    date_prestation=date_prestation,
                    exercice=date_prestation.year,
                    quantite=quantite,
                    montant_base=montant_base,
                    montant_prise_en_charge=montant_prise_en_charge,
                    montant_reste=montant_reste,
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    f"Consommation {consommation.id_consommation} crÃ©Ã©e avec succÃ¨s."
                )

                return redirect("consommations")

            except Exception as e:
               
               messages.error(
                request,
                f"Erreur lors de la création de la consommation : {e}"
              )

    else:
        form = ConsommationForm()
        print("ERREUR CONSOMMATION :", repr(e))
        form.fields["id_detail_pec"].choices = [
            (
                str(detail_pec.id_detail_pec),
                f"{detail_pec.id_pec.numero_pec} - "
                f"{detail_pec.id_acte.code_acte} - "
                f"{detail_pec.id_acte.libelle}"
            )
        ]
        sous_actes = (
            SousActe.objects
            .filter(
                id_acte=detail_pec.id_acte,
                statut="ACTIF"
            )
            .order_by("libelle")
        )

        form.fields["id_sous_acte"].choices = [
            (
                str(sous_acte.id_sous_acte),
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

    return render(
        request,
        "core/consommation_form.html",
        {
            "form": form,
            "detail_pec": detail_pec,
            "titre": "Nouvelle consommation",
        }
    )
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

def types_prestation(request):
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
        .values_list("id_permission__code_permission", flat=True)
    )

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    types_prestation_liste = (
        TypePrestation.objects
        .all()
        .order_by("-id_type_prestation")
    )

    if recherche:
        types_prestation_liste = types_prestation_liste.filter(
            Q(code_type__icontains=recherche)
            | Q(libelle__icontains=recherche)
        )

    if statut:
        types_prestation_liste = types_prestation_liste.filter(
            statut=statut
        )

    return render(
        request,
        "core/types_prestation.html",
        {
            "types_prestation": types_prestation_liste,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )


def type_prestation_create(request):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    if request.method == "POST":
        form = TypePrestationForm(request.POST)

        if form.is_valid():
            try:
                TypePrestation.objects.create(
                    code_type=form.cleaned_data["code_type"].upper(),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"],
                    statut=form.cleaned_data["statut"],
                )
                messages.success(
                    request,
                    "Type de prestation créé avec succès."
                )
                return redirect("types_prestation")
            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = TypePrestationForm()

    return render(
        request,
        "core/types_prestation_form.html",
        {
            "form": form,
            "titre": "Nouveau type de prestation",
        }
    )


def type_prestation_modifier(request, id_type_prestation):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    type_prestation = get_object_or_404(
        TypePrestation,
        id_type_prestation=id_type_prestation
    )

    if request.method == "POST":
        form = TypePrestationForm(request.POST)

        if form.is_valid():
            type_prestation.code_type = form.cleaned_data["code_type"].upper()
            type_prestation.libelle = form.cleaned_data["libelle"]
            type_prestation.description = form.cleaned_data["description"]
            type_prestation.statut = form.cleaned_data["statut"]
            type_prestation.save()

            messages.success(
                request,
                "Type de prestation modifié avec succès."
            )
            return redirect("types_prestation")
    else:
        form = TypePrestationForm(initial={
            "code_type": type_prestation.code_type,
            "libelle": type_prestation.libelle,
            "description": type_prestation.description,
            "statut": type_prestation.statut,
        })

    return render(
        request,
        "core/types_prestation_form.html",
        {
            "form": form,
            "titre": "Modifier le type de prestation",
        }
    )


def type_prestation_radier(request, id_type_prestation):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    type_prestation = get_object_or_404(
        TypePrestation,
        id_type_prestation=id_type_prestation
    )
    type_prestation.statut = "INACTIF"
    type_prestation.save()

    messages.success(
        request,
        "Type de prestation désactivé avec succès."
    )
    return redirect("types_prestation")

def ajax_tarif_sous_acte(request):
    """Retourne le tarif d'un sous-acte pour un prestataire donné (AJAX)."""
    if not request.session.get("id_utilisateur"):
        return JsonResponse({"error": "Non authentifié"}, status=401)

    if request.method != "GET":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    id_sous_acte = request.GET.get("id_sous_acte")
    id_prestataire = request.GET.get("id_prestataire")

    if not id_sous_acte or not id_prestataire:
        return JsonResponse({"tarif": None})

    try:
        date_aujourdhui = timezone.now().date()

        tarif = (
            TarifSousActe.objects
            .filter(
                id_sous_acte_id=id_sous_acte,
                id_prestataire_id=id_prestataire,
                statut="ACTIF",
                date_debut__lte=date_aujourdhui,
            )
            .filter(
                Q(date_fin__isnull=True) | Q(date_fin__gte=date_aujourdhui)
            )
            .order_by("-date_debut")
            .first()
        )

        if not tarif:
            return JsonResponse({"tarif": None})

        return JsonResponse({"tarif": str(tarif.montant)})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def ajax_prestataires_par_sous_acte(request):
    """Retourne la liste des prestataires proposant un sous-acte (AJAX)."""
    if not request.session.get("id_utilisateur"):
        return JsonResponse({"error": "Non authentifié"}, status=401)

    if request.method != "GET":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    id_sous_acte = request.GET.get("id_sous_acte")

    if not id_sous_acte:
        return JsonResponse({"prestataires": []})

    try:
        date_aujourdhui = timezone.now().date()

        tarifs = (
            TarifSousActe.objects
            .filter(
                id_sous_acte_id=id_sous_acte,
                statut="ACTIF",
                date_debut__lte=date_aujourdhui,
            )
            .filter(
                Q(date_fin__isnull=True) | Q(date_fin__gte=date_aujourdhui)
            )
            .select_related("id_prestataire")
        )

        prestataires = []
        vus = set()

        for tarif in tarifs:
            p = tarif.id_prestataire
            if p.id_prestataire in vus:
                continue
            vus.add(p.id_prestataire)
            prestataires.append({
                "id": p.id_prestataire,
                "nom": f"{p.code_prestataire} - {p.raison_sociale}",
            })

        prestataires.sort(key=lambda x: x["nom"])

        return JsonResponse({"prestataires": prestataires})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def tarif_sous_acte_ajax(request, id_detail_pec):
    if not request.session.get("id_utilisateur"):
        return JsonResponse(
            {"error": "Non authentifié"},
            status=401
        )

    if request.method != "GET":
        return JsonResponse(
            {"error": "Méthode non autorisée"},
            status=405
        )

    id_sous_acte = request.GET.get("id_sous_acte")
    date_prestation = request.GET.get("date_prestation")

    if not id_sous_acte or not date_prestation:
        return JsonResponse(
            {"tarif": None}
        )

    try:
        detail_pec = (
            PriseEnChargeDetail.objects
            .select_related("id_pec__id_demande")
            .get(id_detail_pec=id_detail_pec)
        )

        from datetime import datetime

        date_prestation = datetime.strptime(
            date_prestation,
            "%Y-%m-%d"
        ).date()

        tarif = (
            TarifSousActe.objects
            .filter(
                id_sous_acte_id=id_sous_acte,
                id_prestataire_id=detail_pec.id_pec.id_demande.id_prestataire_id,
                statut="ACTIF",
                date_debut__lte=date_prestation,
            )
            .filter(
                Q(date_fin__isnull=True) |
                Q(date_fin__gte=date_prestation)
            )
            .order_by("-date_debut")
            .first()
        )

        if not tarif:
            return JsonResponse(
                {"tarif": None}
            )

        return JsonResponse(
            {
                "tarif": str(tarif.montant),
            }
        )

    except (
        PriseEnChargeDetail.DoesNotExist,
        ValueError,
        TypeError,
    ):
        return JsonResponse(
            {"tarif": None}
        )    

def consommations(request):
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

    if "CONSOMMATION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les consommations."
        )
        return redirect("accueil")

    consommations = (
        Consommation.objects
        .select_related(
            "id_detail_pec",
            "id_personne_beneficiaire",
            "id_adhesion",
            "id_acte",
            "id_garantie",
            "id_prestataire",
        )
        .order_by("-id_consommation")
    )

    return render(
        request,
        "core/consommations.html",
        {
            "consommations": consommations,
            "permissions": permissions,
        }
    )
def consommation_valider(request, id_consommation):
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

    if "CONSOMMATION_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider une consommation."
        )
        return redirect("consommations")

    try:
        consommation = Consommation.objects.get(
            id_consommation=id_consommation
        )
    except Consommation.DoesNotExist:
        messages.error(
            request,
            "Consommation introuvable."
        )
        return redirect("consommations")

    if request.method == "POST":

        if consommation.statut != "A_TRAITER":
            messages.error(
                request,
                "Cette consommation a dÃ©jÃ  Ã©tÃ© traitÃ©e."
            )
            return redirect("consommations")

        consommation.statut = "VALIDEE"
        consommation.date_validation = timezone.now()
        consommation.save()

        messages.success(
            request,
            "Consommation validÃ©e avec succÃ¨s."
        )

    return redirect("consommations")
def consommation_annuler(request, id_consommation):
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

    if "CONSOMMATION_CANCEL" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'annuler une consommation."
        )
        return redirect("consommations")

    try:
        consommation = Consommation.objects.get(
            id_consommation=id_consommation
        )
    except Consommation.DoesNotExist:
        messages.error(
            request,
            "Consommation introuvable."
        )
        return redirect("consommations")

    if request.method == "POST":

        if consommation.statut != "A_TRAITER":
            messages.error(
                request,
                "Cette consommation a dÃ©jÃ  Ã©tÃ© traitÃ©e."
            )
            return redirect("consommations")

        consommation.statut = "ANNULEE"
        consommation.date_validation = timezone.now()
        consommation.save()

        messages.success(
            request,
            "Consommation annulÃ©e avec succÃ¨s."
        )

    return redirect("consommations")

def _generer_numero_facture():
    annee = timezone.now().year
    prefixe = f"FAC-{annee}-"

    numeros = (
        Facture.objects
        .filter(numero_facture__startswith=prefixe)
        .values_list("numero_facture", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_facture = f"{prefixe}{prochain:04d}"

    while Facture.objects.filter(
        numero_facture=numero_facture
    ).exists():
        prochain += 1
        numero_facture = f"{prefixe}{prochain:04d}"

    return numero_facture

def facture_create(request):
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

    if "FACTURE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er une facture."
        )
        return redirect("factures")

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    consommations = (
        Consommation.objects
        .filter(statut="VALIDEE")
        .select_related(
            "id_prestataire",
            "id_acte",
            "id_personne_beneficiaire",
        )
        .order_by("date_prestation", "id_consommation")
    )

    if request.method == "POST":
        form = FactureForm(request.POST)

        form.fields["id_prestataire"].choices = [
            (
                str(p.id_prestataire),
                f"{p.code_prestataire} - {p.raison_sociale}"
            )
            for p in prestataires
        ]

        if form.is_valid():
            try:
                id_prestataire = form.cleaned_data["id_prestataire"]

                consommations_prestataire = [
                    c for c in consommations
                    if c.id_prestataire_id == int(id_prestataire)
                ]

                consommations_deja_facturees = set(
                    DetailFacture.objects
                    .values_list("id_consommation_id", flat=True)
                )

                consommations_prestataire = [
                c for c in consommations_prestataire
                if (
        c.id_consommation not in consommations_deja_facturees
        and c.montant_prise_en_charge > 0
                )
        ]
                if not consommations_prestataire:
                    messages.error(
                        request,
                        "Aucune consommation avec un montant pris en charge supérieur à 0 n'est disponible pour ce prestataire."
                    )
                    return render(
                        request,
                        "core/facture_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle facture",
                            "consommations": consommations,
                        }
                    )

                prestataire = Prestataire.objects.get(
                    id_prestataire=id_prestataire,
                    statut="ACTIF",
                )

                montant_total = sum(
                    c.montant_base
                    for c in consommations_prestataire
                )

                montant_valide = sum(
                    c.montant_prise_en_charge
                    for c in consommations_prestataire
                )

                montant_rejete = sum(
                    c.montant_reste
                    for c in consommations_prestataire
                )

                facture = Facture.objects.create(
                    id_prestataire=prestataire,
                    numero_facture=_generer_numero_facture(),
                    date_facture=form.cleaned_data["date_facture"],
                    date_reception=form.cleaned_data["date_reception"],
                    montant_total=montant_total,
                    montant_valide=montant_valide,
                    montant_rejete=montant_rejete,
                    statut="EN_ATTENTE",
                    date_validation=None,
                    utilisateur_validation=None,
                    observation=form.cleaned_data["observation"] or None,
                )

                for consommation in consommations_prestataire:
                    DetailFacture.objects.create(
                        id_facture=facture,
                        id_consommation=consommation,
                        id_acte=consommation.id_acte,
                        quantite=consommation.quantite,
                        montant_unitaire=(
                            consommation.montant_base
                            / consommation.quantite
                        ),
                        montant_total=consommation.montant_base,
                        montant_valide=consommation.montant_prise_en_charge,
                        montant_rejete=consommation.montant_reste,
                        statut="EN_ATTENTE",
                        id_motif_rejet=None,
                    )

                messages.success(
                    request,
                    f"Facture {facture.numero_facture} crÃ©Ã©e avec succÃ¨s."
                )

                return redirect("factures")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation de la facture : {e}"
                )

    else:
        form = FactureForm()

        form.fields["id_prestataire"].choices = [
            (
                str(p.id_prestataire),
                f"{p.code_prestataire} - {p.raison_sociale}"
            )
            for p in prestataires
        ]

    return render(
        request,
        "core/facture_form.html",
        {
            "form": form,
            "titre": "Nouvelle facture",
            "consommations": consommations,
        }
    )
def factures(request):
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

    if "FACTURE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les factures."
        )
        return redirect("accueil")

    factures = (

        Facture.objects
        .select_related("id_prestataire")
        .order_by("-id_facture")
    )

    return render(
        request,
        "core/factures.html",
        {
            "factures": factures,
            "permissions": permissions,
        }
    )
def facture_valider(request, id_facture):
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

    if "FACTURE_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider une facture."
        )
        return redirect("factures")

    try:
        facture = Facture.objects.get(
            id_facture=id_facture
        )
    except Facture.DoesNotExist:
        messages.error(
            request,
            "Facture introuvable."
        )
        return redirect("factures")

    if request.method == "POST":

        if facture.statut != "EN_ATTENTE":
            messages.error(
                request,
                "Cette facture a dÃ©jÃ  Ã©tÃ© traitÃ©e."
            )
            return redirect("factures")

        facture.statut = "VALIDEE"
        facture.date_validation = timezone.now()
        facture.utilisateur_validation = str(
            request.session.get("id_utilisateur")
        )
        facture.save()

        # Validation des détails de la facture
        DetailFacture.objects.filter(
            id_facture=facture
        ).update(
            statut="VALIDEE"
        )

        messages.success(
            request,
            "Facture validÃ©e avec succÃ¨s."
        )

    return redirect("factures")
def facture_detail(request, id_facture):
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

    if "FACTURE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter le dÃ©tail de la facture."
        )
        return redirect("factures")

    try:
        facture = (
            Facture.objects
            .select_related("id_prestataire")
            .get(id_facture=id_facture)
        )
    except Facture.DoesNotExist:
        messages.error(
            request,
            "Facture introuvable."
        )
        return redirect("factures")

    details = (
        DetailFacture.objects
        .select_related(
            "id_consommation",
            "id_acte",
        )
        .filter(id_facture=facture)
        .order_by("id_detail_facture")
    )

    return render(
        request,
        "core/facture_detail.html",
        {
            "facture": facture,
            "details": details,
        }
    )

def _generer_numero_reglement():
    annee = timezone.now().year
    prefixe = f"REG-{annee}-"

    numeros = (
        Reglement.objects
        .filter(numero_reglement__startswith=prefixe)
        .values_list("numero_reglement", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_reglement = f"{prefixe}{prochain:04d}"

    while Reglement.objects.filter(
        numero_reglement=numero_reglement
    ).exists():
        prochain += 1
        numero_reglement = f"{prefixe}{prochain:04d}"

    return numero_reglement



def _generer_reference_reglement(mode_reglement):
    """Génère une référence unique pour un règlement selon son mode."""
    annee = timezone.now().year

    prefixes = {
        "VIREMENT": f"VIR-{annee}-",
        "CHEQUE": f"CHQ-{annee}-",
        "ESPECES": f"ESP-{annee}-",
    }

    prefixe = prefixes.get(mode_reglement, f"REF-{annee}-")

    # Récupère toutes les références existantes pour ce préfixe
    references = (
        Reglement.objects
        .filter(reference_reglement__startswith=prefixe)
        .values_list("reference_reglement", flat=True)
    )

    valeurs = []
    for ref in references:
        try:
            valeurs.append(int(ref.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    reference = f"{prefixe}{prochain:04d}"

    # Vérifie l'unicité
    while Reglement.objects.filter(
        reference_reglement=reference
    ).exists():
        prochain += 1
        reference = f"{prefixe}{prochain:04d}"

    return reference

def reglement_create(request):
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

    if "REGLEMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un règlement."
        )
        return redirect("reglements")

    factures = (
        Facture.objects
        .filter(statut="VALIDEE")
        .select_related("id_prestataire")
        .order_by("-id_facture")
    )

    if request.method == "POST":
        form = ReglementForm(request.POST)

        form.fields["id_facture"].choices = [
            (
                str(f.id_facture),
                f"{f.numero_facture} - {f.id_prestataire.raison_sociale} - "
                f"{f.montant_valide} DA"
            )
            for f in factures
        ]

        if form.is_valid():
            try:
                facture = Facture.objects.get(
                    id_facture=form.cleaned_data["id_facture"],
                    statut="VALIDEE",
                )

                montant = form.cleaned_data["montant"]

                montant_deja_regle = (
                    Reglement.objects
                    .filter(
                        id_facture=facture,
                        statut="VALIDEE"
                    )
                    .aggregate(total=Sum("montant"))["total"]
                    or 0
                )

                reste_a_payer = facture.montant_valide - montant_deja_regle

                if reste_a_payer <= 0:
                    messages.error(
                        request,
                        "Cette facture est déjà entièrement réglée."
                    )
                    return render(
                        request,
                        "core/reglement_form.html",
                        {
                            "form": form,
                            "titre": "Nouveau règlement",
                            "factures": factures,
                        }
                    )

                if montant > reste_a_payer:
                    messages.error(
                        request,
                        f"Le montant du règlement ne peut pas dépasser "
                        f"le reste à payer de {reste_a_payer} DA."
                    )
                    return render(
                        request,
                        "core/reglement_form.html",
                        {
                            "form": form,
                            "titre": "Nouveau règlement",
                            "factures": factures,
                        }
                    )

                mode = form.cleaned_data["mode_reglement"]

                Reglement.objects.create(
                    id_facture=facture,
                    numero_reglement=_generer_numero_reglement(),
                    date_reglement=form.cleaned_data["date_reglement"],
                    montant=montant,
                    mode_reglement=mode,
                    reference_reglement=_generer_reference_reglement(mode),
                    statut="EN_ATTENTE",
                    observation=form.cleaned_data["observation"] or None,
                )

                messages.success(
                    request,
                    "Règlement créé avec succès."
                )

                return redirect("reglements")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création du règlement : {e}"
                )

    else:
        form = ReglementForm()

        form.fields["id_facture"].choices = [
            (
                str(f.id_facture),
                f"{f.numero_facture} - {f.id_prestataire.raison_sociale} - "
                f"{f.montant_valide} DA"
            )
            for f in factures
        ]

    return render(
        request,
        "core/reglement_form.html",
        {
            "form": form,
            "titre": "Nouveau règlement",
            "factures": factures,
        }
    )


def reglements(request):
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

    if "REGLEMENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les rÃ¨glements."
        )
        return redirect("accueil")

    reglements = (
        Reglement.objects
        .select_related(
            "id_facture",
            "id_facture__id_prestataire",
        )
        .order_by("-id_reglement")
    )

    for reglement in reglements:
        montant_deja_regle = (
            Reglement.objects
            .filter(
                id_facture=reglement.id_facture,
                statut="VALIDEE"
            )
            .aggregate(total=Sum("montant"))["total"]
            or Decimal("0")
        )

        reglement.montant_total_facture = reglement.id_facture.montant_valide
        reglement.montant_deja_regle = montant_deja_regle
        reglement.reste_a_payer = (
            reglement.id_facture.montant_valide - montant_deja_regle
        )

    return render(
        request,
        "core/reglements.html",
        {
            "reglements": reglements,
            "permissions": permissions,
        }
    )
def reglement_valider(request, id_reglement):
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
    

    if "REGLEMENT_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider un rÃ¨glement."
        )
        return redirect("reglements")

    try:
        reglement = Reglement.objects.get(
            id_reglement=id_reglement
        )
    except Reglement.DoesNotExist:
        messages.error(
            request,
            "RÃ¨glement introuvable."
        )
        return redirect("reglements")

    if request.method == "POST":

        if reglement.statut != "EN_ATTENTE":
            messages.error(
                request,
                "Ce rÃ¨glement a dÃ©jÃ  Ã©tÃ© traitÃ©."
            )
            return redirect("reglements")

        reglement.statut = "VALIDEE"
        reglement.save()

        facture = reglement.id_facture

        montant_total_regle = (
              Reglement.objects
              .filter(
                  id_facture=facture,
                  statut="VALIDEE"
              )
              .aggregate(total=Sum("montant"))["total"]
              or 0
          )

        # Mettre à jour le statut de la facture selon le montant réglé
        if montant_total_regle >= facture.montant_valide:
            facture.statut = "PAYEE"
        elif montant_total_regle > 0:
            facture.statut = "PARTIELLEMENT_PAYEE"

        facture.save()

        messages.success(
            request,
            f"Règlement validé avec succès. "
            f"Facture {facture.numero_facture} : {facture.statut}."
        )

    return redirect("reglements")


def reglement_detail(request, id_reglement):
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

    if "REGLEMENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter le dÃ©tail du rÃ¨glement."
        )
        return redirect("reglements")

    try:
        reglement = (
            Reglement.objects
            .select_related(
                "id_facture",
                "id_facture__id_prestataire",
            )
            .get(id_reglement=id_reglement)
        )
    except Reglement.DoesNotExist:
        messages.error(
            request,
            "RÃ¨glement introuvable."
        )
        return redirect("reglements")

    return render(
        request,
        "core/reglement_detail.html",
        {
            "reglement": reglement,
        }
    )

def _generer_numero_recours():
    annee = timezone.now().year
    prefixe = f"REC-{annee}-"

    numeros = (
        Recours.objects
        .filter(numero_recours__startswith=prefixe)
        .values_list("numero_recours", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_recours = f"{prefixe}{prochain:04d}"

    while Recours.objects.filter(
        numero_recours=numero_recours
    ).exists():
        prochain += 1
        numero_recours = f"{prefixe}{prochain:04d}"

    return numero_recours

def recours(request):
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

    if "RECOURS_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les recours."
        )
        return redirect("accueil")

    recours_list = (
        Recours.objects
        .select_related("id_personne")
        .all()
        .order_by("-id_recours")
    )

    return render(
        request,
        "core/recours.html",
        {
            "recours": recours_list,
            "permissions": permissions,
        }
    )

def recours_detail(request, id_recours):
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

    if "RECOURS_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les recours."
        )
        return redirect("recours")

    try:
        recours_obj = (
            Recours.objects
            .select_related("id_personne")
            .get(id_recours=id_recours)
        )
    except Recours.DoesNotExist:
        messages.error(
            request,
            "Recours introuvable."
        )
        return redirect("recours")

    documents_lies = (
        RecoursDocument.objects
        .select_related(
            "id_document",
            "id_document__id_utilisateur",
        )
        .filter(id_recours=recours_obj)
        .order_by("-date_ajout")
    )

    return render(
        request,
        "core/recours_detail.html",
        {
            "recours": recours_obj,
            "documents_lies": documents_lies,
            "permissions": permissions,
        }
    )

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
        }
    )
def recours_create(request):
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

    if "RECOURS_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er un recours."
        )
        return redirect("recours")

    if request.method == "POST":
        form = RecoursForm(request.POST)

        if form.is_valid():
            recours_obj = form.save(commit=False)

            recours_obj.numero_recours = _generer_numero_recours()

            recours_obj.statut = "EN_ATTENTE"

            recours_obj.utilisateur_creation = (
                request.session.get("nom_utilisateur")
            )

            recours_obj.save()

            messages.success(
                request,
                "Le recours a Ã©tÃ© crÃ©Ã© avec succÃ¨s."
            )

            return redirect("recours")

    else:
        form = RecoursForm()

    return render(
        request,
        "core/recours_form.html",
        {
            "form": form,
            "permissions": permissions,
        }
    )
def recours_document_create(request, id_recours):
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

    if "DOCUMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter une pièce jointe."
        )
        return redirect(
            "recours_detail",
            id_recours=id_recours
        )

    try:
        recours_obj = Recours.objects.get(
            id_recours=id_recours
        )
    except Recours.DoesNotExist:
        messages.error(
            request,
            "Recours introuvable."
        )
        return redirect("recours")

    if request.method == "POST":

        form = DocumentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            try:
                with transaction.atomic():

                    fichier = form.cleaned_data["fichier"]

                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    type_document = (
                        form.cleaned_data["type_document"]
                        or getattr(
                            fichier,
                            "content_type",
                            None
                        )
                        or "INCONNU"
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=type_document,
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    RecoursDocument.objects.create(
                        id_recours=recours_obj,
                        id_document=document,
                        type_document=type_document,
                        date_ajout=timezone.now(),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="DEPOT_DOCUMENT",
                        module="DOCUMENT",
                        table_cible="document",
                        id_enregistrement=document.id_document,
                        nouvelle_valeur=(
                            f"Fichier : {document.nom_fichier}, "
                            f"Type : {document.type_document}, "
                            f"Recours : {recours_obj.numero_recours}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="RATTACHEMENT_DOCUMENT",
                        module="RECOURS",
                        table_cible="recours_document",
                        id_enregistrement=recours_obj.id_recours,
                        nouvelle_valeur=(
                            f"Document : {document.nom_fichier}, "
                            f"Recours : {recours_obj.numero_recours}"
                        ),
                        description=(
                            f"Rattachement du document "
                            f"{document.nom_fichier} au recours "
                            f"{recours_obj.numero_recours}"
                        ),
                    )

                messages.success(
                    request,
                    "Le document a été ajouté au recours avec succès."
                )

                return redirect(
                    "recours_detail",
                    id_recours=id_recours
                )

            except Exception as e:

                messages.error(
                    request,
                    f"Erreur lors du dépôt du document : {str(e)}"
                )

    else:

        form = DocumentForm()

    return render(
    request,
    "core/recours_document_form.html",
    {
        "form": form,
        "recours": recours_obj,
        "permissions": permissions,
    }
)

def recours_traiter(request, id_recours):
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

    if "RECOURS_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de traiter les recours."
        )
        return redirect("recours")

    try:
        recours_obj = Recours.objects.get(id_recours=id_recours)
    except Recours.DoesNotExist:
        messages.error(request, "Recours introuvable.")
        return redirect("recours")

    if recours_obj.statut != "EN_ATTENTE":
        messages.error(
            request,
            "Ce recours a déjà été traité."
        )
        return redirect("recours")

    if request.method == "POST":
        form = DecisionRecoursForm(request.POST)

        if form.is_valid():
            decision = form.save(commit=False)

            decision.id_recours = recours_obj
            decision.utilisateur_decision = (
                request.session.get("nom_utilisateur")
            )

            decision.save()

            if decision.type_decision == "ACCEPTEE":
             recours_obj.statut = "ACCEPTEE"

            elif decision.type_decision == "REJETEE":
             recours_obj.statut = "REJETEE"

            elif decision.type_decision == "ACCEPTEE_PARTIELLEMENT":
             recours_obj.statut = "ACCEPTEE_PARTIELLEMENT"

            recours_obj.date_cloture = timezone.now().date()
            recours_obj.observation = decision.observation
            recours_obj.save()

            messages.success(
                request,
                "La dÃ©cision du recours a Ã©tÃ© enregistrÃ©e."
            )

            return redirect("recours")

    else:
        form = DecisionRecoursForm(
            initial={
                "date_decision": timezone.now().date()
            }
        )

    return render(
        request,
        "core/recours_traiter.html",
        {
            "recours": recours_obj,
            "form": form,
            "permissions": permissions,
        }
    )

def prises_en_charge(request):
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

    if "DEMANDE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les prises en charge."
        )
        return redirect("accueil")

    prises = (
        PriseEnCharge.objects
        .select_related(
            "id_demande",
            "id_demande__id_personne_beneficiaire",
            "id_demande__id_contrat",
        )
        .all()
        .order_by("-id_pec")
    )

    return render(
        request,
        "core/prises_en_charge.html",
        {
            "prises": prises,
            "permissions": permissions,
        }
    )
def prise_en_charge_details(request, id_pec):
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

    if "DEMANDE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les détails de la prise en charge."
        )
        return redirect("prises_en_charge")

    try:
        pec = (
            PriseEnCharge.objects
            .select_related(
                "id_demande",
                "id_demande__id_personne_beneficiaire",
                "id_demande__id_contrat",
                "id_demande__id_prestataire",
            )
            .get(id_pec=id_pec)
        )
    except PriseEnCharge.DoesNotExist:
        messages.error(
            request,
            "Prise en charge introuvable."
        )
        return redirect("prises_en_charge")

    details = (
        PriseEnChargeDetail.objects
        .select_related(
            "id_pec",
            "id_detail_demande",
            "id_acte",
        )
        .filter(id_pec=pec)
        .order_by("id_detail_pec")
    )

    return render(
        request,
        "core/prise_en_charge_details.html",
        {
            "pec": pec,
            "details": details,
            "permissions": permissions,
        }
    )

def adherent_import_excel(request):

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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'importer des adhérents."
        )
        return redirect("adherents")

    if request.method == "POST":

        form = ImportAdherentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            try:

                import openpyxl

                fichier = form.cleaned_data["fichier"]

                if not fichier.name.lower().endswith(".xlsx"):
                    messages.error(
                        request,
                        "Veuillez sélectionner un fichier Excel au format .xlsx."
                    )
                    return redirect("adherent_import_excel")

                workbook = openpyxl.load_workbook(
                    fichier,
                    data_only=True
                )

                feuille = workbook.active

                nombre_importes = 0
                erreurs = []

                with transaction.atomic():

                    for numero_ligne, ligne in enumerate(
                        feuille.iter_rows(
                            min_row=2,
                            values_only=True
                        ),
                        start=2
                    ):

                        if not any(ligne):
                            continue

                        nom = ligne[0]
                        prenom = ligne[1]
                        date_naissance = ligne[2]
                        sexe = ligne[3]
                        adresse = ligne[4]
                        telephone = ligne[5]
                        email = ligne[6]
                        date_adhesion = ligne[7]

                        if not nom or not prenom:

                            erreurs.append(
                                f"Ligne {numero_ligne} : "
                                "Nom ou prénom manquant."
                            )

                            continue

                        # Vérification doublon
                        doublon = (
                            Adherent.objects
                            .filter(
                                statut="ACTIF",
                                id_personne__nom__iexact=str(nom).strip(),
                                id_personne__prenom__iexact=str(prenom).strip(),
                                id_personne__date_naissance=date_naissance,
                            )
                            .first()
                        )

                        if doublon:

                            erreurs.append(
                                f"Ligne {numero_ligne} : "
                                f"Cet adhérent existe déjà "
                                f"({doublon.numero_adherent})."
                            )

                            continue

                        # Création de la personne
                        personne = Personne.objects.create(

                            numero_personne=_generer_numero_personne(),

                            nom=str(nom).strip(),

                            prenom=str(prenom).strip(),

                            date_naissance=date_naissance,

                            sexe=(
                                str(sexe).strip()
                                if sexe
                                else None
                            ),

                            adresse=(
                                str(adresse).strip()
                                if adresse
                                else None
                            ),

                            telephone=(
                                str(telephone).strip()
                                if telephone
                                else None
                            ),

                            email=(
                                str(email).strip()
                                if email
                                else None
                            ),

                            statut="ACTIF",

                            date_creation=timezone.now(),

                            date_modification=None,
                        )

                        # Création de l'adhérent
                        adherent = Adherent.objects.create(

                            id_personne=personne,

                            numero_adherent=_generer_numero_adherent(),

                            date_creation=timezone.now(),

                            statut="ACTIF",

                            date_adhesion=date_adhesion,

                            date_radiation=None,
                        )

                        # Audit
                        enregistrer_audit(
                            request=request,
                            type_action="IMPORTATION",
                            module="ADHERENTS",
                            table_cible="adherent",
                            id_enregistrement=adherent.id_adherent,
                            nouvelle_valeur=(
                                f"Import Excel - "
                                f"Adhérent : {adherent.numero_adherent}"
                            ),
                            description=(
                                f"Importation de l'adhérent "
                                f"{adherent.numero_adherent}"
                            ),
                        )

                        nombre_importes += 1


                if nombre_importes > 0:

                    messages.success(
                        request,
                        f"{nombre_importes} adhérent(s) importé(s) "
                        "avec succès."
                    )

                if erreurs:

                    for erreur in erreurs[:10]:

                        messages.warning(
                            request,
                            erreur
                        )

                    if len(erreurs) > 10:

                        messages.warning(
                            request,
                            f"{len(erreurs) - 10} autre(s) erreur(s)."
                        )

                return redirect("adherents")

            except Exception as e:

                messages.error(
                    request,
                    f"Erreur lors de l'importation : {str(e)}"
                )

    else:

        form = ImportAdherentForm()

    return render(
        request,
        "core/adherent_import_excel.html",
        {
            "form": form,
        }
    )
def adherent_export_excel(request):

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

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les adhérents."
        )
        return redirect("adherents")

    import openpyxl

    from openpyxl.styles import Font
    from django.http import HttpResponse


    adherents_list = (
        Adherent.objects
        .select_related("id_personne")
        .order_by("numero_adherent")
    )


    workbook = openpyxl.Workbook()

    feuille = workbook.active

    feuille.title = "Adherents"


    entetes = [

        "Numéro adhérent",

        "Numéro personne",

        "Nom",

        "Prénom",

        "Date de naissance",

        "Sexe",

        "Adresse",

        "Téléphone",

        "Email",

        "Date adhésion",

        "Statut",

    ]


    feuille.append(entetes)


    for cellule in feuille[1]:

        cellule.font = Font(bold=True)


    for adherent in adherents_list:

        personne = adherent.id_personne

        feuille.append([

            adherent.numero_adherent,

            personne.numero_personne,

            personne.nom,

            personne.prenom,

            personne.date_naissance,

            personne.sexe,

            personne.adresse,

            personne.telephone,

            personne.email,

            adherent.date_adhesion,

            adherent.statut,

        ])


    for colonne in feuille.columns:

        longueur_max = 0

        lettre_colonne = colonne[0].column_letter


        for cellule in colonne:

            try:

                longueur = len(
                    str(cellule.value)
                )

                if longueur > longueur_max:

                    longueur_max = longueur

            except Exception:

                pass


        feuille.column_dimensions[
            lettre_colonne
        ].width = longueur_max + 2


    response = HttpResponse(

        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    )


    response[
        "Content-Disposition"
    ] = (

        'attachment; filename="adherents.xlsx"'

    )


    workbook.save(response)


    return response
def facture_export_pdf(request):

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

    if "FACTURE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les factures."
        )
        return redirect("factures")

    from django.http import HttpResponse

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = 'attachment; filename="factures.pdf"'

    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    elements = []

    styles = getSampleStyleSheet()

    titre = Paragraph(
        "Liste des factures",
        styles["Title"]
    )

    elements.append(titre)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    factures_list = (
        Facture.objects
        .select_related("id_prestataire")
        .order_by("-date_facture")
    )

    data = [
        [
            "N° Facture",
            "Prestataire",
            "Date",
            "Montant total",
            "Montant validé",
            "Montant rejeté",
            "Statut",
        ]
    ]

    for facture in factures_list:

        data.append([
            facture.numero_facture,
            facture.id_prestataire.raison_sociale,
            facture.date_facture.strftime("%d/%m/%Y")
            if facture.date_facture else "",
            f"{facture.montant_total:.2f}",
            f"{facture.montant_valide:.2f}",
            f"{facture.montant_rejete:.2f}",
            facture.statut,
        ])

    tableau = Table(
        data,
        repeatRows=1,
        colWidths=[
            3 * cm,
            5 * cm,
            3 * cm,
            3.5 * cm,
            3.5 * cm,
            3.5 * cm,
            3 * cm,
        ]
    )

    tableau.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.grey
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, 0),
                10
            ),
        ])
    )

    elements.append(tableau)

    document.build(elements)

    return response
def prestataire_import_excel(request):

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

    if "PRESTATAIRE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'importer les prestataires."
        )
        return redirect("prestataires")

    if request.method == "POST":

        fichier = request.FILES.get("fichier")

        if not fichier:

            messages.error(
                request,
                "Veuillez sélectionner un fichier Excel."
            )

            return redirect(
                "prestataire_import_excel"
            )

        if not fichier.name.endswith(".xlsx"):

            messages.error(
                request,
                "Le fichier doit être au format .xlsx"
            )

            return redirect(
                "prestataire_import_excel"
            )

        try:

            import openpyxl

            workbook = openpyxl.load_workbook(
                fichier
            )

            feuille = workbook.active

            nombre_importes = 0
            nombre_doublons = 0

            with transaction.atomic():

                for ligne in feuille.iter_rows(
                    min_row=2,
                    values_only=True
                ):

                    raison_sociale = ligne[1]

                    type_prestataire = ligne[2]

                    nif = ligne[3]

                    registre_commerce = ligne[4]

                    adresse = ligne[5]

                    telephone = ligne[6]

                    email = ligne[7]

                    statut = ligne[8]


                    if not raison_sociale:

                      continue


                    Prestataire.objects.create(

                        code_prestataire=_generer_code_prestataire(),

                        raison_sociale=str(
                            raison_sociale or ""
                        ).strip(),

                        type_prestataire=str(
                            type_prestataire or ""
                        ).strip(),

                        nif=str(
                            nif or ""
                        ).strip() or None,

                        registre_commerce=str(
                            registre_commerce or ""
                        ).strip() or None,

                        adresse=str(
                            adresse or ""
                        ).strip() or None,

                        telephone=str(
                            telephone or ""
                        ).strip() or None,

                        email=str(
                            email or ""
                        ).strip() or None,

                        statut=str(
                            statut or "ACTIF"
                        ).strip(),

                        date_creation=timezone.now(),

                    )

                    nombre_importes += 1


            messages.success(
                request,
                f"{nombre_importes} prestataire(s) importé(s) avec succès."
            )


            if nombre_doublons > 0:

                messages.warning(
                    request,
                    f"{nombre_doublons} doublon(s) ignoré(s)."
                )


            return redirect("prestataires")


        except Exception as e:

            messages.error(
                request,
                f"Erreur lors de l'importation : {str(e)}"
            )


    return render(
        request,
        "core/prestataire_import_excel.html",
        {
            "permissions": permissions,
        }
    )
def prestataire_export_excel(request):

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

    if "PRESTATAIRE_VIEW" not in permissions:

        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les prestataires."
        )

        return redirect("prestataires")


    import openpyxl

    from openpyxl.styles import Font

    from django.http import HttpResponse


    prestataires_list = (
        Prestataire.objects
        .all()
        .order_by("code_prestataire")
    )


    workbook = openpyxl.Workbook()

    feuille = workbook.active

    feuille.title = "Prestataires"


    entetes = [

        "Code prestataire",

        "Raison sociale",

        "Type prestataire",

        "NIF",

        "Registre de commerce",

        "Adresse",

        "Téléphone",

        "Email",

        "Statut",

        "Date création",

    ]


    feuille.append(entetes)


    for cellule in feuille[1]:

        cellule.font = Font(bold=True)


    for prestataire in prestataires_list:

        feuille.append([

            prestataire.code_prestataire,

            prestataire.raison_sociale,

            prestataire.type_prestataire,

            prestataire.nif,

            prestataire.registre_commerce,

            prestataire.adresse,

            prestataire.telephone,

            prestataire.email,

            prestataire.statut,

            prestataire.date_creation,

        ])


    for colonne in feuille.columns:

        longueur_max = 0

        lettre_colonne = colonne[0].column_letter


        for cellule in colonne:

            try:

                longueur = len(
                    str(cellule.value)
                ) if cellule.value else 0


                if longueur > longueur_max:

                    longueur_max = longueur

            except Exception:

                pass


        feuille.column_dimensions[
            lettre_colonne
        ].width = min(longueur_max + 2, 50)


    response = HttpResponse(

        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )

    )


    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="prestataires.xlsx"'
    )


    workbook.save(response)


    return response



