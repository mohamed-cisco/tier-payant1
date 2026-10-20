# core/services/plafonds.py
"""
Gestion des plafonds annuels de remboursement.

Ce module calcule et applique les plafonds par bénéficiaire :
- Plafond par acte (ex: Analyses 40 000 DA/an)
- Plafond global annuel (ex: 600 000 DA/an SAGPS)

Utilise les Consommations déjà validées pour calculer
ce qui a déjà été consommé par le bénéficiaire.
"""

from decimal import Decimal
from datetime import date

from core.models import Consommation, Personne


# ============================================================
# FONCTIONS DE CALCUL
# ============================================================

def calculer_deja_consomme(beneficiaire, code_acte, annee=None):
    """
    Calcule le montant déjà remboursé pour un bénéficiaire
    sur un type d'acte, pour une année donnée.

    Args:
        beneficiaire: instance Personne
        code_acte (str): Code de l'acte (ex: "ANALYSES")
        annee (int, optional): Année. Par défaut l'année courante.

    Returns:
        Decimal: Montant total déjà consommé
    """
    if annee is None:
        annee = date.today().year

    # Récupérer toutes les consommations validées du bénéficiaire
    # pour cette année et ce code d'acte
    consommations = Consommation.objects.filter(
        id_personne_beneficiaire=beneficiaire,
        exercice=annee,
        statut="VALIDEE",
        id_acte__code_acte=code_acte,
    )

    total = Decimal("0.00")
    for conso in consommations:
        total += conso.montant_prise_en_charge or Decimal("0.00")

    return total


def calculer_deja_consomme_global(beneficiaire, annee=None):
    """
    Calcule le montant TOTAL déjà remboursé à un bénéficiaire
    pour une année (toutes activités confondues).

    Args:
        beneficiaire: instance Personne
        annee (int, optional): Année

    Returns:
        Decimal: Montant total déjà consommé
    """
    if annee is None:
        annee = date.today().year

    consommations = Consommation.objects.filter(
        id_personne_beneficiaire=beneficiaire,
        exercice=annee,
        statut="VALIDEE",
    )

    total = Decimal("0.00")
    for conso in consommations:
        total += conso.montant_prise_en_charge or Decimal("0.00")

    return total


# ============================================================
# APPLICATION DES PLAFONDS
# ============================================================

def appliquer_plafond_acte(montant_propose, beneficiaire, code_acte, annee=None):
    """
    Applique le plafond annuel par acte en lisant la table Plafond.
    
    Args:
        montant_propose (Decimal): Montant calculé avant plafond
        beneficiaire: instance Personne
        code_acte (str): Code de l'acte (ex: "ACT-2026-0013")
        annee (int, optional): Année de référence
    
    Returns:
        dict: {
            "montant_final": Decimal,
            "plafond_applique": bool,
            "plafond_depasse": bool,
            "details": {...}
        }
    """
    from core.models import Acte, GarantieActe, Plafond
    
    if annee is None:
        annee = date.today().year
    
    # 1. Trouver l'acte par son code
    try:
        acte = Acte.objects.get(code_acte=code_acte)
    except Acte.DoesNotExist:
        # Acte introuvable → pas de plafond
        return {
            "montant_final": montant_propose,
            "plafond_applique": False,
            "plafond_depasse": False,
            "details": None,
        }
    
    # 2. Trouver les GarantieActe actives pour cet acte
    garantie_actes = GarantieActe.objects.filter(
        id_acte=acte,
        statut="ACTIF",
    )
    
    if not garantie_actes.exists():
        return {
            "montant_final": montant_propose,
            "plafond_applique": False,
            "plafond_depasse": False,
            "details": None,
        }
    
    # 3. Chercher un plafond actif dans la table Plafond
    plafond_obj = Plafond.objects.filter(
        id_garantie_acte__in=garantie_actes,
        statut="ACTIF",
        periode="ANNEE",
    ).filter(
        # Vérifier les dates
        date_debut__lte=date(annee, 12, 31),
    ).filter(
        # date_fin NULL ou >= début d'année
        models_Q_date_fin(annee)
    ).order_by("-montant_max").first()
    
    if not plafond_obj or not plafond_obj.montant_max:
        # Aucun plafond trouvé
        return {
            "montant_final": montant_propose,
            "plafond_applique": False,
            "plafond_depasse": False,
            "details": None,
        }
    
    # 4. Calculer le plafond
    plafond = plafond_obj.montant_max
    deja_consomme = calculer_deja_consomme(beneficiaire, code_acte, annee)
    reste_plafond = plafond - deja_consomme
    
    # Si le plafond est déjà dépassé
    if reste_plafond <= 0:
        return {
            "montant_final": Decimal("0.00"),
            "plafond_applique": True,
            "plafond_depasse": True,
            "details": {
                "plafond_annuel": plafond,
                "deja_consomme": deja_consomme,
                "reste": Decimal("0.00"),
                "message": f"Plafond annuel atteint ({plafond} DA)",
            },
        }
    
    # Si le montant proposé dépasse le reste du plafond
    if montant_propose > reste_plafond:
        return {
            "montant_final": reste_plafond,
            "plafond_applique": True,
            "plafond_depasse": True,
            "details": {
                "plafond_annuel": plafond,
                "deja_consomme": deja_consomme,
                "reste": reste_plafond,
                "montant_avant": montant_propose,
                "reduction": montant_propose - reste_plafond,
                "message": f"Plafond partiellement atteint (reste {reste_plafond} DA)",
            },
        }
    
    # Sinon, pas de réduction
    return {
        "montant_final": montant_propose,
        "plafond_applique": True,
        "plafond_depasse": False,
        "details": {
            "plafond_annuel": plafond,
            "deja_consomme": deja_consomme,
            "reste": reste_plafond,
            "message": None,
        },
    }


def models_Q_date_fin(annee):
    """Helper pour filtrer date_fin NULL ou >= fin d'année."""
    from django.db.models import Q
    return Q(date_fin__isnull=True) | Q(date_fin__gte=date(annee, 1, 1))


def appliquer_plafond_global(montant_propose, beneficiaire, plafond_global=None, annee=None):
    """
    Applique le plafond GLOBAL annuel (ex: 600 000 DA SAGPS).

    Args:
        montant_propose (Decimal): Montant
        beneficiaire: instance Personne
        plafond_global (Decimal, optional): Plafond global. Default 600 000
        annee (int, optional): Année

    Returns:
        dict: Même structure que appliquer_plafond_acte
    """
    if annee is None:
        annee = date.today().year

    if plafond_global is None:
        plafond_global = Decimal("600000.00")   # SAGPS par défaut

    deja_consomme = calculer_deja_consomme_global(beneficiaire, annee)
    reste = plafond_global - deja_consomme

    if reste <= 0:
        return {
            "montant_final": Decimal("0.00"),
            "plafond_applique": True,
            "plafond_depasse": True,
            "details": {
                "plafond_global": plafond_global,
                "deja_consomme": deja_consomme,
                "reste": Decimal("0.00"),
                "message": f"Plafond global annuel atteint ({plafond_global} DA)",
            },
        }

    if montant_propose > reste:
        return {
            "montant_final": reste,
            "plafond_applique": True,
            "plafond_depasse": True,
            "details": {
                "plafond_global": plafond_global,
                "deja_consomme": deja_consomme,
                "reste": reste,
                "montant_avant": montant_propose,
                "reduction": montant_propose - reste,
                "message": f"Plafond global partiellement atteint (reste {reste} DA)",
            },
        }

    return {
        "montant_final": montant_propose,
        "plafond_applique": True,
        "plafond_depasse": False,
        "details": {
            "plafond_global": plafond_global,
            "deja_consomme": deja_consomme,
            "reste": reste,
            "message": None,
        },
    }


def appliquer_tous_plafonds(montant_propose, beneficiaire, code_acte, annee=None):
    """
    Applique TOUS les plafonds dans l'ordre :
    1. Plafond par acte (ex: Analyses 40 000 DA)
    2. Plafond global annuel (ex: 600 000 DA)

    Args:
        montant_propose (Decimal): Montant après calcul de base
        beneficiaire: instance Personne
        code_acte (str): Code de l'acte
        annee (int, optional): Année

    Returns:
        dict: {
            "montant_final": Decimal,
            "plafonds": [liste des plafonds appliqués],
            "message": str ou None
        }
    """
    plafonds_appliques = []
    montant_actuel = montant_propose

    # 1. Plafond par acte
    resultat_acte = appliquer_plafond_acte(
        montant_actuel, beneficiaire, code_acte, annee
    )
    montant_actuel = resultat_acte["montant_final"]

    if resultat_acte["plafond_depasse"]:
        plafonds_appliques.append({
            "type": "ACTE",
            "code_acte": code_acte,
            "details": resultat_acte["details"],
        })

    # 2. Plafond global (seulement si le montant n'est pas déjà 0)
    if montant_actuel > 0:
        resultat_global = appliquer_plafond_global(
            montant_actuel, beneficiaire, annee=annee
        )
        montant_actuel = resultat_global["montant_final"]

        if resultat_global["plafond_depasse"]:
            plafonds_appliques.append({
                "type": "GLOBAL",
                "details": resultat_global["details"],
            })

    return {
        "montant_final": montant_actuel,
        "plafonds": plafonds_appliques,
        "message": plafonds_appliques[-1]["details"]["message"] if plafonds_appliques else None,
    }


# ============================================================
# UTILITAIRES
# ============================================================

def lister_plafonds_beneficiaire(beneficiaire, annee=None):
    """
    Liste tous les plafonds d'un bénéficiaire avec leur consommation.

    Returns:
        list: [
            {
                "code_acte": "ANALYSES",
                "libelle": "Analyses médicales",
                "plafond": Decimal("40000.00"),
                "consomme": Decimal("25000.00"),
                "reste": Decimal("15000.00"),
                "pourcentage": 62.5
            },
            ...
        ]
    """
    from core.services.bareme import BAREME_SAGPS

    if annee is None:
        annee = date.today().year

    resultats = []
    for code_acte, regle in BAREME_SAGPS.items():
        plafond = regle.get("plafond_annuel")
        if not plafond:
            continue

        plafond = Decimal(str(plafond))
        consomme = calculer_deja_consomme(beneficiaire, code_acte, annee)
        reste = max(Decimal("0.00"), plafond - consomme)

        pourcentage = Decimal("0.00")
        if plafond > 0:
            pourcentage = (consomme / plafond) * Decimal("100")

        resultats.append({
            "code_acte": code_acte,
            "libelle": regle["libelle"],
            "plafond": plafond,
            "consomme": consomme,
            "reste": reste,
            "pourcentage": round(pourcentage, 2),
        })

    return resultats