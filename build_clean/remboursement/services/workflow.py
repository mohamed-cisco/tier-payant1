# remboursement/services/workflow.py
"""Workflow des bulletins de soins."""
from django.db import transaction
from django.utils import timezone

from remboursement.models import BulletinSoins
from remboursement.services.moteur import calculer_bulletin


class WorkflowError(Exception):
    """Erreur de workflow."""
    pass


TRANSITIONS = {
    'RECU':            ['EN_VERIFICATION', 'REJETE'],
    'EN_VERIFICATION': ['VALIDE', 'REJETE'],
    'VALIDE':          ['TRANSMIS', 'REJETE'],
    'TRANSMIS':        ['REMBOURSE', 'REJETE'],
    'REMBOURSE':       ['REVERSE'],
    'REVERSE':         [],
    'REJETE':          ['RECU'],
}


def verifier_transition(bulletin, nouveau):
    """Vérifie qu'une transition est autorisée."""
    autorisees = TRANSITIONS.get(bulletin.statut, [])
    if nouveau not in autorisees:
        raise WorkflowError(
            f"Transition invalide : {bulletin.statut} → {nouveau}"
        )


@transaction.atomic
def valider_bulletin(bulletin, user):
    """RECU → EN_VERIFICATION avec calcul."""
    verifier_transition(bulletin, 'EN_VERIFICATION')
    
    calculer_bulletin(bulletin)
    bulletin.statut = 'EN_VERIFICATION'
    bulletin.elabore_par = user
    bulletin.date_elaboration = timezone.now()
    bulletin.save()
    
    return bulletin


@transaction.atomic
def controler_bulletin(bulletin, user):
    """EN_VERIFICATION → VALIDE."""
    verifier_transition(bulletin, 'VALIDE')
    
    bulletin.statut = 'VALIDE'
    bulletin.controle_par = user
    bulletin.date_controle = timezone.now()
    bulletin.save()
    
    return bulletin


@transaction.atomic
def transmettre_bulletin(bulletin, user):
    """VALIDE → TRANSMIS."""
    verifier_transition(bulletin, 'TRANSMIS')
    bulletin.statut = 'TRANSMIS'
    bulletin.save()
    return bulletin


@transaction.atomic
def marquer_rembourse(bulletin, user):
    """TRANSMIS → REMBOURSE."""
    verifier_transition(bulletin, 'REMBOURSE')
    bulletin.statut = 'REMBOURSE'
    bulletin.save()
    return bulletin


@transaction.atomic
def marquer_reverse(bulletin, user):
    """REMBOURSE → REVERSE."""
    verifier_transition(bulletin, 'REVERSE')
    bulletin.statut = 'REVERSE'
    bulletin.save()
    return bulletin


@transaction.atomic
def rejeter_bulletin(bulletin, motif, user):
    """Rejette un bulletin."""
    verifier_transition(bulletin, 'REJETE')
    if not motif or not motif.strip():
        raise WorkflowError("Motif obligatoire.")
    bulletin.statut = 'REJETE'
    bulletin.motif_rejet = motif.strip()
    bulletin.save()
    return bulletin


@transaction.atomic
def reactiver_bulletin(bulletin, user):
    """REJETE → RECU."""
    verifier_transition(bulletin, 'RECU')
    bulletin.statut = 'RECU'
    bulletin.motif_rejet = ''
    bulletin.save()
    return bulletin