# core/views/ajax.py
"""
Vues AJAX pour les appels asynchrones.

Fonctions :
- ajax_tarif_sous_acte : retourne le tarif d'un sous-acte
- ajax_prestataires_par_sous_acte : retourne les prestataires pour un sous-acte
- tarif_sous_acte_ajax : retourne le tarif pour un détail PEC
"""

from datetime import datetime

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from core.models import (
    PriseEnChargeDetail,
    TarifSousActe,
)


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
    """Retourne le tarif applicable à un détail de PEC (AJAX)."""
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
        return JsonResponse({"tarif": None})

    try:
        detail_pec = (
            PriseEnChargeDetail.objects
            .select_related("id_pec__id_demande")
            .get(id_detail_pec=id_detail_pec)
        )

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
            return JsonResponse({"tarif": None})

        return JsonResponse({
            "tarif": str(tarif.montant),
        })

    except (
        PriseEnChargeDetail.DoesNotExist,
        ValueError,
        TypeError,
    ):
        return JsonResponse({"tarif": None})