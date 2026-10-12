# rename_config_col.py
"""Renomme type_prestation_id en id_type_prestation."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

print("=== Renommage de la colonne ===")
with connection.cursor() as cursor:
    try:
        cursor.execute("ALTER TABLE config_cnas RENAME COLUMN type_prestation_id TO id_type_prestation;")
        print("OK : Colonne renommée")
    except Exception as e:
        print("ERREUR :", e)
        raise

# Vérification
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'config_cnas'
        ORDER BY ordinal_position;
    """)
    cols = cursor.fetchall()
    print("\n=== Colonnes de config_cnas ===")
    for col in cols:
        print(f"  - {col[0]}")

print("\n=== TERMINE ===")