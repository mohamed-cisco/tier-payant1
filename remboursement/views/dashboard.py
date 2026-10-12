# remboursement/views/dashboard.py
"""Tableau de bord dédié au module Remboursement (séparé du dashboard principal)."""
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.contrib import messages

from core.models import RolePermission, Souscripteur, Adherent, CoordonneesBancaires
from core.views.decorators import session_utilisateur_required

from remboursement.models import (
    BulletinSoins, RecapSouscripteur, VirementAdherent
)


def _get_permissions(id_utilisateur):
    return set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )


@session_utilisateur_required
def dashboard(request):
    """Tableau de bord dédié au remboursement."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")
    
    # ============ PÉRIODE ============
    periode = request.GET.get("periode", "mois")
    today = date.today()
    
    if periode == "mois":
        date_debut = today.replace(day=1)
        date_fin = today
    elif periode == "trimestre":
        mois_debut = ((today.month - 1) // 3) * 3 + 1
        date_debut = date(today.year, mois_debut, 1)
        date_fin = today
    elif periode == "annee":
        date_debut = date(today.year, 1, 1)
        date_fin = today
    else:
        date_debut = today.replace(day=1)
        date_fin = today
    
    # ============ STATS BULLETINS ============
    bulletins = BulletinSoins.objects.filter(
        date_soins__gte=date_debut,
        date_soins__lte=date_fin,
    )
    
    stats_bulletins = {
        'total': bulletins.count(),
        'recu': bulletins.filter(statut='RECU').count(),
        'en_verification': bulletins.filter(statut='EN_VERIFICATION').count(),
        'valide': bulletins.filter(statut='VALIDE').count(),
        'transmis': bulletins.filter(statut='TRANSMIS').count(),
        'rembourse': bulletins.filter(statut='REMBOURSE').count(),
        'reverse': bulletins.filter(statut='REVERSE').count(),
        'rejete': bulletins.filter(statut='REJETE').count(),
    }
    
    # ============ MONTANTS ============
    montants = bulletins.aggregate(
        facture=Sum('montant_total_facture'),
        cnas=Sum('montant_total_cnas'),
        rembourse=Sum('montant_total_rembourse'),
        charge=Sum('montant_a_charge'),
    )
    
    stats_montants = {
        'facture': montants['facture'] or Decimal('0'),
        'cnas': montants['cnas'] or Decimal('0'),
        'rembourse': montants['rembourse'] or Decimal('0'),
        'charge': montants['charge'] or Decimal('0'),
    }
    
    # ============ STATS RÉCAPS ============
    recaps = RecapSouscripteur.objects.filter(
        periode_debut__gte=date_debut,
        periode_fin__lte=date_fin,
    )
    
    montant_demande = recaps.aggregate(t=Sum('montant_total'))['t'] or Decimal('0')
    montant_recu = recaps.aggregate(t=Sum('montant_recu'))['t'] or Decimal('0')
    
    stats_recaps = {
        'total': recaps.count(),
        'brouillon': recaps.filter(statut='BROUILLON').count(),
        'envoye': recaps.filter(statut='ENVOYE').count(),
        'valide': recaps.filter(statut='VALIDE').count(),
        'paye': recaps.filter(statut='PAYE').count(),
        'rejete': recaps.filter(statut='REJETE').count(),
        'montant_total': montant_demande,
        'montant_recu': montant_recu,
        'ecart': montant_demande - montant_recu,
    }
    
    # ============ STATS VIREMENTS ============
    virements = VirementAdherent.objects.filter(
        date_creation__date__gte=date_debut,
        date_creation__date__lte=date_fin,
    )
    
    stats_virements = {
        'total': virements.count(),
        'a_payer': virements.filter(statut='A_PAYER').count(),
        'paye': virements.filter(statut='PAYE').count(),
        'echec': virements.filter(statut='ECHEC').count(),
        'annule': virements.filter(statut='ANNULE').count(),
        'montant_a_payer': virements.filter(statut='A_PAYER').aggregate(t=Sum('montant'))['t'] or Decimal('0'),
        'montant_paye': virements.filter(statut='PAYE').aggregate(t=Sum('montant'))['t'] or Decimal('0'),
    }
    
    # ============ ALERTES ============
    date_30j = today - timedelta(days=30)
    bulletins_retard = BulletinSoins.objects.filter(
        statut__in=['RECU', 'EN_VERIFICATION', 'VALIDE'],
        date_depot__date__lte=date_30j,
    ).count()
    
    virements_echec = VirementAdherent.objects.filter(statut='ECHEC').count()
    
    date_15j = today - timedelta(days=15)
    recaps_attente = RecapSouscripteur.objects.filter(
        statut__in=['ENVOYE', 'VALIDE'],
        date_envoi__lte=date_15j,
    ).count()
    
    adherents_sans_rib = Adherent.objects.filter(
        statut='ACTIF'
    ).exclude(
        id_adherent__in=CoordonneesBancaires.objects.values_list('adherent_id', flat=True)
    ).count()
    
    alertes = {
        'bulletins_retard': bulletins_retard,
        'virements_echec': virements_echec,
        'recaps_attente': recaps_attente,
        'adherents_sans_rib': adherents_sans_rib,
    }
    
    # ============ GRAPHIQUE ÉVOLUTION (6 mois) ============
    mois_labels = []
    mois_demandes = []
    mois_payes = []
    
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        
        debut_mois = date(y, m, 1)
        fin_mois = date(y, m, monthrange(y, m)[1])
        
        recaps_mois = RecapSouscripteur.objects.filter(
            periode_debut__gte=debut_mois,
            periode_debut__lte=fin_mois,
        )
        
        mois_labels.append(f"{m:02d}/{y}")
        mois_demandes.append(float(recaps_mois.aggregate(t=Sum('montant_total'))['t'] or 0))
        mois_payes.append(float(recaps_mois.aggregate(t=Sum('montant_recu'))['t'] or 0))
    
    # ============ TOP 5 SOUSCRIPTEURS ============
    souscripteurs_stats = []
    for s in Souscripteur.objects.filter(statut='ACTIF'):
        total = RecapSouscripteur.objects.filter(
            souscripteur=s,
            periode_debut__gte=date_debut,
        ).aggregate(t=Sum('montant_total'))['t'] or Decimal('0')
        
        if total > 0:
            souscripteurs_stats.append({
                'nom': s.raison_sociale,
                'montant': float(total),
            })
    
    souscripteurs_stats.sort(key=lambda x: x['montant'], reverse=True)
    souscripteurs_stats = souscripteurs_stats[:5]
    
    # ============ ACTIVITÉ RÉCENTE ============
    derniers_bulletins = BulletinSoins.objects.select_related(
        'patient', 'souscripteur'
    ).order_by('-date_depot')[:5]
    
    derniers_virements = VirementAdherent.objects.select_related(
        'adherent', 'adherent__id_personne'
    ).order_by('-date_creation')[:5]
    
    return render(request, "remboursement/dashboard.html", {
        "periode": periode,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "stats_bulletins": stats_bulletins,
        "stats_montants": stats_montants,
        "stats_recaps": stats_recaps,
        "stats_virements": stats_virements,
        "alertes": alertes,
        "mois_labels": mois_labels,
        "mois_demandes": mois_demandes,
        "mois_payes": mois_payes,
        "souscripteurs_stats": souscripteurs_stats,
        "derniers_bulletins": derniers_bulletins,
        "derniers_virements": derniers_virements,
        "permissions": permissions,
        "page": "remb_dashboard",
    })