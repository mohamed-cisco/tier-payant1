# remboursement/services/recap.py
"""
Service de gestion des récaps souscripteur.
Regroupe les bulletins validés d'un mois → envoi à TALA/AMANA.
"""
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count

from remboursement.models import (
    BulletinSoins, RecapSouscripteur, VirementAdherent
)


# ============================================================
# NUMÉROTATION
# ============================================================

def generer_numero_recap(souscripteur, periode_debut):
    """REC-{CODE}-{MM}-{YYYY}"""
    code = souscripteur.code_souscripteur.upper()
    return f"REC-{code}-{periode_debut.strftime('%m')}-{periode_debut.strftime('%Y')}"


# ============================================================
# CRÉATION D'UN RÉCAP MENSUEL
# ============================================================

@transaction.atomic
def creer_recap_mensuel(souscripteur, annee=None, mois=None):
    """
    Crée un récap mensuel pour un souscripteur.
    Par défaut : mois précédent.
    """
    today = date.today()
    if annee is None or mois is None:
        first = today.replace(day=1)
        last_prev = first - timedelta(days=1)
        annee = last_prev.year
        mois = last_prev.month
    
    periode_debut = date(annee, mois, 1)
    dernier_jour = monthrange(annee, mois)[1]
    periode_fin = date(annee, mois, dernier_jour)
    
    # Vérifier si existe
    existant = RecapSouscripteur.objects.filter(
        souscripteur=souscripteur,
        periode_debut=periode_debut,
        periode_fin=periode_fin,
    ).first()
    
    if existant:
        return existant
    
    # Créer le récap
    recap = RecapSouscripteur.objects.create(
        numero=generer_numero_recap(souscripteur, periode_debut),
        souscripteur=souscripteur,
        periode_debut=periode_debut,
        periode_fin=periode_fin,
        statut='BROUILLON',
    )
    
    recalculer_totaux_recap(recap)
    return recap


# ============================================================
# RECALCUL DES TOTAUX
# ============================================================

@transaction.atomic
def recalculer_totaux_recap(recap):
    """Recalcule nb bulletins, nb adhérents, montant total."""
    bulletins = BulletinSoins.objects.filter(
        souscripteur=recap.souscripteur,
        statut__in=['VALIDE', 'TRANSMIS', 'REMBOURSE', 'REVERSE'],
        date_soins__gte=recap.periode_debut,
        date_soins__lte=recap.periode_fin,
    )
    
    recap.nb_bulletins = bulletins.count()
    recap.nb_adherents = bulletins.values('adhesion__id_adherent').distinct().count()
    recap.montant_total = bulletins.aggregate(
        t=Sum('montant_total_rembourse')
    )['t'] or Decimal('0')
    recap.save()
    
    return recap


# ============================================================
# BULLETINS D'UN RÉCAP
# ============================================================

def get_bulletins_recap(recap):
    """Retourne les bulletins du récap."""
    return BulletinSoins.objects.filter(
        souscripteur=recap.souscripteur,
        statut__in=['VALIDE', 'TRANSMIS', 'REMBOURSE', 'REVERSE'],
        date_soins__gte=recap.periode_debut,
        date_soins__lte=recap.periode_fin,
    ).select_related(
        'adhesion', 'adhesion__id_adherent', 'patient', 'contrat'
    ).order_by('adhesion__id_adherent__numero_adherent', 'date_soins')


# ============================================================
# TRANSITIONS DE STATUT
# ============================================================

@transaction.atomic
def envoyer_recap(recap, user):
    """BROUILLON → ENVOYE."""
    if recap.statut != 'BROUILLON':
        raise ValueError("Le récap doit être en BROUILLON.")
    if recap.nb_bulletins == 0:
        raise ValueError("Impossible d'envoyer un récap vide.")
    
    recalculer_totaux_recap(recap)
    
    # Marquer les bulletins comme TRANSMIS
    bulletins = get_bulletins_recap(recap)
    bulletins.update(statut='TRANSMIS', recap=recap)
    
    recap.statut = 'ENVOYE'
    recap.date_envoi = timezone.now().date()
    recap.save()
    
    return recap


@transaction.atomic
def valider_recap(recap, user, reference=''):
    """ENVOYE → VALIDE."""
    if recap.statut not in ['ENVOYE', 'EN_CONTROLE']:
        raise ValueError("Le récap doit être ENVOYE.")
    
    recap.statut = 'VALIDE'
    recap.date_validation = timezone.now().date()
    if reference:
        recap.reference_virement = reference
    recap.save()
    
    return recap


@transaction.atomic
def enregistrer_paiement_recap(recap, montant, user, reference='', date_paiement=None):
    """
    VALIDE → PAYE.
    Enregistre le virement reçu du souscripteur.
    """
    if recap.statut != 'VALIDE':
        raise ValueError("Le récap doit être VALIDE.")
    
    recap.statut = 'PAYE'
    recap.montant_recu = Decimal(str(montant))
    recap.date_paiement = date_paiement or timezone.now().date()
    if reference:
        recap.reference_virement = reference
    recap.save()
    
    # Marquer les bulletins comme REMBOURSE
    bulletins = get_bulletins_recap(recap)
    bulletins.update(statut='REMBOURSE')
    
    return recap


@transaction.atomic
def rejeter_recap(recap, motif, user):
    """Rejette un récap."""
    if not motif or not motif.strip():
        raise ValueError("Motif obligatoire.")
    
    recap.statut = 'REJETE'
    recap.motif_rejet = motif.strip()
    recap.save()
    return recap


# ============================================================
# RÉSUMÉ POUR AFFICHAGE
# ============================================================

def get_resume_recap(recap):
    return {
        'numero': recap.numero,
        'souscripteur': recap.souscripteur.raison_sociale,
        'periode': f"{recap.periode_debut.strftime('%d/%m/%Y')} → {recap.periode_fin.strftime('%d/%m/%Y')}",
        'statut': recap.get_statut_display(),
        'nb_bulletins': recap.nb_bulletins,
        'nb_adherents': recap.nb_adherents,
        'montant_total': recap.montant_total,
    }