# core/services/tva.py
"""
Service de gestion de la TVA sur les factures.

Taux par défaut : 19% (Algérie - taux normal).
Le taux est configurable par l'administrateur via la table ConfigTVA.
"""
from decimal import Decimal
from datetime import date

from django.db.models import Q

from core.models import ConfigTVA


# ============================================================
# RÉCUPÉRATION DU TAUX ACTIF
# ============================================================

def get_taux_tva_actif():
    """
    Retourne le taux de TVA actif à la date du jour.
    
    Returns:
        Decimal: Taux en % (ex: Decimal('19.00'))
    """
    today = date.today()
    
    config = (
        ConfigTVA.objects
        .filter(
            actif=True,
            date_debut__lte=today,
        )
        .filter(
            Q(date_fin__isnull=True) | Q(date_fin__gte=today)
        )
        .order_by('-date_debut')
        .first()
    )
    
    if config:
        return config.taux
    
    # Taux par défaut si aucune config
    return Decimal("19.00")


# ============================================================
# CALCUL DE LA TVA
# ============================================================

def calculer_tva(montant_ht, taux=None):
    """
    Calcule la TVA et le montant TTC.
    
    Args:
        montant_ht (Decimal ou float): Montant hors taxe
        taux (Decimal, optional): Taux de TVA en %. Si None, utilise le taux actif.
    
    Returns:
        dict: {
            'taux': Decimal,
            'montant_tva': Decimal,
            'montant_ttc': Decimal,
        }
    """
    if montant_ht is None:
        montant_ht = Decimal("0.00")
    
    montant_ht = Decimal(str(montant_ht))
    
    if taux is None:
        taux = get_taux_tva_actif()
    else:
        taux = Decimal(str(taux))
    
    montant_tva = (montant_ht * taux / Decimal("100")).quantize(Decimal("0.01"))
    montant_ttc = (montant_ht + montant_tva).quantize(Decimal("0.01"))
    
    return {
        'taux': taux,
        'montant_tva': montant_tva,
        'montant_ttc': montant_ttc,
    }


# ============================================================
# APPLICATION À UNE FACTURE
# ============================================================

def appliquer_tva_facture(facture, taux=None, sauvegarder=True):
    """
    Applique la TVA à une facture existante.
    
    Args:
        facture: instance Facture
        taux (Decimal, optional): Taux à appliquer. Sinon taux actif.
        sauvegarder (bool): Si True, sauvegarde la facture.
    
    Returns:
        dict: Résultat du calcul
    """
    resultat = calculer_tva(facture.montant_total, taux)
    
    facture.taux_tva = resultat['taux']
    facture.montant_tva = resultat['montant_tva']
    facture.montant_ttc = resultat['montant_ttc']
    
    if sauvegarder:
        facture.save(update_fields=['taux_tva', 'montant_tva', 'montant_ttc'])
    
    return resultat


# ============================================================
# FORMATAGE
# ============================================================

def formater_tva(taux):
    """Formate un taux (ex: Decimal('19.00') → '19.00%')."""
    return f"{taux}%"


def formater_montant(montant):
    """Formate un montant en DA."""
    if montant is None:
        return "0.00 DA"
    return f"{montant:,.2f} DA".replace(",", " ")