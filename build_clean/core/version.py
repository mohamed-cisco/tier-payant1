"""
Système de versioning de la plateforme Tiers Payant.

Chaque mise à jour doit être documentée ici.
"""

# ============================================================
# VERSION ACTUELLE
# ============================================================

VERSION = "1.1.0"
DATE_VERSION = "2026-10-08"
NOM_VERSION = "Rapports & Refactoring"

# ============================================================
# HISTORIQUE DES VERSIONS
# ============================================================

HISTORIQUE = [
    {
        "version": "1.0.0",
        "date": "2026-10-01",
        "nom": "Version initiale",
        "description": "Plateforme de base fonctionnelle",
        "changements": [
            "Workflow TP complet (demande → PEC → facture)",
            "Gestion des adhérents et ayants droit",
            "Gestion des contrats et garanties",
            "Génération de 7 PDF",
        ],
    },
    {
        "version": "1.0.1",
        "date": "2026-10-05",
        "nom": "Corrections bugs",
        "description": "Correction de bugs identifiés",
        "changements": [
            "Correction du moteur de calculs",
            "Correction des plafonds",
            "Correction du workflow de validation",
        ],
    },
    {
        "version": "1.1.0",
        "date": "2026-10-08",
        "nom": "Rapports & Refactoring",
        "description": "Ajout du module Rapports et refactoring complet",
        "changements": [
            "⭐ Nouveau : Module Rapports (7 rapports)",
            "⭐ Nouveau : Export PDF pour tous les rapports",
            "⭐ Nouveau : Export Excel pour tous les rapports",
            "🔧 Découpage de views.py en 26 modules",
            "🔧 Module de calculs centralisé (services/)",
            "🔧 20 tests automatiques",
            "🔧 14 plafonds configurés",
            "🔧 Cohérence métier (prestataire ↔ acte)",
            "🔧 Système de déploiement automatique",
            "🔧 Système de backup automatique",
        ],
    },
]


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def get_version():
    """Retourne la version actuelle."""
    return VERSION


def get_date_version():
    """Retourne la date de la version."""
    return DATE_VERSION


def get_nom_version():
    """Retourne le nom de la version."""
    return NOM_VERSION


def get_historique():
    """Retourne l'historique complet (du plus récent au plus ancien)."""
    return sorted(HISTORIQUE, key=lambda v: v["date"], reverse=True)


def get_derniere_version():
    """Retourne la dernière version."""
    return HISTORIQUE[-1] if HISTORIQUE else None
