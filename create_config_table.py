# create_config_table.py
"""Crée la table config_cnas dans PostgreSQL."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

SQL = """
CREATE TABLE IF NOT EXISTS config_cnas (
    id BIGSERIAL PRIMARY KEY,
    forfait NUMERIC(10, 2) NOT NULL DEFAULT 0,
    taux_pourcentage NUMERIC(5, 2) NOT NULL DEFAULT 0,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    date_modification TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    type_prestation_id BIGINT NOT NULL UNIQUE
        REFERENCES type_prestation(id_type_prestation)
        ON DELETE CASCADE
);
"""

print("=== Création de la table config_cnas ===")
with connection.cursor() as cursor:
    try:
        cursor.execute(SQL)
        print("OK : Table config_cnas créée")
    except Exception as e:
        print("ERREUR :", e)
        raise

# Vérification
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'config_cnas'
        ORDER BY ordinal_position;
    """)
    cols = cursor.fetchall()
    print("\n=== Colonnes de config_cnas ===")
    for col in cols:
        print(f"  - {col[0]} ({col[1]})")

print("\n=== TERMINE ===")