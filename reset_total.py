# reset_total.py
"""
RESET TOTAL du module Remboursement.
Supprime TOUT : bulletins, lignes, pièces, récaps, virements.
À supprimer après usage.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from remboursement.models import (
    BulletinSoins, LigneBulletin, PieceJointe,
    RecapSouscripteur, VirementAdherent
)
from django.db import transaction

print("=== RESET TOTAL DU MODULE REMBOURSEMENT ===\n")

with transaction.atomic():
    # 1. Supprimer les virements
    nb = VirementAdherent.objects.count()
    VirementAdherent.objects.all().delete()
    print(f"OK Virements supprimes : {nb}")
    
    # 2. Supprimer les recaps
    nb = RecapSouscripteur.objects.count()
    RecapSouscripteur.objects.all().delete()
    print(f"OK Recaps supprimes : {nb}")
    
    # 3. Supprimer les pieces jointes
    nb = PieceJointe.objects.count()
    PieceJointe.objects.all().delete()
    print(f"OK Pieces jointes supprimees : {nb}")
    
    # 4. Supprimer les lignes de bulletins
    nb = LigneBulletin.objects.count()
    LigneBulletin.objects.all().delete()
    print(f"OK Lignes de bulletins supprimees : {nb}")
    
    # 5. Supprimer les bulletins de soins
    nb = BulletinSoins.objects.count()
    BulletinSoins.objects.all().delete()
    print(f"OK Bulletins de soins supprimes : {nb}")

print("\n=== RESULTAT ===")
print(f"Bulletins restants  : {BulletinSoins.objects.count()}")
print(f"Lignes restantes    : {LigneBulletin.objects.count()}")
print(f"Pieces restantes    : {PieceJointe.objects.count()}")
print(f"Recaps restants     : {RecapSouscripteur.objects.count()}")
print(f"Virements restants  : {VirementAdherent.objects.count()}")

print("\n=== TERMINE ===")