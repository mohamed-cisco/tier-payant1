# remboursement/services/bordereau.py
"""
Service de génération du bordereau bancaire.

Regroupe les virements adhérents à payer dans un format imprimable
pour dépôt à la banque.
"""
from decimal import Decimal
from datetime import date
from django.db.models import Sum

from remboursement.models import VirementAdherent
from core.models import Adherent


# ============================================================
# RÉCUPÉRATION DES LIGNES
# ============================================================

def get_bordereau_virements(
    date_debut=None,
    date_fin=None,
    souscripteur=None,
    banque=None,
    mode_paiement=None,
    statut=None,
):
    """
    Retourne un queryset de virements filtrable pour le bordereau.
    
    Par défaut : tous les virements A_PAYER + EN_COURS.
    """
    if statut is None:
        statut = ['A_PAYER', 'EN_COURS']

    qs = (
        VirementAdherent.objects
        .filter(statut__in=statut if isinstance(statut, list) else [statut])
        .select_related(
            'adherent',
            'adherent__id_personne',
            'recap',
            'recap__souscripteur',
        )
        .order_by('adherent__numero_adherent')
    )

    if date_debut:
        qs = qs.filter(date_creation__date__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_creation__date__lte=date_fin)
    if souscripteur:
        qs = qs.filter(recap__souscripteur=souscripteur)
    if banque:
        qs = qs.filter(banque__icontains=banque)
    if mode_paiement:
        qs = qs.filter(mode_paiement=mode_paiement)

    return qs


def construire_lignes_bordereau(virements_qs):
    """
    Transforme un queryset de VirementAdherent en lignes prêtes pour le PDF.
    
    Retourne une liste de dict :
    [
        {
            "numero": "VIR-2026-0001",
            "adherent_nom": "BENALI Mohamed",
            "adherent_numero": "ADH-2026-0001",
            "banque": "BNA",
            "rib": "00799999123456789012",
            "mode_paiement": "Virement bancaire",
            "montant": Decimal("15000.00"),
            "nb_bulletins": 3,
            "reference": "REF-123",
        },
        ...
    ]
    """
    lignes = []
    for v in virements_qs:
        personne = v.adherent.id_personne
        nom_complet = f"{personne.nom} {personne.prenom}".strip()

        lignes.append({
            "numero": v.numero,
            "adherent_nom": nom_complet,
            "adherent_numero": v.adherent.numero_adherent,
            "banque": v.banque or "—",
            "rib": v.rib or "—",
            "mode_paiement": v.get_mode_paiement_display(),
            "montant": v.montant or Decimal("0.00"),
            "nb_bulletins": v.bulletins.count(),
            "reference": v.reference_paiement or "",
        })

    return lignes


def calculer_totaux(lignes):
    """Calcule les totaux du bordereau."""
    total = sum((l["montant"] for l in lignes), Decimal("0.00"))

    # Regrouper par banque (pour info)
    par_banque = {}
    for l in lignes:
        b = l["banque"] or "Non renseignée"
        par_banque.setdefault(b, {"nb": 0, "montant": Decimal("0.00")})
        par_banque[b]["nb"] += 1
        par_banque[b]["montant"] += l["montant"]

    return {
        "total": total,
        "nb_virements": len(lignes),
        "par_banque": par_banque,
    }
