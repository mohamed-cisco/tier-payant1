"""Vues des référentiels « motifs de rejet » et « types de prestation ».

Ces vues sont isolées de core/views.py (11 500 lignes) mais respectent ses
conventions : garde de session, ensemble de permissions lu depuis
RolePermission, messages, trace via enregistrer_audit(), et radiation logique
par passage du statut à INACTIF plutôt que suppression physique.

Le module sous-actes / tarifs prestataire n'est volontairement PAS ici : il
existe déjà dans core/views.py et s'appuie sur les permissions ACTE_*.
"""

import re
import unicodedata

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import MotifRejetForm, TypePrestationForm
from .models import Acte, MotifRejet, RolePermission, TypePrestation
from .views import enregistrer_audit


def _permissions(request):
    return set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=request.session["id_utilisateur"],
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF",
        )
        .values_list("id_permission__code_permission", flat=True)
    )


def _generer_code_motif_rejet():
    annee = timezone.now().year
    prefixe = f"MR-{annee}-"

    codes = (
        MotifRejet.objects
        .filter(code__startswith=prefixe)
        .values_list("code", flat=True)
    )

    valeurs = []

    for code in codes:
        try:
            valeurs.append(int(code.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code = f"{prefixe}{prochain:04d}"

    while MotifRejet.objects.filter(code=code).exists():
        prochain += 1
        code = f"{prefixe}{prochain:04d}"

    return code


def _normaliser_code(libelle):
    sans_accent = unicodedata.normalize("NFKD", libelle or "")
    sans_accent = "".join(
        c for c in sans_accent if not unicodedata.combining(c)
    )
    return re.sub(r"[^A-Z0-9]+", "_", sans_accent.upper()).strip("_")[:30]


def _generer_code_type_prestation(libelle):
    # Les types existants portent des codes sémantiques (ANALYSE, DENTAIRE,
    # RADIOLOGIE…) et non des codes séquentiels : on suit cette convention.
    base = _normaliser_code(libelle) or "TYPE"

    code = base
    compteur = 2

    while TypePrestation.objects.filter(code_type=code).exists():
        suffixe = f"_{compteur}"
        code = base[:30 - len(suffixe)] + suffixe
        compteur += 1

    return code


# =========================
# MOTIFS DE REJET
# =========================

def motifs_rejet(request):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    permissions = _permissions(request)

    if "MOTIF_REJET_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les motifs de rejet."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    motifs = MotifRejet.objects.all().order_by("code")

    if recherche:
        motifs = motifs.filter(
            Q(code__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        motifs = motifs.filter(statut=statut)

    return render(
        request,
        "core/motifs_rejet.html",
        {
            "motifs": motifs,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        },
    )


def motif_rejet_create(request):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    permissions = _permissions(request)

    if "MOTIF_REJET_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un motif de rejet."
        )
        return redirect("motifs_rejet")

    if request.method == "POST":
        form = MotifRejetForm(request.POST)

        if form.is_valid():
            code_saisi = (form.cleaned_data["code"] or "").strip()

            if code_saisi and MotifRejet.objects.filter(code=code_saisi).exists():
                messages.error(
                    request,
                    f"Le code « {code_saisi} » est déjà utilisé par un autre "
                    f"motif de rejet."
                )
                return redirect("motif_rejet_create")

            try:
                motif = MotifRejet.objects.create(
                    code=code_saisi or _generer_code_motif_rejet(),
                    libelle=form.cleaned_data["libelle"],
                    type_rejet=form.cleaned_data["type_rejet"],
                    description=form.cleaned_data["description"] or None,
                    statut=form.cleaned_data["statut"],
                )

                enregistrer_audit(
                    request,
                    "CREATION",
                    "Motif de rejet",
                    table_cible="motif_rejet",
                    id_enregistrement=motif.id_motif_rejet,
                    nouvelle_valeur=f"{motif.code} - {motif.libelle}",
                    description=f"Création du motif de rejet {motif.code}.",
                )

                messages.success(
                    request,
                    f"Motif de rejet {motif.code} créé avec succès."
                )

                return redirect("motifs_rejet")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )
    else:
        form = MotifRejetForm()

    return render(
        request,
        "core/motif_rejet_form.html",
        {
            "form": form,
            "titre": "Nouveau motif de rejet",
        },
    )


def motif_rejet_modifier(request, id_motif_rejet):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    permissions = _permissions(request)

    if "MOTIF_REJET_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un motif de rejet."
        )
        return redirect("motifs_rejet")

    try:
        motif = MotifRejet.objects.get(id_motif_rejet=id_motif_rejet)
    except MotifRejet.DoesNotExist:
        messages.error(request, "Motif de rejet introuvable.")
        return redirect("motifs_rejet")

    if request.method == "POST":
        form = MotifRejetForm(request.POST)
        # Le code est l'identifiant métier : il ne se modifie pas.
        del form.fields["code"]

        if form.is_valid():
            try:
                avant = f"{motif.libelle} | {motif.type_rejet} | {motif.statut}"

                motif.libelle = form.cleaned_data["libelle"]
                motif.type_rejet = form.cleaned_data["type_rejet"]
                motif.description = form.cleaned_data["description"] or None
                motif.statut = form.cleaned_data["statut"]
                motif.save()

                enregistrer_audit(
                    request,
                    "MODIFICATION",
                    "Motif de rejet",
                    table_cible="motif_rejet",
                    id_enregistrement=motif.id_motif_rejet,
                    ancienne_valeur=avant,
                    nouvelle_valeur=f"{motif.libelle} | {motif.type_rejet} | {motif.statut}",
                    description=f"Modification du motif de rejet {motif.code}.",
                )

                messages.success(request, "Motif de rejet modifié avec succès.")

                return redirect("motifs_rejet")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )
    else:
        form = MotifRejetForm(
            initial={
                "libelle": motif.libelle,
                "type_rejet": motif.type_rejet,
                "description": motif.description or "",
                "statut": motif.statut,
            }
        )
        del form.fields["code"]

    return render(
        request,
        "core/motif_rejet_form.html",
        {
            "form": form,
            "titre": f"Modifier le motif {motif.code}",
            "motif": motif,
        },
    )


def motif_rejet_desactiver(request, id_motif_rejet):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    permissions = _permissions(request)

    if "MOTIF_REJET_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de désactiver un motif de rejet."
        )
        return redirect("motifs_rejet")

    try:
        motif = MotifRejet.objects.get(id_motif_rejet=id_motif_rejet)
    except MotifRejet.DoesNotExist:
        messages.error(request, "Motif de rejet introuvable.")
        return redirect("motifs_rejet")

    if request.method == "POST":
        motif.statut = "INACTIF"
        motif.save()

        enregistrer_audit(
            request,
            "DESACTIVATION",
            "Motif de rejet",
            table_cible="motif_rejet",
            id_enregistrement=motif.id_motif_rejet,
            description=f"Désactivation du motif de rejet {motif.code}.",
        )

        messages.success(
            request,
            f"Motif de rejet {motif.code} désactivé."
        )

    return redirect("motifs_rejet")


# =========================
# TYPES DE PRESTATION
# =========================

def types_prestation(request):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    permissions = _permissions(request)

    if "TYPE_PRESTATION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les types de prestation."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    types = TypePrestation.objects.all().order_by("code_type")

    if recherche:
        types = types.filter(
            Q(code_type__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        types = types.filter(statut=statut)

    return render(
        request,
        "core/types_prestation.html",
        {
            "types_prestation": types,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        },
    )


def type_prestation_create(request):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    permissions = _permissions(request)

    if "TYPE_PRESTATION_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un type de prestation."
        )
        return redirect("types_prestation")

    if request.method == "POST":
        form = TypePrestationForm(request.POST)

        if form.is_valid():
            code_saisi = (form.cleaned_data["code_type"] or "").strip().upper()

            if code_saisi and TypePrestation.objects.filter(
                code_type=code_saisi
            ).exists():
                messages.error(
                    request,
                    f"Le code « {code_saisi} » est déjà utilisé par un autre "
                    f"type de prestation."
                )
                return redirect("type_prestation_create")

            try:
                type_prestation = TypePrestation.objects.create(
                    code_type=(
                        code_saisi
                        or _generer_code_type_prestation(
                            form.cleaned_data["libelle"]
                        )
                    ),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"] or None,
                    statut=form.cleaned_data["statut"],
                )

                enregistrer_audit(
                    request,
                    "CREATION",
                    "Type de prestation",
                    table_cible="type_prestation",
                    id_enregistrement=type_prestation.id_type_prestation,
                    nouvelle_valeur=(
                        f"{type_prestation.code_type} - {type_prestation.libelle}"
                    ),
                    description=(
                        f"Création du type de prestation "
                        f"{type_prestation.code_type}."
                    ),
                )

                messages.success(
                    request,
                    f"Type de prestation {type_prestation.code_type} créé avec succès."
                )

                return redirect("types_prestation")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )
    else:
        form = TypePrestationForm()

    return render(
        request,
        "core/type_prestation_form.html",
        {
            "form": form,
            "titre": "Nouveau type de prestation",
        },
    )


def type_prestation_modifier(request, id_type_prestation):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    permissions = _permissions(request)

    if "TYPE_PRESTATION_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un type de prestation."
        )
        return redirect("types_prestation")

    try:
        type_prestation = TypePrestation.objects.get(
            id_type_prestation=id_type_prestation
        )
    except TypePrestation.DoesNotExist:
        messages.error(request, "Type de prestation introuvable.")
        return redirect("types_prestation")

    if request.method == "POST":
        form = TypePrestationForm(request.POST)
        # Le code est l'identifiant métier : il ne se modifie pas.
        del form.fields["code_type"]

        if form.is_valid():
            try:
                avant = f"{type_prestation.libelle} | {type_prestation.statut}"

                type_prestation.libelle = form.cleaned_data["libelle"]
                type_prestation.description = (
                    form.cleaned_data["description"] or None
                )
                type_prestation.statut = form.cleaned_data["statut"]
                type_prestation.save()

                enregistrer_audit(
                    request,
                    "MODIFICATION",
                    "Type de prestation",
                    table_cible="type_prestation",
                    id_enregistrement=type_prestation.id_type_prestation,
                    ancienne_valeur=avant,
                    nouvelle_valeur=(
                        f"{type_prestation.libelle} | {type_prestation.statut}"
                    ),
                    description=(
                        f"Modification du type de prestation "
                        f"{type_prestation.code_type}."
                    ),
                )

                messages.success(
                    request,
                    "Type de prestation modifié avec succès."
                )

                return redirect("types_prestation")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )
    else:
        form = TypePrestationForm(
            initial={
                "libelle": type_prestation.libelle,
                "description": type_prestation.description or "",
                "statut": type_prestation.statut,
            }
        )
        del form.fields["code_type"]

    return render(
        request,
        "core/type_prestation_form.html",
        {
            "form": form,
            "titre": f"Modifier le type {type_prestation.code_type}",
            "type_prestation": type_prestation,
        },
    )


def type_prestation_desactiver(request, id_type_prestation):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    permissions = _permissions(request)

    if "TYPE_PRESTATION_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de désactiver un type de prestation."
        )
        return redirect("types_prestation")

    try:
        type_prestation = TypePrestation.objects.get(
            id_type_prestation=id_type_prestation
        )
    except TypePrestation.DoesNotExist:
        messages.error(request, "Type de prestation introuvable.")
        return redirect("types_prestation")

    if request.method == "POST":
        actes_lies = Acte.objects.filter(
            id_type_prestation=type_prestation,
            statut="ACTIF",
        ).count()

        if actes_lies:
            messages.error(
                request,
                f"Impossible de désactiver ce type : {actes_lies} acte(s) "
                f"actif(s) y sont rattachés."
            )
            return redirect("types_prestation")

        type_prestation.statut = "INACTIF"
        type_prestation.save()

        enregistrer_audit(
            request,
            "DESACTIVATION",
            "Type de prestation",
            table_cible="type_prestation",
            id_enregistrement=type_prestation.id_type_prestation,
            description=(
                f"Désactivation du type de prestation "
                f"{type_prestation.code_type}."
            ),
        )

        messages.success(
            request,
            f"Type de prestation {type_prestation.code_type} désactivé."
        )

    return redirect("types_prestation")
