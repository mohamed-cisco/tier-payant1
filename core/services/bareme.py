# core/services/bareme.py
"""
Barème de remboursement des frais de santé.

Ce fichier contient les RÈGLES de remboursement issues de :
- Contrat SAGPS-TALA (assurance groupe) : 90% des frais réels
- Barème CNL (santé complémentaire) : forfaits fixes

Chaque règle définit :
- mode : POURCENTAGE / FORFAIT / FRAIS_REELS
- taux ou montant_forfait
- plafond_annuel : plafond par bénéficiaire
- code : référence unique
"""

from decimal import Decimal


# ============================================================
# BARÈME SAGPS-TALA — Assurance groupe
# Règle : 90% des frais réels + plafonds annuels
# Plafond global : 600 000 DA/an par assuré
# ============================================================

BAREME_SAGPS = {
    # ----- CONSULTATIONS -----
    "CONSULTATION_GENERALISTE": {
        "libelle": "Consultation généraliste",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": None,
    },
    "CONSULTATION_SPECIALISTE": {
        "libelle": "Consultation spécialiste",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": None,
    },

    # ----- ACTES EXPLORATOIRES -----
    "RADIOGRAPHIE": {
        "libelle": "Radiographie (Scanner & IRM inclus)",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("20000.00"),
    },
    "ECHOGRAPHIE": {
        "libelle": "Échographie (examen vasculaire inclus)",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("10000.00"),
    },
    "ANALYSES": {
        "libelle": "Analyses médicales",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("40000.00"),
    },

    # ----- ACTES DE SPÉCIALISTES -----
    "KINESITHERAPIE": {
        "libelle": "Kinésithérapie",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("600.00"),
        "limite_seances": 15,
        "plafond_annuel": None,
    },
    "INFIRMIER": {
        "libelle": "Actes infirmiers",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("600.00"),
        "plafond_annuel": None,
    },
    "ORTHOPHONIE": {
        "libelle": "Orthophonie",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("150.00"),
        "limite_seances": 10,
        "plafond_annuel": None,
    },
    "PETITE_CHIRURGIE": {
        "libelle": "Petite chirurgie",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("10000.00"),
    },

    # ----- HOSPITALISATION -----
    "HONORAIRES_CHIRURGICAUX": {
        "libelle": "Honoraires chirurgicaux",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("100000.00"),
    },
    "FRAIS_SEJOUR_CLINIQUE": {
        "libelle": "Frais de séjour en clinique",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("20000.00"),
    },

    # ----- MATERNITÉ -----
    "CONSULTATION_PRENATALE": {
        "libelle": "Consultation pré/post-natale",
        "mode": "FRAIS_REELS",
        "taux": Decimal("100.00"),
        "plafond_annuel": None,
    },
    "ECHOGRAPHIE_GROSSESSE": {
        "libelle": "Échographie de grossesse",
        "mode": "FRAIS_REELS",
        "taux": Decimal("100.00"),
        "plafond_annuel": None,
    },
    "ACCOUCHEMENT_NORMAL": {
        "libelle": "Accouchement normal",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("80000.00"),
        "plafond_annuel": None,
    },
    "ACCOUCHEMENT_CESARIENNE": {
        "libelle": "Accouchement avec césarienne",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("100000.00"),
        "plafond_annuel": None,
    },
    "FRAIS_SEJOUR_MATERNITE": {
        "libelle": "Frais de séjour en maternité",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("15000.00"),
    },

    # ----- PHARMACIE -----
    "VIGNETTES_VERTES": {
        "libelle": "Vignettes vertes",
        "mode": "POURCENTAGE",
        "taux": Decimal("20.00"),
        "plafond_annuel": None,
    },
    "VIGNETTES_ROUGES": {
        "libelle": "Vignettes rouges",
        "mode": "POURCENTAGE",
        "taux": Decimal("80.00"),
        "plafond_annuel": Decimal("20000.00"),
    },
    "VIGNETTES_BLANCHES": {
        "libelle": "Vignettes blanches",
        "mode": "POURCENTAGE",
        "taux": Decimal("50.00"),
        "plafond_annuel": Decimal("8000.00"),
    },

    # ----- LUNETTERIE -----
    "VERRES_OPTIQUES": {
        "libelle": "Verres optiques ordinaires/progressifs",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("25000.00"),
    },
    "LENTILLES": {
        "libelle": "Lentilles de contact thérapeutiques",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("100000.00"),
    },

    # ----- DENTAIRE -----
    "SOINS_DENTAIRES": {
        "libelle": "Soins dentaires",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("100000.00"),
    },
    "PROTHESE_DENTAIRE": {
        "libelle": "Prothèse dentaire",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("100000.00"),
    },
    "ORTHODONTIE": {
        "libelle": "Orthodontie (enfants < 16 ans)",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("100000.00"),
    },

    # ----- PROTHÈSES -----
    "PROTHESE_AUDITIVE": {
        "libelle": "Prothèse auditive",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("20000.00"),
    },
    "PROTHESE_ORTHOPEDIQUE": {
        "libelle": "Prothèse orthopédique",
        "mode": "POURCENTAGE",
        "taux": Decimal("90.00"),
        "plafond_annuel": Decimal("20000.00"),
    },

    # ----- CURE THERMALE -----
    "CURE_THERMALE": {
        "libelle": "Cure thermale",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("1000.00"),   # par nuit
        "plafond_annuel": Decimal("15000.00"),   # max 15 jours
    },
}


# ============================================================
# BARÈME CNL — Santé complémentaire
# Règle : montants forfaitaires fixes
# ============================================================

BAREME_CNL = {
    # ----- CONSULTATIONS -----
    "CONSULTATION_GENERALISTE": {
        "libelle": "Consultation généraliste",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("1500.00"),
        "plafond_annuel": None,
    },
    "CONSULTATION_SPECIALISTE": {
        "libelle": "Consultation spécialiste",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("2000.00"),
        "plafond_annuel": None,
    },

    # ----- EXPLORATIONS -----
    "RADIOGRAPHIE": {
        "libelle": "Radiographie standard",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("2000.00"),
        "plafond_annuel": Decimal("35000.00"),
    },
    "ECHOGRAPHIE": {
        "libelle": "Échographie",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("2500.00"),
        "plafond_annuel": Decimal("35000.00"),
    },
    "SCANNER": {
        "libelle": "Scanner",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("15000.00"),
        "plafond_annuel": Decimal("35000.00"),
    },
    "IRM": {
        "libelle": "IRM",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("15000.00"),
        "plafond_annuel": Decimal("35000.00"),
    },
    "ANALYSES": {
        "libelle": "Analyses médicales",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("4000.00"),
        "plafond_annuel": Decimal("35000.00"),
    },

    # ----- HOSPITALISATION -----
    "HOSPITALISATION_CHIRURGICALE": {
        "libelle": "Hospitalisation chirurgicale",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("100000.00"),
        "plafond_annuel": Decimal("100000.00"),
    },
    "HOSPITALISATION_MEDICALE": {
        "libelle": "Hospitalisation médicale",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("30000.00"),
        "plafond_annuel": Decimal("30000.00"),
    },
    "FRAIS_SEJOUR": {
        "libelle": "Frais de séjour (jusqu'à 3 jours)",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("5000.00"),   # par jour
        "plafond_annuel": Decimal("15000.00"),
    },

    # ----- PHARMACIE -----
    "VIGNETTES_VERTES": {
        "libelle": "Vignettes vertes",
        "mode": "POURCENTAGE",
        "taux": Decimal("20.00"),
        "plafond_annuel": None,
    },
    "VIGNETTES_ROUGES": {
        "libelle": "Vignettes rouges",
        "mode": "POURCENTAGE",
        "taux": Decimal("50.00"),
        "plafond_annuel": Decimal("10000.00"),
    },

    # ----- DENTAIRE -----
    "CHIRURGIE_DENTAIRE": {
        "libelle": "Chirurgie dentaire",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("2000.00"),
        "plafond_annuel": Decimal("30000.00"),
    },
    "CONSULTATION_DENTAIRE": {
        "libelle": "Consultation dentaire",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("1200.00"),
        "plafond_annuel": Decimal("30000.00"),
    },
    "SOINS_DENTAIRES": {
        "libelle": "Soins dentaires",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("2500.00"),
        "plafond_annuel": Decimal("30000.00"),
    },

    # ----- PROTHÈSES -----
    "PROTHESE_DENTAIRE": {
        "libelle": "Prothèse dentaire",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("15000.00"),
        "plafond_annuel": Decimal("15000.00"),
    },
    "PROTHESE_AUDITIVE": {
        "libelle": "Prothèse auditive",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("20000.00"),
        "plafond_annuel": Decimal("20000.00"),
    },
    "PROTHESE_ORTHOPEDIQUE": {
        "libelle": "Prothèse orthopédique",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("20000.00"),
        "plafond_annuel": Decimal("20000.00"),
    },

    # ----- OPTIQUE -----
    "VERRES_OPTIQUES": {
        "libelle": "Verres optiques",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("6000.00"),
        "plafond_annuel": None,
        "limite_annuelle": 1,   # 1 fois par an
    },
    "LENTILLES": {
        "libelle": "Lentilles de contact thérapeutiques",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("6000.00"),
        "plafond_annuel": None,
        "limite_annuelle": 1,
    },

    # ----- MATERNITÉ -----
    "ECHOGRAPHIE_GROSSESSE": {
        "libelle": "Échographie de grossesse",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("2000.00"),
        "plafond_annuel": None,
    },
    "ACCOUCHEMENT_NORMAL": {
        "libelle": "Accouchement sans complication",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("40000.00"),
        "plafond_annuel": None,
    },
    "ACCOUCHEMENT_CESARIENNE": {
        "libelle": "Accouchement avec complication",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("60000.00"),
        "plafond_annuel": None,
    },
    "FRAIS_SEJOUR_MATERNITE": {
        "libelle": "Frais de séjour maternité",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("5000.00"),  # par jour
        "plafond_annuel": Decimal("15000.00"),
    },

    # ----- ACTES COURANTS -----
    "PETITE_CHIRURGIE": {
        "libelle": "Petite chirurgie",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("1500.00"),
        "plafond_annuel": None,
    },
    "KINESITHERAPIE": {
        "libelle": "Kinésithérapie",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("800.00"),   # par séance
        "limite_seances": 10,
        "plafond_annuel": None,
    },
    "INFIRMIER": {
        "libelle": "Actes infirmiers",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("800.00"),
        "plafond_annuel": None,
    },
}


# ============================================================
# BARÈME ASCENDANTS (personnes âgées)
# ============================================================

BAREME_ASCENDANTS = {
    "CONSULTATION_GENERALISTE": {
        "libelle": "Consultation généraliste",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("900.00"),
    },
    "CONSULTATION_SPECIALISTE": {
        "libelle": "Consultation spécialiste",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("1200.00"),
    },
    "RADIOGRAPHIE": {
        "libelle": "Radiographie",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("8000.00"),
        "plafond_annuel": Decimal("8000.00"),
    },
    "ECHOGRAPHIE": {
        "libelle": "Échographie",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("5000.00"),
        "plafond_annuel": Decimal("5000.00"),
    },
    "ANALYSES": {
        "libelle": "Analyses",
        "mode": "FORFAIT",
        "montant_forfait": Decimal("10000.00"),
        "plafond_annuel": Decimal("10000.00"),
    },
}


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def get_bareme(type_contrat):
    """
    Retourne le barème correspondant au type de contrat.
    
    Args:
        type_contrat (str): "SAGPS", "CNL", "ASCENDANTS"
    
    Returns:
        dict: Le barème complet
    """
    baremes = {
        "SAGPS": BAREME_SAGPS,
        "CNL": BAREME_CNL,
        "ASCENDANTS": BAREME_ASCENDANTS,
    }
    return baremes.get(type_contrat.upper(), BAREME_SAGPS)


def get_regle(type_contrat, code_acte):
    """
    Retourne la règle applicable pour un acte donné.
    
    Args:
        type_contrat (str): Type de contrat
        code_acte (str): Code de l'acte (ex: "ANALYSES")
    
    Returns:
        dict ou None: La règle si trouvée
    """
    bareme = get_bareme(type_contrat)
    return bareme.get(code_acte.upper())


def lister_codes_actes(type_contrat="SAGPS"):
    """
    Liste tous les codes d'actes disponibles dans un barème.
    """
    bareme = get_bareme(type_contrat)
    return list(bareme.keys())