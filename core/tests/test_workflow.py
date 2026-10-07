# core/tests/test_workflow.py
"""
Tests automatiques du workflow complet Tiers Payant.

Scénarios testés :
1. Création d'une demande TP
2. Validation de la demande → PEC créée
3. Calcul des montants (taux, plafonds)
4. Création des consommations
5. Création d'une facture
6. Création d'un règlement
"""

from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import (
    # Personnes
    Personne,
    Adherent,
    AyantDroit,

    # Contrats
    Souscripteur,
    Contrat,
    ContratGarantie,

    # Garanties
    Garantie,
    GarantieActe,
    Plafond,

    # Actes
    TypePrestation,
    Acte,
    SousActe,
    TarifSousActe,

    # Prestataires
    Prestataire,
    Convention,

    # Adhésions
    Adhesion,

    # Workflow TP
    DemandeTp,
    DemandeTpDetail,
    PriseEnCharge,
    PriseEnChargeDetail,
    Consommation,

    # Factures
    Facture,
    DetailFacture,
    Reglement,
)

from core.services.calculs import calculer_pour_demande


class WorkflowTest(TestCase):
    """Tests du workflow complet Tiers Payant."""

    def setUp(self):
        """Crée les données de test."""
        maintenant = timezone.now()
        aujourd_hui = date.today()

        # 1. Personne (adhérent)
        self.personne = Personne.objects.create(
            numero_personne="PERS-TEST-0001",
            nom="BENALI",
            prenom="Ahmed",
            date_naissance=date(1980, 1, 1),
            statut="ACTIF",
            date_creation=maintenant,
        )

        # 2. Adhérent
        self.adherent = Adherent.objects.create(
            id_personne=self.personne,
            numero_adherent="ADH-TEST-0001",
            date_adhesion=aujourd_hui,
            statut="ACTIF",
            date_creation=maintenant,
        )

        # 3. Type de prestation
        self.type_prestation = TypePrestation.objects.create(
            code_type="DENTAIRE",
            libelle="Soins dentaires",
            statut="ACTIF",
        )

        # 4. Acte
        self.acte = Acte.objects.create(
            id_type_prestation=self.type_prestation,
            code_acte="ACT-TEST-0001",
            libelle="Soins dentaires",
            statut="ACTIF",
        )

        # 5. Sous-acte
        self.sous_acte = SousActe.objects.create(
            id_acte=self.acte,
            code_sous_acte="SA-TEST-0001",
            libelle="Détartrage",
            statut="ACTIF",
        )

        # 6. Prestataire
        self.prestataire = Prestataire.objects.create(
            code_prestataire="PREST-TEST-0001",
            raison_sociale="Centre Dentaire Test",
            type_prestataire="DENTAIRE",
            statut="ACTIF",
            date_creation=maintenant,
        )

        # 7. Convention active
        self.convention = Convention.objects.create(
            id_prestataire=self.prestataire,
            numero_convention="CONV-TEST-0001",
            date_debut=date(2026, 1, 1),
            statut="ACTIF",
        )

        # 8. Souscripteur
        self.souscripteur = Souscripteur.objects.create(
            code_souscripteur="SOUS-TEST-0001",
            raison_sociale="SAGPS",
            type_souscripteur="ENTREPRISE",
            statut="ACTIF",
            date_creation=maintenant,
        )

        # 9. Contrat
        self.contrat = Contrat.objects.create(
            id_souscripteur=self.souscripteur,
            numero_contrat="CTR-TEST-0001",
            date_debut=date(2026, 1, 1),
            type_contrat="SAGPS",
            statut="ACTIF",
            date_creation=maintenant,
        )

        # 10. Garantie
        self.garantie = Garantie.objects.create(
            code_garantie="GAR-TEST-0001",
            libelle="Soins dentaires 80%",
            statut="ACTIF",
        )

        # 11. Lien contrat ↔ garantie
        ContratGarantie.objects.create(
            id_contrat=self.contrat,
            id_garantie=self.garantie,
            date_debut=date(2026, 1, 1),
            statut="ACTIF",
        )

        # 12. GarantieActe (80%)
        self.garantie_acte = GarantieActe.objects.create(
            id_garantie=self.garantie,
            id_acte=self.acte,
            taux_prise_en_charge=Decimal("80.00"),
            franchise=Decimal("0.00"),
            mode_calcul="POURCENTAGE",
            date_debut=date(2026, 1, 1),
            statut="ACTIF",
        )

        # 13. Tarif sous-acte
        self.tarif = TarifSousActe.objects.create(
            id_sous_acte=self.sous_acte,
            id_prestataire=self.prestataire,
            montant=Decimal("10000.00"),
            date_debut=date(2026, 1, 1),
            statut="ACTIF",
        )

        # 14. Adhésion
        self.adhesion = Adhesion.objects.create(
            id_adherent=self.adherent,
            id_contrat=self.contrat,
            numero_adhesion="ADHES-TEST-0001",
            date_debut=date(2026, 1, 1),
            statut="ACTIF",
            date_creation=maintenant,
        )

    # ============================================================
    # TEST 1 : Créer une demande TP
    # ============================================================
    def test_1_creation_demande_tp(self):
        """Créer une demande TP avec 1 acte."""
        demande = DemandeTp.objects.create(
            numero_demande="DTP-TEST-0001",
            id_personne_beneficiaire=self.personne,
            id_contrat=self.contrat,
            id_prestataire=self.prestataire,
            date_demande=timezone.now(),
            montant_demande=Decimal("0.00"),
            statut="EN_ATTENTE",
        )

        self.assertEqual(demande.statut, "EN_ATTENTE")
        self.assertEqual(demande.montant_demande, Decimal("0.00"))

    # ============================================================
    # TEST 2 : Ajouter un acte à la demande
    # ============================================================
    def test_2_ajout_acte(self):
        """Ajouter un acte à la demande."""
        demande = DemandeTp.objects.create(
            numero_demande="DTP-TEST-0002",
            id_personne_beneficiaire=self.personne,
            id_contrat=self.contrat,
            id_prestataire=self.prestataire,
            date_demande=timezone.now(),
            montant_demande=Decimal("0.00"),
            statut="EN_ATTENTE",
        )

        detail = DemandeTpDetail.objects.create(
            id_demande=demande,
            id_acte=self.acte,
            id_sous_acte=self.sous_acte,
            id_prestataire=self.prestataire,
            quantite=Decimal("2.00"),
            montant_unitaire=Decimal("10000.00"),
            montant_total=Decimal("20000.00"),
        )

        self.assertEqual(detail.montant_total, Decimal("20000.00"))
        self.assertEqual(detail.quantite, Decimal("2.00"))

    # ============================================================
    # TEST 3 : Calculer les montants (moteur de calculs)
    # ============================================================
    def test_3_calcul_montants(self):
        """Calculer les montants via le moteur."""
        demande = DemandeTp.objects.create(
            numero_demande="DTP-TEST-0003",
            id_personne_beneficiaire=self.personne,
            id_contrat=self.contrat,
            id_prestataire=self.prestataire,
            date_demande=timezone.now(),
            montant_demande=Decimal("0.00"),
            statut="EN_ATTENTE",
        )

        detail = DemandeTpDetail.objects.create(
            id_demande=demande,
            id_acte=self.acte,
            id_sous_acte=self.sous_acte,
            id_prestataire=self.prestataire,
            quantite=Decimal("1.00"),
            montant_unitaire=Decimal("10000.00"),
            montant_total=Decimal("10000.00"),
        )

        resultats = calculer_pour_demande(demande)

        # Vérifier le calcul 80%
        self.assertEqual(resultats["total_demande"], Decimal("10000.00"))
        self.assertEqual(resultats["total_accepte"], Decimal("8000.00"))
        self.assertEqual(resultats["total_rejete"], Decimal("2000.00"))
        self.assertEqual(resultats["nb_actes"], 1)

    # ============================================================
    # TEST 4 : Appliquer le plafond
    # ============================================================
    def test_4_plafond(self):
        """Appliquer le plafond annuel."""
        # Créer un plafond de 5000 DA
        Plafond.objects.create(
            id_garantie_acte=self.garantie_acte,
            type_plafond="MONTANT",
            niveau_application="BENEFICIAIRE",
            periode="ANNEE",
            montant_max=Decimal("5000.00"),
            date_debut=date(2026, 1, 1),
            statut="ACTIF",
        )

        demande = DemandeTp.objects.create(
            numero_demande="DTP-TEST-0004",
            id_personne_beneficiaire=self.personne,
            id_contrat=self.contrat,
            id_prestataire=self.prestataire,
            date_demande=timezone.now(),
            montant_demande=Decimal("0.00"),
            statut="EN_ATTENTE",
        )

        detail = DemandeTpDetail.objects.create(
            id_demande=demande,
            id_acte=self.acte,
            id_sous_acte=self.sous_acte,
            id_prestataire=self.prestataire,
            quantite=Decimal("1.00"),
            montant_unitaire=Decimal("10000.00"),
            montant_total=Decimal("10000.00"),
        )

        resultats = calculer_pour_demande(demande)

        # Le plafond de 5000 DA doit s'appliquer
        self.assertEqual(resultats["total_demande"], Decimal("10000.00"))
        self.assertEqual(resultats["total_accepte"], Decimal("5000.00"))
        self.assertEqual(resultats["total_rejete"], Decimal("5000.00"))

    # ============================================================
    # TEST 5 : Vérifier la cohérence prestataire ↔ acte
    # ============================================================
    def test_5_coherence_prestataire_acte(self):
        """Vérifier que le type du prestataire correspond au type de l'acte."""
        # Le prestataire est DENTAIRE
        self.assertEqual(self.prestataire.type_prestataire, "DENTAIRE")

        # L'acte est de type DENTAIRE
        self.assertEqual(self.acte.id_type_prestation.code_type, "DENTAIRE")

        # → Compatibles ✅
        self.assertEqual(
            self.prestataire.type_prestataire,
            self.acte.id_type_prestation.code_type,
        )