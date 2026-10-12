# reset_remboursement.py
"""
Script de reset du module Remboursement.
Supprime tous les récaps et virements, remet les bulletins en VALIDE.
À supprimer après usage.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from remboursement.models import (
    RecapSouscripteur, VirementAdherent, BulletinSoins
)
from django.db import transaction

print("=== RESET DU MODULE REMBOURSEMENT ===\n")

with transaction.atomic():
    # 1. Supprimer tous les virements
    nb_virements = VirementAdherent.objects.count()
    VirementAdherent.objects.all().delete()
    print(f"✅ Virements supprimés : {nb_virements}")
    
    # 2. Détacher tous les bulletins des récaps
    nb_bulletins_detaches = BulletinSoins.objects.filter(recap__isnull=False).count()
    BulletinSoins.objects.all().update(recap=None)
    print(f"✅ Bulletins détachés : {nb_bulletins_detaches}")
    
    # 3. Remettre tous les bulletins en VALIDE
    nb_bulletins = BulletinSoins.objects.count()
    BulletinSoins.objects.all().update(statut='VALIDE')
    print(f"✅ Bulletins remis en VALIDE : {nb_bulletins}")
    
    # 4. Supprimer tous les récaps
    nb_recaps = RecapSouscripteur.objects.count()
    RecapSouscripteur.objects.all().delete()
    print(f"✅ Récaps supprimés : {nb_recaps}")

print("\n=== RÉSULTAT ===")
print(f"Récaps restants    : {RecapSouscripteur.objects.count()}")
print(f"Virements restants : {VirementAdherent.objects.count()}")
print(f"Bulletins VALIDE   : {BulletinSoins.objects.filter(statut='VALIDE').count()}")
print(f"Bulletins total    : {BulletinSoins.objects.count()}")

print("\n=== TERMINÉ ===")