# core/views/garanties.py
"""
Vues de gestion des garanties.

Fonctions :
- garanties : liste des garanties
- garantie_detail : fiche d'une garantie
- _generer_code_garantie : helper
- garantie_create : créer une garantie
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import GarantieForm
from core.models import (
    Garantie,
    GarantieActe,
    RolePermission,
)


def garanties(request):
    """Liste des garanties."""
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
        garanties = garanties.filter(
            Q(code_garantie__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        garanties = garanties.filter(statut=statut)

    return render(
        request,
        "core/garanties.html",
        {
            "garanties": garanties,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "garanties",
        }
    )


def garantie_detail(request, id_garantie):
    """Fiche détaillée d'une garantie."""
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
            "Vous n'avez pas l'autorisation de consulter cette garantie."
        )
        return redirect("garanties")

    try:
        garantie = Garantie.objects.get(id_garantie=id_garantie)
    except Garantie.DoesNotExist:
        messages.error(request, "Garantie introuvable.")
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
    """Génère un code unique de garantie."""
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
            valeurs.append(int(code.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    code_garantie = f"{prefixe}{prochain:04d}"

    while Garantie.objects.filter(code_garantie=code_garantie).exists():
        prochain += 1
        code_garantie = f"{prefixe}{prochain:04d}"

    return code_garantie



def garantie_create(request):
    """Créer une nouvelle garantie."""
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
            "Vous n'avez pas l'autorisation de créer une garantie."
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

                messages.success(request, "Garantie créée avec succès.")
                return redirect("garanties")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
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
    """Modifier une garantie existante."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    try:
        garantie = Garantie.objects.get(id_garantie=id_garantie)
    except Garantie.DoesNotExist:
        messages.error(request, "Garantie introuvable.")
        return redirect("garanties")

    if request.method == "POST":
        form = GarantieForm(request.POST)

        if form.is_valid():
            try:
                garantie.libelle = form.cleaned_data["libelle"]
                garantie.description = form.cleaned_data["description"] or None
                garantie.statut = form.cleaned_data["statut"]
                garantie.save()

                messages.success(request, "Garantie modifiée avec succès.")
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

def garantie_create(request):
    """Créer une nouvelle garantie."""
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
            "Vous n'avez pas l'autorisation de créer une garantie."
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

                messages.success(request, "Garantie créée avec succès.")
                return redirect("garanties")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
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
    """Modifier une garantie existante."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    try:
        garantie = Garantie.objects.get(id_garantie=id_garantie)
    except Garantie.DoesNotExist:
        messages.error(request, "Garantie introuvable.")
        return redirect("garanties")

    if request.method == "POST":
        form = GarantieForm(request.POST)

        if form.is_valid():
            try:
                garantie.libelle = form.cleaned_data["libelle"]
                garantie.description = form.cleaned_data["description"] or None
                garantie.statut = form.cleaned_data["statut"]
                garantie.save()

                messages.success(request, "Garantie modifiée avec succès.")
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
    """Radier une garantie."""
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
            "Vous n'avez pas l'autorisation de radier une garantie."
        )
        return redirect("garanties")

    try:
        garantie = Garantie.objects.get(id_garantie=id_garantie)
    except Garantie.DoesNotExist:
        messages.error(request, "Garantie introuvable.")
        return redirect("garanties")

    if request.method == "POST":
        garantie.statut = "RADIE"
        garantie.save()

        messages.success(request, "Garantie radiée avec succès.")

    return redirect("garanties")
