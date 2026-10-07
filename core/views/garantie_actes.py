# core/views/garantie_actes.py
"""
Vues de gestion des associations garantie ↔ acte.

Fonctions :
- garantie_actes : liste des associations
- garantie_acte_create : créer une association
- garantie_acte_modifier : modifier une association
- garantie_acte_radier : radier une association
"""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from core.forms import GarantieActeForm
from core.models import (
    Acte,
    Garantie,
    GarantieActe,
    RolePermission,
)


def garantie_actes(request):
    """Liste des associations garantie-acte."""
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
        garantie_actes = garantie_actes.filter(
            Q(id_garantie__code_garantie__icontains=recherche)
            | Q(id_garantie__libelle__icontains=recherche)
            | Q(id_acte__code_acte__icontains=recherche)
            | Q(id_acte__libelle__icontains=recherche)
        )

    if id_garantie:
        garantie_actes = garantie_actes.filter(id_garantie=id_garantie)

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
            "page": "garantie_actes",
        }
    )


def garantie_acte_create(request):
    """Créer une association garantie-acte."""
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

    if "GARANTIE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'associer un acte à une garantie."
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

    id_garantie_preselectionne = request.GET.get("id_garantie", "").strip()
    garantie_preselectionnee = None

    if id_garantie_preselectionne:
        garantie_preselectionnee = (
            Garantie.objects
            .filter(id_garantie=id_garantie_preselectionne, statut="ACTIF")
            .first()
        )

    if request.method == "POST":
        form = GarantieActeForm(request.POST)

        form.fields["id_garantie"].choices = [
            (str(g.id_garantie), f"{g.code_garantie} - {g.libelle}")
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
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
                    taux_prise_en_charge=form.cleaned_data["taux_prise_en_charge"],
                    franchise=form.cleaned_data["franchise"],
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Association garantie-acte créée avec succès."
                )
                return redirect("garantie_actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )
    else:
        form = GarantieActeForm()

        form.fields["id_garantie"].choices = [
            (str(g.id_garantie), f"{g.code_garantie} - {g.libelle}")
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
            for a in actes
        ]

        if garantie_preselectionnee:
            form.initial["id_garantie"] = str(garantie_preselectionnee.id_garantie)

    return render(
        request,
        "core/garantie_acte_form.html",
        {
            "form": form,
            "titre": "Associer un acte à une garantie",
            "garantie_preselectionnee": garantie_preselectionnee,
            "page": "garantie_actes",
        }
    )


def garantie_acte_modifier(request, id_garantie_acte):
    """Modifier une association garantie-acte."""
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

    if "GARANTIE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier une association garantie-acte."
        )
        return redirect("garantie_actes")

    try:
        garantie_acte = GarantieActe.objects.get(id_garantie_acte=id_garantie_acte)
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

    if request.method == "POST":
        form = GarantieActeForm(request.POST)

        form.fields["id_garantie"].choices = [
            (str(g.id_garantie), f"{g.code_garantie} - {g.libelle}")
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
            for a in actes
        ]

        if form.is_valid():
            try:
                garantie_acte.id_garantie_id = form.cleaned_data["id_garantie"]
                garantie_acte.id_acte_id = form.cleaned_data["id_acte"]
                garantie_acte.taux_prise_en_charge = form.cleaned_data["taux_prise_en_charge"]
                garantie_acte.franchise = form.cleaned_data["franchise"]
                garantie_acte.date_debut = form.cleaned_data["date_debut"]
                garantie_acte.date_fin = form.cleaned_data["date_fin"]
                garantie_acte.statut = form.cleaned_data["statut"]

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
                "id_garantie": str(garantie_acte.id_garantie_id),
                "id_acte": str(garantie_acte.id_acte_id),
                "taux_prise_en_charge": garantie_acte.taux_prise_en_charge,
                "franchise": garantie_acte.franchise,
                "date_debut": garantie_acte.date_debut,
                "date_fin": garantie_acte.date_fin,
                "statut": garantie_acte.statut,
            }
        )

        form.fields["id_garantie"].choices = [
            (str(g.id_garantie), f"{g.code_garantie} - {g.libelle}")
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
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
    """Radier une association garantie-acte."""
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

    if "GARANTIE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une association garantie-acte."
        )
        return redirect("garantie_actes")

    try:
        garantie_acte = GarantieActe.objects.get(id_garantie_acte=id_garantie_acte)
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
            "Association garantie-acte radiée avec succès."
        )

    return redirect("garantie_actes")