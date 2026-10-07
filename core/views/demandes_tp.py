# core/views/demandes_tp.py
"""
Vues de gestion des demandes de tiers payant.

Fonctions :
- demandes_tp : liste
- demande_tp_details : détail
- _libelle_beneficiaire : helper
- _generer_numero_demande : helper
- demande_tp_create : créer
"""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import (
    Adherent,
    AyantDroit,
    Consommation,
    DemandeTp,
    DemandeTpDetail,
    DemandeTpDocument,
    PriseEnChargeDetail,
    RolePermission,
)


def demandes_tp(request):
    """Liste des demandes TP."""
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
        demandes = demandes.filter(
            Q(numero_demande__icontains=recherche)
            | Q(id_personne_beneficiaire__nom__icontains=recherche)
            | Q(id_personne_beneficiaire__prenom__icontains=recherche)
            | Q(id_contrat__numero_contrat__icontains=recherche)
            | Q(id_prestataire__raison_sociale__icontains=recherche)
        )

    if statut:
        demandes = demandes.filter(statut=statut)

    statuts = [
        ("EN_ATTENTE", "En attente"),
        ("ACCEPTEE", "Acceptée"),
        ("REJETEE", "Rejetée"),
        ("ANNULEE", "Annulée"),
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
            "page": "demandes_tp",
        }
    )


def _libelle_beneficiaire(personne):
    """Retourne le libellé du bénéficiaire (adhérent ou ayant droit)."""
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
    """Génère un numéro unique de demande TP."""
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
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_demande = f"{prefixe}{prochain:04d}"

    while DemandeTp.objects.filter(numero_demande=numero_demande).exists():
        prochain += 1
        numero_demande = f"{prefixe}{prochain:04d}"

    return numero_demande


def demande_tp_details(request, id_demande):
    """Détail d'une demande TP."""
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

    if "DEMANDE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les détails de la demande."
        )
        return redirect("demandes_tp")

    try:
        demande = DemandeTp.objects.get(id_demande=id_demande)
    except DemandeTp.DoesNotExist:
        messages.error(request, "Demande de tiers payant introuvable.")
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