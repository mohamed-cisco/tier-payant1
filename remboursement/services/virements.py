# remboursement/services/virements.py
"""
Service de gestion des virements adhérents.
Génère 1 virement par adhérent après réception du paiement souscripteur.
"""
from decimal import Decimal
from datetime import date
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum

from remboursement.models import (
    VirementAdherent, BulletinSoins, RecapSouscripteur
)
from core.models import Adherent, CoordonneesBancaires
from remboursement.services.workflow import marquer_reverse


# ============================================================
# NUMÉROTATION
# ============================================================

def generer_numero_virement(adherent, annee=None):
    """VIR-{ANNEE}-{NUM_ADHERENT}"""
    if annee is None:
        annee = timezone.now().year
    
    num = str(adherent.numero_adherent).replace('ADH-', '').replace('-', '')
    base = f"VIR-{annee}-{num}"
    
    numero = base
    compteur = 1
    while VirementAdherent.objects.filter(numero=numero).exists():
        compteur += 1
        numero = f"{base}-{compteur:02d}"
    
    return numero


# ============================================================
# VÉRIFICATION RIB
# ============================================================

def verifier_coordonnees_bancaires(adherent):
    """Vérifie les coordonnées bancaires d'un adhérent."""
    try:
        cb = CoordonneesBancaires.objects.get(adherent=adherent)
    except CoordonneesBancaires.DoesNotExist:
        return False, '', '', "Aucune coordonnée bancaire"
    
    if not cb.rib or len(cb.rib.strip()) < 15:
        return False, '', '', "RIB invalide"
    
    return True, cb.rib, cb.banque or '', ''


# ============================================================
# GÉNÉRATION DES VIREMENTS D'UN RÉCAP
# ============================================================

@transaction.atomic
def generer_virements_recap(recap, user):
    """
    Génère 1 virement par adhérent pour un récap PAYE.
    Regroupe les bulletins de chaque adhérent.
    """
    if recap.statut != 'PAYE':
        raise ValueError("Le récap doit être PAYE.")
    
        # Récupérer les bulletins DU récap UNIQUEMENT
    bulletins = BulletinSoins.objects.filter(
        recap=recap,                        # ← Rattacher à ce récap uniquement
        statut='REMBOURSE',
    ).select_related('adhesion', 'adhesion__id_adherent')
    
    # Grouper par adhérent
    groupes = {}
    for b in bulletins:
        adherent = b.adhesion.id_adherent
        key = adherent.id_adherent
        if key not in groupes:
            groupes[key] = {
                'adherent': adherent,
                'bulletins': [],
                'montant': Decimal('0'),
            }
        groupes[key]['bulletins'].append(b)
        groupes[key]['montant'] += b.montant_total_rembourse or Decimal('0')
    
    # Créer 1 virement par adhérent
    virements_crees = []
    for key, groupe in groupes.items():
                # Éviter les doublons — chercher dans TOUS les récaps
        existant = VirementAdherent.objects.filter(
            adherent=groupe['adherent'],
            statut__in=['A_PAYER', 'EN_COURS', 'PAYE'],  # ← Virements valides
        ).exclude(
            statut='ANNULE'  # ← Ignorer les annulés
        ).first()
        
        if existant:
            print(f"⚠️ Virement déjà existant pour {groupe['adherent'].numero_adherent} : {existant.numero} ({existant.statut})")
            continue
        
        if existant:
            continue
        
        # RIB
        ok, rib, banque, msg = verifier_coordonnees_bancaires(groupe['adherent'])
        
        # Créer le virement
        virement = VirementAdherent.objects.create(
            numero=generer_numero_virement(groupe['adherent']),
            adherent=groupe['adherent'],
            recap=recap,
            montant=groupe['montant'],
            mode_paiement='VIREMENT' if ok else 'ESPECES',
            rib=rib,
            banque=banque,
            statut='A_PAYER',
            cree_par=user,
            observations='' if ok else msg,
        )
        
        # Lier les bulletins
        virement.bulletins.set(groupe['bulletins'])
        virements_crees.append(virement)
    
    return virements_crees


# ============================================================
# MARQUER UN VIREMENT PAYÉ
# ============================================================

@transaction.atomic
def marquer_virement_paye(virement, user, reference='', date_paiement=None):
    """Marque un virement comme payé et met les bulletins à REVERSE."""
    if virement.statut == 'PAYE':
        raise ValueError("Déjà payé.")
    
    virement.statut = 'PAYE'
    virement.date_paiement = date_paiement or timezone.now().date()
    if reference:
        virement.reference_paiement = reference
    virement.paye_par = user
    virement.save()
    
    # Mettre les bulletins en REVERSE
    for bulletin in virement.bulletins.all():
        marquer_reverse(bulletin, user)
    
    return virement


# ============================================================
# ANNULER / ÉCHEC
# ============================================================

@transaction.atomic
def annuler_virement(virement, motif, user):
    if virement.statut == 'PAYE':
        raise ValueError("Impossible d'annuler un virement payé.")
    virement.statut = 'ANNULE'
    virement.observations = f"{virement.observations}\n[Annulé] {motif}"
    virement.save()
    return virement


@transaction.atomic
def marquer_echec_virement(virement, motif, user):
    virement.statut = 'ECHEC'
    virement.observations = f"{virement.observations}\n[Échec] {motif}"
    virement.save()
    return virement


@transaction.atomic
def corriger_rib_virement(virement, rib, banque, user):
    virement.rib = rib
    virement.banque = banque
    virement.statut = 'A_PAYER'
    virement.observations = f"{virement.observations}\n[RIB corrigé]"
    virement.save()
    return virement


# ============================================================
# LISTES ET TOTAUX
# ============================================================

def get_virements_a_payer(souscripteur=None):
    qs = VirementAdherent.objects.filter(
        statut__in=['A_PAYER', 'EN_COURS']
    ).select_related('adherent', 'adherent__id_personne', 'recap')
    
    if souscripteur:
        qs = qs.filter(recap__souscripteur=souscripteur)
    
    return qs.order_by('adherent__numero_adherent')


def get_totaux_virements(souscripteur=None):
    qs = VirementAdherent.objects.all()
    if souscripteur:
        qs = qs.filter(recap__souscripteur=souscripteur)
    
    return {
        'a_payer': qs.filter(statut='A_PAYER').aggregate(
            t=Sum('montant')
        )['t'] or Decimal('0'),
        'payes': qs.filter(statut='PAYE').aggregate(
            t=Sum('montant')
        )['t'] or Decimal('0'),
        'nb_a_payer': qs.filter(statut='A_PAYER').count(),
        'nb_payes': qs.filter(statut='PAYE').count(),
    }