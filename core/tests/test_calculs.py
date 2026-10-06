# core/tests/test_calculs.py
"""
Tests unitaires pour le moteur de calcul.
"""

from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.utils import timezone

from core.models import (
    Personne, Souscripteur, Contrat, ContratGarantie,
    Garantie, Acte, TypePrestation, GarantieActe,
    Prestataire, DemandeTp, DemandeTpDetail,
)
from core.services.calculs import calculer_pour_un_acte, calculer_pour_demande
from core.services.bareme import get_regle, lister_codes_actes


class CalculsTest(TestCase):

    def setUp(self):
        maintenant = timezone.now()

        self.personne = Personne.objects.create(
            numero_personne="PERS-0001",
            nom="BENALI",
            prenom="Ahmed",
            date_naissance=date(1980, 1, 1),
            statut="ACTIF",
            date_creation=maintenant,
        )

        self.type_prestation = TypePrestation.objects.create(
            code_type="TYPE-ANALYSES",
            libelle="Analyses medicales",
            statut="ACTIF",
        )

        self.acte_analyses = Acte.objects.create(
            id_type_prestation=self.type_prestation,
            code_acte="ANALYSES",
            libelle="Analyses medicales",
            statut="ACTIF",
        )

        self.prestataire = Prestataire.objects.create(
            code_prestataire="PREST-001",
            raison_sociale="Laboratoire El Amel",
            type_prestataire="LABORATOIRE",
            statut="ACTIF",
            date_creation=maintenant,
        )

        self.souscripteur = Souscripteur.objects.create(
            code_souscripteur="SOUS-001",
            raison_sociale="SAGPS",
            type_souscripteur="ENTREPRISE",
            statut="ACTIF",
            date_creation=maintenant,
        )

        self.contrat = Contrat.objects.create(
            id_souscripteur=self.souscripteur,
            numero_contrat="CTR-2026-0001",
            date_debut=date(2026, 1, 1),
            type_contrat="SAGPS",
            statut="ACTIF",
            date_creation=maintenant,
        )

        self.garantie = Garantie.objects.create(
            code_garantie="GAR-ANALYSES",
            libelle="Analyses 90%",
            statut="ACTIF",
        )

        ContratGarantie.objects.create(
            id_contrat=self.contrat,
            id_garantie=self.garantie,
            date_debut=date(2026, 1, 1),
            statut="ACTIF",
        )

        self.garantie_acte = GarantieActe.objects.create(
            id_garantie=self.garantie,
            id_acte=self.acte_analyses,
            taux_prise_en_charge=Decimal("90.00"),
            franchise=Decimal("0.00"),
            mode_calcul="POURCENTAGE",
            date_debut=date(2026, 1, 1),
            statut="ACTIF",
        )

    def _creer_demande(self):
        return DemandeTp.objects.create(
            numero_demande=f"DTP-TEST-{DemandeTp.objects.count() + 1}",
            id_personne_beneficiaire=self.personne,
            id_contrat=self.contrat,
            id_prestataire=self.prestataire,
            date_demande=timezone.now(),
            montant_demande=Decimal("0.00"),
            statut="EN_ATTENTE",
        )

    def _creer_detail(self, demande, montant_unitaire, quantite=1):
        return DemandeTpDetail.objects.create(
            id_demande=demande,
            id_acte=self.acte_analyses,
            id_prestataire=self.prestataire,
            quantite=Decimal(str(quantite)),
            montant_unitaire=montant_unitaire,
            montant_total=montant_unitaire * Decimal(str(quantite)),
        )

    # ===== TESTS =====

    def test_1_pourcentage_90(self):
        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("9000.00"))
        self.assertEqual(calcul["montant_rejete"], Decimal("1000.00"))
        self.assertEqual(calcul["taux"], Decimal("90.00"))
        self.assertIsNone(calcul["erreur"])

    def test_2_aucune_garantie(self):
        self.garantie_acte.delete()
        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("0.00"))
        self.assertEqual(calcul["montant_rejete"], Decimal("10000.00"))
        self.assertIsNotNone(calcul["erreur"])

    def test_3_mode_forfait(self):
        self.garantie_acte.mode_calcul = "FORFAIT"
        self.garantie_acte.montant_forfait = Decimal("5000.00")
        self.garantie_acte.save()

        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("5000.00"))

    def test_4_mode_frais_reels(self):
        self.garantie_acte.mode_calcul = "FRAIS_REELS"
        self.garantie_acte.save()

        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("10000.00"))

    def test_5_franchise(self):
        self.garantie_acte.franchise = Decimal("2000.00")
        self.garantie_acte.save()

        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("7200.00"))

    def test_6_quantite(self):
        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("2000.00"), quantite=5)

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_demande"], Decimal("10000.00"))
        self.assertEqual(calcul["montant_accorde"], Decimal("9000.00"))

    def test_7_forfait_superieur(self):
        self.garantie_acte.mode_calcul = "FORFAIT"
        self.garantie_acte.montant_forfait = Decimal("15000.00")
        self.garantie_acte.save()

        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("10000.00"))

    def test_8_plusieurs_actes(self):
        demande = self._creer_demande()
        self._creer_detail(demande, Decimal("10000.00"))
        self._creer_detail(demande, Decimal("5000.00"))
        self._creer_detail(demande, Decimal("3000.00"))

        resultats = calculer_pour_demande(demande)

        self.assertEqual(resultats["nb_actes"], 3)
        self.assertEqual(resultats["total_demande"], Decimal("18000.00"))
        self.assertEqual(resultats["total_accepte"], Decimal("16200.00"))
        self.assertEqual(resultats["total_rejete"], Decimal("1800.00"))

    def test_9_bareme_sagps(self):
        regle = get_regle("SAGPS", "ANALYSES")
        self.assertIsNotNone(regle)
        self.assertEqual(regle["taux"], Decimal("90.00"))
        self.assertEqual(regle["plafond_annuel"], Decimal("40000.00"))

    def test_10_bareme_cnl(self):
        regle = get_regle("CNL", "CONSULTATION_GENERALISTE")
        self.assertIsNotNone(regle)
        self.assertEqual(regle["mode"], "FORFAIT")
        self.assertEqual(regle["montant_forfait"], Decimal("1500.00"))

    def test_11_lister_codes(self):
        codes = lister_codes_actes("SAGPS")
        self.assertIn("ANALYSES", codes)
        self.assertIn("RADIOGRAPHIE", codes)
        self.assertIn("CONSULTATION_GENERALISTE", codes)

    def test_12_taux_nul(self):
        self.garantie_acte.taux_prise_en_charge = Decimal("0.00")
        self.garantie_acte.save()

        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("0.00"))

    def test_13_taux_100(self):
        self.garantie_acte.taux_prise_en_charge = Decimal("100.00")
        self.garantie_acte.save()

        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("10000.00"))

    def test_14_franchise_superieure(self):
        self.garantie_acte.franchise = Decimal("15000.00")
        self.garantie_acte.save()

        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("10000.00"))

        calcul = calculer_pour_un_acte(detail, demande)

        self.assertEqual(calcul["montant_accorde"], Decimal("0.00"))

    def test_15_montant_decimal(self):
        demande = self._creer_demande()
        detail = self._creer_detail(demande, Decimal("123.45"))

        calcul = calculer_pour_un_acte(detail, demande)

        attendu = Decimal("111.105")
        self.assertEqual(calcul["montant_accorde"], attendu)