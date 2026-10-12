# drop_tables.py
"""
Script temporaire pour supprimer les tables de l'app remboursement
et les modèles en doublon de core.
À supprimer après usage.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

# Tables à supprimer
TABLES = [
    # App remboursement
    'remb_virement_bulletins',
    'remb_piece_jointe',
    'remb_ligne_bulletin',
    'remb_bulletin_soins',
    'remb_virement_adherent',
    'remb_recap_compagnie',
    'remb_bareme',
    'remb_regle_bareme',
    # Doublons core
    'compagnie_assurance',
    'entreprise_cliente',
]

print("=== Suppression des tables ===")
with connection.cursor() as cursor:
    for table in TABLES:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print(f"  OK : {table}")
        except Exception as e:
            print(f"  ERREUR sur {table} : {e}")

print("\n=== Vérification ===")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND (
            table_name LIKE 'remb_%' 
            OR table_name IN ('compagnie_assurance', 'entreprise_cliente')
        )
        ORDER BY table_name;
    """)
    rows = cursor.fetchall()
    
    if not rows:
        print("  Aucune table restante")
    else:
        print("  Tables restantes :")
        for row in rows:
            print(f"    - {row[0]}")

print("\n=== TERMINÉ ===")