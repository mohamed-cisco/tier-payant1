# core/services/calculs.py
"""
Moteur de calcul centralisé pour la plateforme Tiers Payant.

Ce module contient TOUTE la logique de calcul des montants :
- Calcul pour UN acte
- Calcul pour TOUTE une demande
- Application des plafonds
- Gestion des modes (pourcentage, forfait, frais réels)

Utilisé par :
- demande_tp_valider
- prise_en_charge_valider
- consommation_valider
"""

from decimal import Decimal
from datetime import date

from core.models import (
    DemandeTp, DemandeTpDetail,
    GarantieActe, ContratGarantie,
)


# ============================================================
# CALCUL POUR UN ACTE
# ============================================================

def calculer_pour_un_acte(detail, demande, garantie_acte=None):
    """
    Calcule les montants pour UN acte d'une demande.

    Args:
        detail: instance DemandeTpDetail
        demande: instance DemandeTp
        garantie_acte: instance GarantieActe (optionnel - sinon cherché)

    Returns:
        dict: {
            "detail": detail,
            "montant_demande": Decimal,
            "montant_accorde": Decimal,
            "montant_rejete": Decimal,
            "taux": Decimal,
            "franchise": Decimal,
            "garantie_acte": GarantieActe ou None,
            "erreur": str ou None,
        }
    """
    montant_demande = detail.montant_total

    # 1. Trouver la garantie applicable si non fournie
    if garantie_acte is None:
        garantie_acte = _trouver_garantie(detail, demande)

    # 2. Aucune garantie → tout rejeté
    if not garantie_acte:
        return {
            "detail": detail,
            "montant_demande": montant_demande,
            "montant_accorde": Decimal("0.00"),
            "montant_rejete": montant_demande,
            "taux": Decimal("0.00"),
            "franchise": Decimal("0.00"),
            "garantie_acte": None,
            "erreur": "Aucune garantie active trouvée pour cet acte",
        }

    # 3. Calculer le montant brut selon le mode
    try:
        montant_brut = _calculer_montant_brut(detail, garantie_acte)
    except Exception as e:
        return {
            "detail": detail,
            "montant_demande": montant_demande,
            "montant_accorde": Decimal("0.00"),
            "montant_rejete": montant_demande,
            "taux": Decimal("0.00"),
            "franchise": Decimal("0.00"),
            "garantie_acte": garantie_acte,
            "erreur": f"Erreur de calcul : {e}",
        }

    # 4. Appliquer les plafonds
    try:
        from core.services.plafonds import appliquer_tous_plafonds

        resultat_plafonds = appliquer_tous_plafonds(
            montant_brut,
            demande.id_personne_beneficiaire,
            detail.id_acte.code_acte,
            annee=demande.date_demande.year,
        )
        montant_final = resultat_plafonds["montant_final"]

    except Exception as e:
        # En cas d'erreur, on garde le montant brut
        montant_final = montant_brut
        print(f"⚠️ Erreur plafonds pour {detail.id_acte.code_acte}: {e}")

    # 5. Limiter au montant demandé
    montant_final = min(montant_final, montant_demande)
    montant_final = max(montant_final, Decimal("0.00"))

    # 6. Calculer le rejeté
    montant_rejete = montant_demande - montant_final

    # 7. Taux et franchise (pour info)
    taux = garantie_acte.taux_prise_en_charge or Decimal("0.00")
    franchise = garantie_acte.franchise or Decimal("0.00")

    return {
        "detail": detail,
        "montant_demande": montant_demande,
        "montant_accorde": montant_final,
        "montant_rejete": montant_rejete,
        "taux": taux,
        "franchise": franchise,
        "garantie_acte": garantie_acte,
        "erreur": None,
    }


# ============================================================
# CALCUL POUR TOUTE UNE DEMANDE
# ============================================================

def calculer_pour_demande(demande):
    """
    Calcule les montants pour TOUS les actes d'une demande.

    Args:
        demande: instance DemandeTp

    Returns:
        dict: {
            "calculs": [liste de calculs par acte],
            "total_demande": Decimal,
            "total_accepte": Decimal,
            "total_rejete": Decimal,
            "erreurs": [liste d'erreurs],
            "nb_actes": int,
        }
    """
    details = list(
        DemandeTpDetail.objects
        .select_related("id_acte", "id_sous_acte")
        .filter(id_demande=demande)
        .order_by("id_detail")
    )

    calculs = []
    erreurs = []
    total_demande = Decimal("0.00")
    total_accepte = Decimal("0.00")
    total_rejete = Decimal("0.00")

    for detail in details:
        try:
            calcul = calculer_pour_un_acte(detail, demande)
            calculs.append(calcul)

            total_demande += calcul["montant_demande"]
            total_accepte += calcul["montant_accorde"]
            total_rejete += calcul["montant_rejete"]

            if calcul["erreur"]:
                erreurs.append(
                    f"{detail.id_acte.code_acte}: {calcul['erreur']}"
                )

        except Exception as e:
            erreurs.append(f"Erreur sur acte {detail.id_acte.code_acte}: {e}")

    return {
        "calculs": calculs,
        "total_demande": total_demande,
        "total_accepte": total_accepte,
        "total_rejete": total_rejete,
        "erreurs": erreurs,
        "nb_actes": len(details),
    }


# ============================================================
# FONCTIONS INTERNES
# ============================================================

def _trouver_garantie(detail, demande):
    """
    Trouve la GarantieActe applicable pour un acte d'une demande.

    Critères :
    - L'acte correspond
    - La garantie est liée au contrat de la demande
    - La garantie est active à la date de la demande
    """
    date_ref = demande.date_demande.date()

    garantie_acte = (
        GarantieActe.objects
        .filter(
            id_acte=detail.id_acte,
            statut="ACTIF",
            date_debut__lte=date_ref,
            id_garantie__contratgarantie__id_contrat=demande.id_contrat,
            id_garantie__contratgarantie__statut="ACTIF",
        )
        .filter(
            models_Q_date_fin(date_ref)
        )
        .order_by("-date_debut")
        .first()
    )

    return garantie_acte


def models_Q_date_fin(date_ref):
    """Helper pour filtrer les date_fin NULL ou >= date_ref."""
    from django.db.models import Q
    return Q(date_fin__isnull=True) | Q(date_fin__gte=date_ref)


def _calculer_montant_brut(detail, garantie_acte):
    """
    Calcule le montant brut selon le mode de la garantie.

    Modes :
    - POURCENTAGE : montant × taux / 100 - franchise
    - FORFAIT : montant_forfait fixe (limité au montant)
    - FRAIS_REELS : 100% du montant
    """
    montant_total = detail.montant_total
    mode = getattr(garantie_acte, "mode_calcul", "POURCENTAGE") or "POURCENTAGE"

    if mode == "FORFAIT":
        montant_forfait = getattr(garantie_acte, "montant_forfait", None)
        if montant_forfait:
            montant = min(Decimal(str(montant_forfait)), montant_total)
        else:
            montant = montant_total

        # Appliquer plafond_forfait si défini
        plafond_forfait = getattr(garantie_acte, "plafond_forfait", None)
        if plafond_forfait:
            montant = min(montant, Decimal(str(plafond_forfait)))

        return montant

    elif mode == "FRAIS_REELS":
        return montant_total

    else:  # POURCENTAGE (défaut)
        taux = garantie_acte.taux_prise_en_charge or Decimal("0.00")
        franchise = garantie_acte.franchise or Decimal("0.00")

        # 1. Appliquer la franchise d'abord
        base = max(Decimal("0.00"), montant_total - franchise)

        # 2. Appliquer le taux
        montant = base * taux / Decimal("100")

        return montant


# ============================================================
# UTILITAIRES
# ============================================================

def formater_montant(montant):
    """Formate un montant en DA."""
    if montant is None:
        montant = Decimal("0.00")
    return f"{montant:,.2f} DA".replace(",", " ")


def tester_calcul_simple():
    """
    Fonction de test rapide.
    À lancer dans le shell : python manage.py shell
    >>> from core.services.calculs import tester_calcul_simple
    >>> tester_calcul_simple()
    """
    from core.models import DemandeTp

    demande = DemandeTp.objects.last()
    if not demande:
        print("Aucune demande trouvée.")
        return

    print(f"\n📋 Demande : {demande.numero_demande}")
    print(f"👤 Bénéficiaire : {demande.id_personne_beneficiaire.nom}")
    print(f"📄 Contrat : {demande.id_contrat.numero_contrat}")

    resultats = calculer_pour_demande(demande)

    print(f"\n📊 RÉSULTATS :")
    print(f"  Nombre d'actes : {resultats['nb_actes']}")
    print(f"  Total demandé  : {formater_montant(resultats['total_demande'])}")
    print(f"  Total accepté  : {formater_montant(resultats['total_accepte'])}")
    print(f"  Total rejeté   : {formater_montant(resultats['total_rejete'])}")

    if resultats['erreurs']:
        print(f"\n⚠️ ERREURS :")
        for err in resultats['erreurs']:
            print(f"  - {err}")

    print(f"\n📋 DÉTAIL PAR ACTE :")
    for calc in resultats['calculs']:
        acte = calc['detail'].id_acte
        print(f"  • {acte.code_acte} - {acte.libelle}")
        print(f"      Demandé : {formater_montant(calc['montant_demande'])}")
        print(f"      Accepté : {formater_montant(calc['montant_accorde'])}")
        print(f"      Rejeté  : {formater_montant(calc['montant_rejete'])}")
        if calc['erreur']:
            print(f"      ⚠️ {calc['erreur']}")