# core/views/rapports.py
"""
Module de rapports professionnels.

Fonctions :
- rapports : page principale
- rapport_mensuel : vue du rapport mensuel
- rapport_mensuel_pdf : export PDF
- rapport_mensuel_excel : export Excel
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDay, TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import (
    Consommation,
    DemandeTp,
    Facture,
    Prestataire,
    PriseEnCharge,
    Reglement,
    RolePermission,
)


def _get_permissions(request):
    """Récupère les permissions de l'utilisateur connecté."""
    if not request.session.get("id_utilisateur"):
        return None

    id_utilisateur = request.session["id_utilisateur"]

    return set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )


def rapports(request):
    """Page principale des rapports."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions and "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de consulter les rapports.")
        return redirect("accueil")

    return render(
        request,
        "core/rapports.html",
        {
            "permissions": permissions,
            "page": "rapports",
        }
    )


def rapport_mensuel(request):
    """Rapport mensuel global."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions and "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")

    # Récupérer le mois et l'année depuis les paramètres GET
    aujourd_hui = timezone.now().date()

    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year

    # Bornes du mois
    date_debut = date(annee, mois, 1)
    if mois == 12:
        date_fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin = date(annee, mois + 1, 1) - timedelta(days=1)

    # ============================================================
    # STATISTIQUES GÉNÉRALES
    # ============================================================
    demandes = DemandeTp.objects.filter(
        date_demande__date__gte=date_debut,
        date_demande__date__lte=date_fin,
    )

    pec = PriseEnCharge.objects.filter(
        date_pec__date__gte=date_debut,
        date_pec__date__lte=date_fin,
    )

    consommations = Consommation.objects.filter(
        date_prestation__gte=date_debut,
        date_prestation__lte=date_fin,
    )

    factures = Facture.objects.filter(
        date_facture__gte=date_debut,
        date_facture__lte=date_fin,
    )

    reglements = Reglement.objects.filter(
        date_reglement__gte=date_debut,
        date_reglement__lte=date_fin,
    )

    # KPIs
    nb_demandes = demandes.count()
    nb_pec = pec.count()
    nb_consommations = consommations.count()
    nb_factures = factures.count()
    nb_reglements = reglements.count()

    # Montants
    montant_demandes = demandes.aggregate(total=Sum("montant_demande"))["total"] or Decimal("0.00")
    montant_pec_accepte = pec.aggregate(total=Sum("montant_accepte"))["total"] or Decimal("0.00")
    montant_pec_rejete = pec.aggregate(total=Sum("montant_rejete"))["total"] or Decimal("0.00")
    montant_consommations = consommations.aggregate(
        total=Sum("montant_prise_en_charge")
    )["total"] or Decimal("0.00")
    montant_factures_valide = factures.aggregate(
        total=Sum("montant_valide")
    )["total"] or Decimal("0.00")
    montant_reglements = reglements.aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0.00")

    # Taux d'acceptation
    demandes_acceptees = demandes.filter(statut="ACCEPTEE").count()
    if nb_demandes > 0:
        taux_acceptation = round((demandes_acceptees / nb_demandes) * 100, 1)
    else:
        taux_acceptation = 0

    # ============================================================
    # TOP 10 PRESTATAIRES
    # ============================================================
    top_prestataires = (
        Facture.objects
        .filter(
            date_facture__gte=date_debut,
            date_facture__lte=date_fin,
        )
        .values("id_prestataire__raison_sociale")
        .annotate(
            total=Sum("montant_valide"),
            nb_factures=Count("id_facture"),
        )
        .order_by("-total")[:10]
    )

    # ============================================================
    # TOP 10 ACTES
    # ============================================================
    top_actes = (
        Consommation.objects
        .filter(
            date_prestation__gte=date_debut,
            date_prestation__lte=date_fin,
        )
        .values("id_acte__code_acte", "id_acte__libelle")
        .annotate(
            total=Sum("montant_prise_en_charge"),
            nb=Count("id_consommation"),
        )
        .order_by("-nb")[:10]
    )

    # ============================================================
    # ÉVOLUTION JOURNALIÈRE
    # ============================================================
    evolution_demandes = (
        demandes
        .annotate(jour=TruncDay("date_demande"))
        .values("jour")
        .annotate(total=Count("id_demande"))
        .order_by("jour")
    )

    graphique_labels = [item["jour"].strftime("%d/%m") for item in evolution_demandes]
    graphique_demandes = [item["total"] for item in evolution_demandes]

    # ============================================================
    # COMPARAISON MOIS PRÉCÉDENT
    # ============================================================
    if mois == 1:
        mois_precedent = 12
        annee_precedente = annee - 1
    else:
        mois_precedent = mois - 1
        annee_precedente = annee

    date_debut_prec = date(annee_precedente, mois_precedent, 1)
    if mois_precedent == 12:
        date_fin_prec = date(annee_precedente + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin_prec = date(annee_precedente, mois_precedent + 1, 1) - timedelta(days=1)

    demandes_prec = DemandeTp.objects.filter(
        date_demande__date__gte=date_debut_prec,
        date_demande__date__lte=date_fin_prec,
    ).count()

    if demandes_prec > 0:
        evolution_demandes_pct = round(((nb_demandes - demandes_prec) / demandes_prec) * 100, 1)
    else:
        evolution_demandes_pct = 0

    # Noms des mois
    noms_mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    return render(
        request,
        "core/rapport_mensuel.html",
        {
            "permissions": permissions,
            "page": "rapports",

            # Paramètres
            "mois": mois,
            "annee": annee,
            "nom_mois": noms_mois[mois - 1],
            "date_debut": date_debut,
            "date_fin": date_fin,

            # KPIs
            "nb_demandes": nb_demandes,
            "nb_pec": nb_pec,
            "nb_consommations": nb_consommations,
            "nb_factures": nb_factures,
            "nb_reglements": nb_reglements,

            # Montants
            "montant_demandes": montant_demandes,
            "montant_pec_accepte": montant_pec_accepte,
            "montant_pec_rejete": montant_pec_rejete,
            "montant_consommations": montant_consommations,
            "montant_factures_valide": montant_factures_valide,
            "montant_reglements": montant_reglements,

            # Taux
            "taux_acceptation": taux_acceptation,
            "evolution_demandes_pct": evolution_demandes_pct,
            "demandes_prec": demandes_prec,

            # Top
            "top_prestataires": top_prestataires,
            "top_actes": top_actes,

            # Graphique
            "graphique_labels": graphique_labels,
            "graphique_demandes": graphique_demandes,
        }
    )