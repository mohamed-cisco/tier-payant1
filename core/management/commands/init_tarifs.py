"""
Commande Django pour créer tous les tarifs sous-actes automatiquement.

Usage :
    python manage.py init_tarifs
    python manage.py init_tarifs --reset  (supprime tous les tarifs existants avant)

Logique :
    - Pour chaque sous-acte, applique un tarif de référence
    - Crée un tarif par sous-acte ET par prestataire ACTIF
"""

from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    SousActe,
    Prestataire,
    TarifSousActe,
)


# ============================================================
# TABLEAU DE RÉFÉRENCE — Montants par libellé de sous-acte
# ============================================================

TARIFS = {
    # Consultations généralistes
    "Consultation médecine générale": 1500,
    "Consultation à domicile": 2500,
    "Consultation d'urgence": 3000,

    # Consultations spécialistes
    "Cardiologie": 2500,
    "Dermatologie": 2000,
    "Gynécologie": 2500,
    "Ophtalmologie": 2500,
    "ORL": 2000,
    "Pédiatrie": 2000,
    "Neurologie": 3000,
    "Orthopédie": 2500,

    # Scanner / IRM
    "Scanner cérébral": 15000,
    "Scanner thoracique": 15000,
    "Scanner abdominal": 15000,
    "IRM cérébrale": 25000,
    "IRM rachis": 25000,
    "IRM articulaire": 25000,

    # Échographie
    "Échographie abdominale": 2500,
    "Échographie pelvienne": 2500,
    "Échographie obstétricale": 3000,
    "Échographie cardiaque": 4000,
    "Échographie vasculaire": 3500,
    "Échographie thyroïdienne": 2500,

    # Radiographie
    "Radio thorax": 1500,
    "Radio colonne": 2000,
    "Radio membres": 1500,
    "Radio crâne": 1500,
    "Radio bassin": 1800,
    "Radio dentaire (panoramique)": 2000,

    # Analyses médicales
    "NFS (Numération formule sanguine)": 800,
    "Glycémie à jeun": 400,
    "Bilan lipidique": 1200,
    "Créatinine": 400,
    "Transaminases": 500,
    "TSH (Thyroïde)": 1500,
    "Sérologie (Hépatite B/C)": 2500,
    "Test grossesse (βHCG)": 1200,
    "Ionogramme sanguin": 800,
    "VS (Vitesse sédimentation)": 300,
    "CRP": 500,
    "Ferritine": 1200,

    # Forfaits
    "Forfait mariage (unique)": 20000,
    "Forfait naissance (unique)": 20000,

    # Hospitalisation
    "Chirurgie générale": 80000,
    "Chirurgie orthopédique": 100000,
    "Chirurgie cardiaque": 150000,
    "Chirurgie digestive": 90000,
    "Chirurgie gynécologique": 100000,
    "Hospitalisation standard": 5000,
    "Soins intensifs": 15000,
    "Surveillance post-op": 8000,

    # Dentaire
    "Détartrage": 3000,
    "Carie (obturation)": 2500,
    "Extraction dentaire": 3000,
    "Traitement canal": 8000,
    "Couronne céramique": 15000,
    "Prothèse fixe": 25000,
    "Prothèse amovible": 20000,
    "Bridge dentaire": 45000,

    # Orthodontie
    "Appareil orthodontique fixe": 80000,
    "Appareil orthodontique mobile": 30000,
    "Contrôle orthodontie": 2000,

    # Optique
    "Verres unifocaux": 3000,
    "Verres progressifs": 6000,
    "Verres anti-reflets": 4000,
    "Monture enfant": 3000,
    "Monture adulte": 4000,
    "Lentilles thérapeutiques": 4000,
    "Lentilles correctrices": 3000,

    # Pharmacie
    "Médicaments vignette verte": 1000,
    "Médicaments vignette rouge": 5000,

    # Kinésithérapie
    "Séance kiné standard": 1200,
    "Rééducation post-op": 1500,
    "Massage thérapeutique": 1000,

    # Orthophoniste
    "Bilan orthophonique": 3000,
    "Séance rééducation langage": 1500,
    "Séance rééducation voix": 1500,
}


class Command(BaseCommand):
    help = "Crée automatiquement tous les tarifs sous-actes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime tous les tarifs existants avant de créer",
        )
        parser.add_argument(
            "--date-debut",
            type=str,
            default="2026-01-01",
            help="Date de début des tarifs (format YYYY-MM-DD)",
        )

    def handle(self, *args, **options):
        # Parser la date
        try:
            annee, mois, jour = options["date_debut"].split("-")
            date_debut = date(int(annee), int(mois), int(jour))
        except Exception:
            self.stderr.write(self.style.ERROR("❌ Format de date invalide. Utilise YYYY-MM-DD"))
            return

        # Option reset
        if options["reset"]:
            with transaction.atomic():
                nb = TarifSousActe.objects.count()
                TarifSousActe.objects.all().delete()
                self.stdout.write(f"🗑️  {nb} tarif(s) supprimé(s)")

        # Récupérer les données
        prestataires = list(Prestataire.objects.filter(statut="ACTIF"))
        sous_actes = list(SousActe.objects.filter(statut="ACTIF"))

        if not prestataires:
            self.stderr.write(self.style.ERROR("❌ Aucun prestataire ACTIF trouvé."))
            return

        if not sous_actes:
            self.stderr.write(self.style.ERROR("❌ Aucun sous-acte ACTIF trouvé."))
            return

        self.stdout.write(f"\n📋 {len(prestataires)} prestataire(s)")
        self.stdout.write(f"📋 {len(sous_actes)} sous-acte(s)")
        self.stdout.write(f"📋 Total tarifs à créer : {len(prestataires) * len(sous_actes)}\n")

        # Création
        crees = 0
        ignores = 0
        erreurs = []

        with transaction.atomic():
            for prestataire in prestataires:
                self.stdout.write(f"\n🏥 {prestataire.code_prestataire} - {prestataire.raison_sociale}")

                for sous_acte in sous_actes:
                    # Trouver le tarif correspondant au libellé
                    montant = TARIFS.get(sous_acte.libelle)

                    if montant is None:
                        # Pas de tarif défini pour ce sous-acte
                        ignores += 1
                        continue

                    # Vérifier si le tarif existe déjà
                    existant = TarifSousActe.objects.filter(
                        id_sous_acte=sous_acte,
                        id_prestataire=prestataire,
                        date_debut=date_debut,
                    ).exists()

                    if existant:
                        ignores += 1
                        continue

                    try:
                        TarifSousActe.objects.create(
                            id_sous_acte=sous_acte,
                            id_prestataire=prestataire,
                            montant=Decimal(str(montant)),
                            date_debut=date_debut,
                            date_fin=None,
                            statut="ACTIF",
                        )
                        crees += 1
                    except Exception as e:
                        erreurs.append(f"{prestataire.raison_sociale} / {sous_acte.libelle} : {e}")

        # Résumé
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"✅ {crees} tarif(s) créé(s)"))
        self.stdout.write(f"⏭️  {ignores} ignoré(s) (déjà existants ou non configurés)")

        if erreurs:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {len(erreurs)} erreur(s) :"))
            for e in erreurs[:10]:
                self.stdout.write(f"   - {e}")

        self.stdout.write("=" * 50 + "\n")