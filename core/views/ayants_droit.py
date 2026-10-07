# core/views/ayants_droit.py
"""
Vues de gestion des ayants droit.

Fonctions :
- ayant_droits : liste des ayants droit
- ayant_droit_create : créer un ayant droit
- ayant_droit_modifier : modifier un ayant droit
- ayant_droit_radier : radier un ayant droit
- ayant_droit_export_excel : exporter en Excel
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import AyantDroitForm
from core.models import (
    Adherent,
    AyantDroit,
    Personne,
    RolePermission,
)
from core.views.adherents import _generer_numero_personne
from core.views.champs import (
    get_champs_pour_entite,
    get_valeur_champ,
    sauvegarder_valeurs_champs,
)


def ayant_droits(request):
    """Liste des ayants droit."""
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
        ayant_droits = ayant_droits.filter(
            Q(id_personne__nom__icontains=recherche)
            | Q(id_personne__prenom__icontains=recherche)
            | Q(id_personne__numero_personne__icontains=recherche)
            | Q(id_adherent__numero_adherent__icontains=recherche)
            | Q(type_lien__icontains=recherche)
        )

    if id_adherent:
        ayant_droits = ayant_droits.filter(id_adherent=id_adherent)

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
            "page": "ayant_droits",
        }
    )


def ayant_droit_create(request):
    """Créer un nouvel ayant droit."""
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

    if "AYANT_DROIT_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("ayant_droits")

    id_adherent_preselectionne = request.GET.get("id_adherent", "").strip()
    adherent_preselectionne = None

    if id_adherent_preselectionne:
        adherent_preselectionne = (
            Adherent.objects
            .filter(id_adherent=id_adherent_preselectionne, statut="ACTIF")
            .select_related("id_personne")
            .first()
        )

    if not adherent_preselectionne:
        messages.error(request, "Veuillez sélectionner un adhérent.")
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
                        messages.error(request, "Cet ayant droit existe déjà.")
                        return render(
                            request,
                            "core/ayant_droit_form.html",
                            {
                                "form": form,
                                "titre": "Nouvel ayant droit",
                                "adherent_preselectionne": adherent_preselectionne,
                                "champs_disponibles": get_champs_pour_entite("AYANT_DROIT"),
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

                    ayant_droit = AyantDroit.objects.create(
                        id_personne=personne,
                        id_adherent=adherent_preselectionne,
                        type_lien=form.cleaned_data["type_lien"],
                        date_debut=form.cleaned_data["date_debut"],
                        date_fin=form.cleaned_data["date_fin"],
                        statut=form.cleaned_data["statut"],
                    )

                    sauvegarder_valeurs_champs(
                        request, "AYANT_DROIT", ayant_droit.id_ayant_droit
                    )

                messages.success(request, "Ayant droit créé avec succès.")
                return redirect("adherent_detail", id_adherent=adherent_preselectionne.id_adherent)

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = AyantDroitForm(
            initial={
                "id_adherent": str(adherent_preselectionne.id_adherent),
                "statut": "ACTIF",
            },
            nom_adherent=adherent_preselectionne.id_personne.nom,
            date_adhesion=adherent_preselectionne.date_adhesion
        )

    champs = get_champs_pour_entite("AYANT_DROIT")
    for c in champs:
        c.valeur_actuelle = None
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/ayant_droit_form.html",
        {
            "form": form,
            "titre": "Nouvel ayant droit",
            "adherent_preselectionne": adherent_preselectionne,
            "champs_disponibles": champs,
        }
    )


def ayant_droit_modifier(request, id_ayant_droit):
    """Modifier un ayant droit existant."""
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

    if "AYANT_DROIT_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("ayant_droits")

    try:
        ayant_droit = (
            AyantDroit.objects
            .select_related("id_personne", "id_adherent", "id_adherent__id_personne")
            .get(id_ayant_droit=id_ayant_droit)
        )
    except AyantDroit.DoesNotExist:
        messages.error(request, "Ayant droit introuvable.")
        return redirect("ayant_droits")

    personne = ayant_droit.id_personne
    adherent = ayant_droit.id_adherent

    if request.method == "POST":
        form = AyantDroitForm(
            request.POST,
            nom_adherent=adherent.id_personne.nom,
            date_adhesion=adherent.date_adhesion,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    personne.nom = form.cleaned_data["nom"].strip()
                    personne.prenom = form.cleaned_data["prenom"].strip()
                    personne.date_naissance = form.cleaned_data["date_naissance"]
                    personne.sexe = form.cleaned_data["sexe"] or None
                    personne.date_modification = timezone.now()
                    personne.save()

                    ayant_droit.type_lien = form.cleaned_data["type_lien"]
                    ayant_droit.date_debut = form.cleaned_data["date_debut"]
                    ayant_droit.date_fin = form.cleaned_data["date_fin"]
                    ayant_droit.statut = form.cleaned_data["statut"]
                    ayant_droit.save()

                    sauvegarder_valeurs_champs(
                        request, "AYANT_DROIT", ayant_droit.id_ayant_droit
                    )

                messages.success(request, "Ayant droit modifié avec succès.")
                return redirect("adherent_detail", id_adherent=adherent.id_adherent)

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = AyantDroitForm(
            initial={
                "id_adherent": str(ayant_droit.id_adherent_id),
                "nom": personne.nom,
                "prenom": personne.prenom,
                "date_naissance": personne.date_naissance,
                "sexe": personne.sexe,
                "type_lien": ayant_droit.type_lien,
                "date_debut": ayant_droit.date_debut,
                "date_fin": ayant_droit.date_fin,
                "statut": ayant_droit.statut,
            },
            nom_adherent=adherent.id_personne.nom,
            date_adhesion=adherent.date_adhesion,
        )

    champs = get_champs_pour_entite("AYANT_DROIT")
    for c in champs:
        c.valeur_actuelle = get_valeur_champ(c, ayant_droit.id_ayant_droit)
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/ayant_droit_form.html",
        {
            "form": form,
            "titre": "Modifier l'ayant droit",
            "adherent_preselectionne": adherent,
            "champs_disponibles": champs,
        }
    )


def ayant_droit_radier(request, id_ayant_droit):
    """Radier un ayant droit."""
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

    if "AYANT_DROIT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un ayant droit."
        )
        return redirect("ayant_droits")

    try:
        ayant_droit = AyantDroit.objects.get(id_ayant_droit=id_ayant_droit)
    except AyantDroit.DoesNotExist:
        messages.error(request, "Ayant droit introuvable.")
        return redirect("ayant_droits")

    if request.method == "POST":
        ayant_droit.statut = "RADIE"
        ayant_droit.save()

        messages.success(request, "Ayant droit radié avec succès.")

    return redirect("ayant_droits")


def ayant_droit_export_excel(request):
    """Exporter les ayants droit en Excel."""
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

        feuille.column_dimensions[lettre_colonne].width = min(longueur_max + 2, 50)

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = 'attachment; filename="ayants_droits.xlsx"'

    workbook.save(response)

    return response