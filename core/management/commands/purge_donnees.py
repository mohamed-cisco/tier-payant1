"""
Commande Django pour TOUT supprimer sauf :
    - Rôles
    - Utilisateurs
    - Permissions
    - Motifs de rejet

Usage :
    python manage.py purge_donnees
    python manage.py purge_donnees --confirm
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Supprime TOUTES les données métier (garde rôles, users, permissions)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Ne pas demander de confirmation",
        )

    def handle(self, *args, **options):
        from core.models import (
            # À SUPPRIMER
            AuditLog,
            RecoursDocument, DecisionRecours, Recours,
            DemandeTpDocument, DemandeTpDetail, DemandeTp,
            Reglement, DetailFacture, Facture,
            Consommation,
            PriseEnChargeDetail, PriseEnCharge,
            Convention,
            TarifSousActe,
            Prestataire,
            Plafond,
            GarantieActe,
            ContratGarantie, Contrat,
            Souscripteur,
            Adhesion, AyantDroit, Adherent, Personne,
            Document,
            Garantie,
            TypePrestation,
            SousActe,
            Acte,
            MotifRejet,
            ChampPersonnalise, ValeurChampPersonnalise,
            # À GARDER : Role, Utilisateur, Permission,
            # RolePermission, UtilisateurRole
        )

        if not options["confirm"]:
            self.stdout.write(self.style.WARNING(
                "\n⚠️  ATTENTION — Cette commande va TOUT supprimer SAUF :\n"
                "   ✅ Rôles\n"
                "   ✅ Utilisateurs\n"
                "   ✅ Permissions\n"
                "   ✅ Motifs de rejet\n\n"
                "SERA SUPPRIMÉ :\n"
                "   ❌ Adhérents, Ayants droit, Personnes\n"
                "   ❌ Adhésions, Souscripteurs, Contrats, Garanties\n"
                "   ❌ Prestataires, Conventions, Tarifs\n"
                "   ❌ Types de prestation, Actes, Sous-actes\n"
                "   ❌ Demandes TP, PEC, Consommations\n"
                "   ❌ Factures, Règlements, Recours, Documents\n"
                "   ❌ Champs personnalisés\n"
                "   ❌ Audit logs\n"
            ))
            reponse = input("\nContinuer ? Tape 'OUI' en majuscules : ").strip()

            if reponse != "OUI":
                self.stdout.write(self.style.ERROR("❌ Annulé."))
                return

        self.stdout.write("\n🗑️  Suppression en cours...\n")

        # ORDRE CRITIQUE (respecter les dépendances FK)
        ordre = [
            ("Audit logs", AuditLog),
            ("Documents joints recours", RecoursDocument),
            ("Décisions recours", DecisionRecours),
            ("Recours", Recours),
            ("Documents joints demande", DemandeTpDocument),
            ("Règlements", Reglement),
            ("Détails facture", DetailFacture),
            ("Factures", Facture),
            ("Consommations", Consommation),
            ("Détails PEC", PriseEnChargeDetail),
            ("PEC", PriseEnCharge),
            ("Détails demande TP", DemandeTpDetail),
            ("Demandes TP", DemandeTp),
            ("Conventions", Convention),
            ("Tarifs sous-actes", TarifSousActe),
            ("Prestataires", Prestataire),
            ("Plafonds", Plafond),
            ("Garantie-Actes", GarantieActe),
            ("Contrat-Garanties", ContratGarantie),
            ("Contrats", Contrat),
            ("Souscripteurs", Souscripteur),
            ("Adhésions", Adhesion),
            ("Ayants droit", AyantDroit),
            ("Adhérents", Adherent),
            ("Personnes", Personne),
            ("Documents", Document),
            ("Valeurs champs perso", ValeurChampPersonnalise),
            ("Champs personnalisés", ChampPersonnalise),
            ("Motifs de rejet", MotifRejet),
            ("Sous-actes", SousActe),
            ("Actes", Acte),
            ("Types de prestation", TypePrestation),
            ("Garanties", Garantie),
        ]

        with transaction.atomic():
            for nom, modele in ordre:
                try:
                    nb = modele.objects.count()
                    modele.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f"   ✅ {nom} : {nb} supprimé(s)"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ {nom} : ERREUR — {e}"))

        self.stdout.write(self.style.SUCCESS("\n✅ Nettoyage terminé !\n"))
        self.stdout.write("CONSERVÉ :")
        self.stdout.write("   ✅ Rôles")
        self.stdout.write("   ✅ Utilisateurs")
        self.stdout.write("   ✅ Permissions\n")