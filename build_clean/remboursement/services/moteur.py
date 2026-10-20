# remboursement/services/moteur.py
"""
Moteur de calcul du remboursement.
Utilise GarantieActe (taux + franchise) + Plafond existants.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from django.db import transaction
from django.db.models import Q, Sum

from core.models import GarantieActe, Plafond, Acte, SousActe


def arrondir(m):
    """Arrondit à 2 décimales."""
    if m is None:
        return Decimal('0.00')
    return Decimal(m).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# ============================================================
# CNAS AUTOMATIQUE
# ============================================================

CNAS_TAUX_MEDICAMENTS = Decimal('80.00')

CNAS_FORFAITS = {
    'CONSULTATION': Decimal('120.00'),
    'RADIO':        Decimal('100.00'),
    'ECHO':         Decimal('120.00'),
    'ANALYSE':      Decimal('80.00'),
    'HOSPITALISATION_JOUR': Decimal('500.00'),
}


def calculer_cnas_automatique(ligne):
    """Calcule le CNAS automatiquement selon le type de prestation."""
    from core.models import ConfigCNAS
    
    acte = ligne.acte
    if not acte or not acte.id_type_prestation:
        return None
    
    # Chercher la config CNAS pour ce type de prestation
    try:
        config = ConfigCNAS.objects.get(
            type_prestation=acte.id_type_prestation,
            actif=True
        )
    except ConfigCNAS.DoesNotExist:
        return None
    
    # Si taux > 0 → appliquer le %
    if config.taux_pourcentage > 0:
        montant = arrondir(
            ligne.montant_total * config.taux_pourcentage / Decimal('100')
        )
    # Sinon → utiliser le forfait
    elif config.forfait > 0:
        montant = Decimal(config.forfait)
        # Hospitalisation × nb_nuits
        if ligne.nb_nuits and ligne.nb_nuits > 1:
            montant = arrondir(montant * ligne.nb_nuits)
    else:
        return None
    
    return montant


# ============================================================
# RECHERCHE GARANTIE
# ============================================================

def trouver_garantie_acte(acte, date_acte):
    """Trouve la GarantieActe active pour un acte à une date donnée."""
    return GarantieActe.objects.filter(
        id_acte=acte,
        statut='ACTIF',
        date_debut__lte=date_acte,
    ).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=date_acte)
    ).order_by('-date_debut').first()


# ============================================================
# RECHERCHE PLAFOND
# ============================================================

def trouver_plafonds(garantie_acte, date_acte):
    """Trouve les plafonds actifs pour une GarantieActe."""
    return Plafond.objects.filter(
        id_garantie_acte=garantie_acte,
        statut='ACTIF',
        date_debut__lte=date_acte,
    ).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=date_acte)
    )


# ============================================================
# CALCUL COMPLÉMENTAIRE
# ============================================================

def calculer_complementaire(ligne, base):
    """Calcule le remboursement selon la GarantieActe."""
    garantie = ligne.garantie_acte_utilisee
    if not garantie:
        return {
            'montant': Decimal('0'),
            'taux': None,
            'franchise': None,
            'statut': 'REJETE',
            'motif': 'Aucune garantie active pour cet acte',
        }
    
    taux = Decimal(garantie.taux_prise_en_charge or 0)
    franchise = Decimal(garantie.franchise or 0)
    
    # Appliquer taux
    montant = arrondir(base * taux / Decimal('100'))
    
    # Déduire franchise
    montant = max(montant - franchise, Decimal('0'))
    
    return {
        'montant': montant,
        'taux': taux,
        'franchise': franchise,
        'statut': 'CALCULE',
        'motif': '',
    }


# ============================================================
# CONSOMMATION PLAFOND
# ============================================================

def calculer_consommation_plafond(patient, plafond, date_ref, ligne_actuelle=None):
    """Calcule la consommation d'un plafond pour un patient, EXCLUT la ligne en cours."""
    from remboursement.models import LigneBulletin
    from datetime import timedelta
    
    # Période
    if plafond.periode in ['ANNEE', 'ANNEE_CIVILE']:
        debut = date(date_ref.year, 1, 1)
        fin = date(date_ref.year, 12, 31)
    elif plafond.periode == 'MOIS':
        debut = date(date_ref.year, date_ref.month, 1)
        if date_ref.month == 12:
            fin = date(date_ref.year, 12, 31)
        else:
            fin = date(date_ref.year, date_ref.month + 1, 1) - timedelta(days=1)
    elif plafond.periode == 'JOUR':
        debut = date_ref
        fin = date_ref
    else:
        debut = date(date_ref.year, 1, 1)
        fin = date(date_ref.year, 12, 31)
    
    # Consommation (exclut la ligne en cours)
    lignes = LigneBulletin.objects.filter(
        bulletin__patient=patient,
        plafond_utilise=plafond,
        bulletin__date_soins__gte=debut,
        bulletin__date_soins__lte=fin,
        statut_calcul__in=['CALCULE', 'MANUEL'],
    )
    
    if ligne_actuelle and ligne_actuelle.pk:
        lignes = lignes.exclude(pk=ligne_actuelle.pk)
    
    total = lignes.aggregate(t=Sum('montant_rembourse'))['t'] or Decimal('0')
    return total


def appliquer_plafonds(ligne, montant_propose):
    """Applique les plafonds existants sur un montant."""
    garantie = ligne.garantie_acte_utilisee
    if not garantie:
        return montant_propose, []
    
    plafonds = trouver_plafonds(garantie, ligne.date_acte)
    montant = montant_propose
    motifs = []
    
    for plafond in plafonds:
        if plafond.montant_max:
            consomme = calculer_consommation_plafond(
              ligne.bulletin.patient, plafond, ligne.date_acte,
              ligne_actuelle=ligne
)
            disponible = Decimal(plafond.montant_max) - consomme
            
            if disponible <= 0:
                return Decimal('0'), [f"Plafond atteint"]
            
            if montant > disponible:
                montant = disponible
                motifs.append(f"Écrêté au plafond")
        
        if plafond.quantite_max:
            # Compter les actes
            from remboursement.models import LigneBulletin
            nb_actes = LigneBulletin.objects.filter(
                bulletin__patient=ligne.bulletin.patient,
                plafond_utilise=plafond,
                statut_calcul__in=['CALCULE', 'MANUEL'],
                ).exclude(pk=ligne.pk if ligne.pk else 0).count()
            
            
            if nb_actes >= plafond.quantite_max:
                return Decimal('0'), [f"Quantité max atteinte"]
    
    return montant, motifs


# ============================================================
# CALCUL D'UNE LIGNE
# ============================================================

@transaction.atomic
def calculer_ligne(ligne, cnas_manuel=None):
    """Calcule une ligne complète."""
    facture = ligne.montant_total or Decimal('0')
    
    # CNAS
    if cnas_manuel is not None:
        cnas = arrondir(cnas_manuel)
    else:
        cnas = calculer_cnas_automatique(ligne) or Decimal('0')
    
    cnas = min(cnas, facture)
    reste = facture - cnas
    
    # Trouver la garantie
    if not ligne.garantie_acte_utilisee:
        garantie = trouver_garantie_acte(ligne.acte, ligne.date_acte)
        ligne.garantie_acte_utilisee = garantie
    
    # Calculer complémentaire
    res = calculer_complementaire(ligne, reste)
    
    # Appliquer plafonds
    montant_final, motifs = appliquer_plafonds(ligne, res['montant'])
    
    if motifs:
        ligne.plafond_utilise = trouver_plafonds(
            ligne.garantie_acte_utilisee, ligne.date_acte
        ).first()
    
    # Snapshot
    ligne.montant_cnas = cnas
    ligne.base_calcul = reste
    ligne.taux_applique = res['taux']
    ligne.franchise_appliquee = res['franchise']
    ligne.montant_rembourse = montant_final
    ligne.montant_a_charge = reste - montant_final
    ligne.statut_calcul = 'CALCULE' if res['statut'] == 'CALCULE' else 'MANUEL'
    ligne.motif_rejet = res['motif'] or ' | '.join(motifs)
    ligne.save()
    
    return {
        'facture': facture,
        'cnas': cnas,
        'rembourse': montant_final,
        'a_charge': ligne.montant_a_charge,
    }


# ============================================================
# CALCUL D'UN BULLETIN COMPLET
# ============================================================

@transaction.atomic
def calculer_bulletin(bulletin):
    """Calcule un bulletin entier."""
    total_facture = Decimal('0')
    total_cnas = Decimal('0')
    total_remb = Decimal('0')
    total_charge = Decimal('0')
    
    for ligne in bulletin.lignes.all():
        res = calculer_ligne(ligne)
        total_facture += res['facture']
        total_cnas += res['cnas']
        total_remb += res['rembourse']
        total_charge += res['a_charge']
    
    bulletin.montant_total_facture = total_facture
    bulletin.montant_total_cnas = total_cnas
    bulletin.montant_total_rembourse = total_remb
    bulletin.montant_a_charge = total_charge
    bulletin.save()
    
    return {
        'total_facture': total_facture,
        'total_cnas': total_cnas,
        'total_rembourse': total_remb,
        'total_a_charge': total_charge,
    }