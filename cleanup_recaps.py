# cleanup_recaps.py
"""
Nettoyage complet des récaps et virements en doublon.
Remet les bulletins en VALIDE pour repartir sur des bases saines.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from remboursement.models import (
    RecapSouscripteur, VirementAdherent, BulletinSoins
)
from django.db import transaction

print("=== NETTOYAGE COMPLET ===\n")

with transaction.atomic():
    # 1. Voir l'état AVANT
    print("--- AVANT NETTOYAGE ---")
    print(f"Récaps : {RecapSouscripteur.objects.count()}")
    print(f"Virements : {VirementAdherent.objects.count()}")
    print(f"Bulletins : {BulletinSoins.objects.count()}")
    print()
    
    # 2. Supprimer TOUS les virements
    nb_virements = VirementAdherent.objects.count()
    VirementAdherent.objects.all().delete()
    print(f"✅ Virements supprimés : {nb_virements}")
    
    # 3. Détacher TOUS les bulletins des récaps
    nb_detaches = BulletinSoins.objects.filter(recap__isnull=False).count()
    BulletinSoins.objects.all().update(recap=None)
    print(f"✅ Bulletins détachés : {nb_detaches}")
    
    # 4. Remettre les bulletins en VALIDE
    nb_valides = BulletinSoins.objects.count()
    BulletinSoins.objects.all().update(statut='VALIDE')
    print(f"✅ Bulletins remis en VALIDE : {nb_valides}")
    
    # 5. Supprimer TOUS les récaps
    nb_recaps = RecapSouscripteur.objects.count()
    RecapSouscripteur.objects.all().delete()
    print(f"✅ Récaps supprimés : {nb_recaps}")

print("\n--- APRÈS NETTOYAGE ---")
print(f"Récaps restants : {RecapSouscripteur.objects.count()}")
print(f"Virements restants : {VirementAdherent.objects.count()}")
print(f"Bulletins VALIDE : {BulletinSoins.objects.filter(statut='VALIDE').count()}")
print(f"Bulletins total : {BulletinSoins.objects.count()}")

print("\n=== TERMINE ===")