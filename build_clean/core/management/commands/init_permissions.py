from django.core.management.base import BaseCommand
from core.models import Permission


PERMISSIONS = [
    # Adhérents
    ("ADHERENT_VIEW", "Consulter les adhérents", "Adhérents"),
    ("ADHERENT_CREATE", "Créer un adhérent", "Adhérents"),
    ("ADHERENT_UPDATE", "Modifier un adhérent", "Adhérents"),
    ("ADHERENT_DELETE", "Radier un adhérent", "Adhérents"),

    # Ayants droit
    ("AYANT_DROIT_VIEW", "Consulter les ayants droit", "Ayants droit"),
    ("AYANT_DROIT_CREATE", "Créer un ayant droit", "Ayants droit"),
    ("AYANT_DROIT_UPDATE", "Modifier un ayant droit", "Ayants droit"),
    ("AYANT_DROIT_DELETE", "Radier un ayant droit", "Ayants droit"),

    # Adhésions
    ("ADHESION_VIEW", "Consulter les adhésions", "Adhésions"),
    ("ADHESION_CREATE", "Créer une adhésion", "Adhésions"),
    ("ADHESION_UPDATE", "Modifier une adhésion", "Adhésions"),
    ("ADHESION_DELETE", "Radier une adhésion", "Adhésions"),

    # Souscripteurs
    ("SOUSCRIPTEUR_VIEW", "Consulter les souscripteurs", "Souscripteurs"),
    ("SOUSCRIPTEUR_CREATE", "Créer un souscripteur", "Souscripteurs"),
    ("SOUSCRIPTEUR_UPDATE", "Modifier un souscripteur", "Souscripteurs"),
    ("SOUSCRIPTEUR_DELETE", "Radier un souscripteur", "Souscripteurs"),

    # Contrats
    ("CONTRAT_VIEW", "Consulter les contrats", "Contrats"),
    ("CONTRAT_CREATE", "Créer un contrat", "Contrats"),
    ("CONTRAT_UPDATE", "Modifier un contrat", "Contrats"),
    ("CONTRAT_DELETE", "Radier un contrat", "Contrats"),

    # Garanties
    ("GARANTIE_VIEW", "Consulter les garanties", "Garanties"),
    ("GARANTIE_CREATE", "Créer une garantie", "Garanties"),
    ("GARANTIE_UPDATE", "Modifier une garantie", "Garanties"),
    ("GARANTIE_DELETE", "Radier une garantie", "Garanties"),

    # Garantie-Acte
    ("GARANTIE_ACTE_VIEW", "Consulter les associations garantie-acte", "Garantie-Acte"),
    ("GARANTIE_ACTE_CREATE", "Créer une association garantie-acte", "Garantie-Acte"),
    ("GARANTIE_ACTE_UPDATE", "Modifier une association garantie-acte", "Garantie-Acte"),
    ("GARANTIE_ACTE_DELETE", "Radier une association garantie-acte", "Garantie-Acte"),

    # Plafonds
    ("PLAFOND_VIEW", "Consulter les plafonds", "Plafonds"),
    ("PLAFOND_CREATE", "Créer un plafond", "Plafonds"),
    ("PLAFOND_UPDATE", "Modifier un plafond", "Plafonds"),
    ("PLAFOND_DELETE", "Désactiver un plafond", "Plafonds"),

    # Types de prestation
    ("TYPE_PRESTATION_VIEW", "Consulter les types de prestation", "Types de prestation"),
    ("TYPE_PRESTATION_CREATE", "Créer un type de prestation", "Types de prestation"),
    ("TYPE_PRESTATION_UPDATE", "Modifier un type de prestation", "Types de prestation"),
    ("TYPE_PRESTATION_DELETE", "Désactiver un type de prestation", "Types de prestation"),

    # Actes
    ("ACTE_VIEW", "Consulter les actes", "Actes"),
    ("ACTE_CREATE", "Créer un acte", "Actes"),
    ("ACTE_UPDATE", "Modifier un acte", "Actes"),
    ("ACTE_DELETE", "Radier un acte", "Actes"),

    # Sous-actes
    ("SOUS_ACTE_VIEW", "Consulter les sous-actes", "Sous-actes"),
    ("SOUS_ACTE_CREATE", "Créer un sous-acte", "Sous-actes"),
    ("SOUS_ACTE_UPDATE", "Modifier un sous-acte", "Sous-actes"),
    ("SOUS_ACTE_DELETE", "Radier un sous-acte", "Sous-actes"),

    # Tarifs sous-actes
    ("TARIF_SOUS_ACTE_VIEW", "Consulter les tarifs sous-actes", "Tarifs sous-actes"),
    ("TARIF_SOUS_ACTE_CREATE", "Créer un tarif sous-acte", "Tarifs sous-actes"),
    ("TARIF_SOUS_ACTE_UPDATE", "Modifier un tarif sous-acte", "Tarifs sous-actes"),
    ("TARIF_SOUS_ACTE_DELETE", "Radier un tarif sous-acte", "Tarifs sous-actes"),

    # Prestataires
    ("PRESTATAIRE_VIEW", "Consulter les prestataires", "Prestataires"),
    ("PRESTATAIRE_CREATE", "Créer un prestataire", "Prestataires"),
    ("PRESTATAIRE_UPDATE", "Modifier un prestataire", "Prestataires"),
    ("PRESTATAIRE_DELETE", "Désactiver un prestataire", "Prestataires"),

    # Conventions
    ("CONVENTION_VIEW", "Consulter les conventions", "Conventions"),
    ("CONVENTION_CREATE", "Créer une convention", "Conventions"),
    ("CONVENTION_UPDATE", "Modifier une convention", "Conventions"),
    ("CONVENTION_DELETE", "Clôturer une convention", "Conventions"),

    # Demandes TP
    ("DEMANDE_VIEW", "Consulter les demandes TP", "Demandes TP"),
    ("DEMANDE_CREATE", "Créer une demande TP", "Demandes TP"),
    ("DEMANDE_UPDATE", "Modifier une demande TP", "Demandes TP"),
    ("DEMANDE_VALIDATE", "Valider une demande TP", "Demandes TP"),
    ("DEMANDE_DELETE", "Annuler une demande TP", "Demandes TP"),

    # Consommations
    ("CONSOMMATION_VIEW", "Consulter les consommations", "Consommations"),
    ("CONSOMMATION_CREATE", "Créer une consommation", "Consommations"),
    ("CONSOMMATION_VALIDATE", "Valider une consommation", "Consommations"),
    ("CONSOMMATION_CANCEL", "Annuler une consommation", "Consommations"),

    # Factures
    ("FACTURE_VIEW", "Consulter les factures", "Factures"),
    ("FACTURE_CREATE", "Créer une facture", "Factures"),
    ("FACTURE_VALIDATE", "Valider une facture", "Factures"),

    # Règlements
    ("REGLEMENT_VIEW", "Consulter les règlements", "Règlements"),
    ("REGLEMENT_CREATE", "Créer un règlement", "Règlements"),
    ("REGLEMENT_VALIDATE", "Valider un règlement", "Règlements"),

    # Recours
    ("RECOURS_VIEW", "Consulter les recours", "Recours"),
    ("RECOURS_CREATE", "Créer un recours", "Recours"),
    ("RECOURS_VALIDATE", "Traiter un recours", "Recours"),

    # Documents
    ("DOCUMENT_VIEW", "Consulter les documents", "Documents"),
    ("DOCUMENT_CREATE", "Déposer un document", "Documents"),
    ("DOCUMENT_UPDATE", "Modifier un document", "Documents"),
    ("DOCUMENT_DELETE", "Archiver un document", "Documents"),

    # Audit
    ("AUDIT_VIEW", "Consulter les journaux d'audit", "Audit"),

    # Utilisateurs
    ("USER_VIEW", "Consulter les utilisateurs", "Utilisateurs"),
    ("USER_CREATE", "Créer un utilisateur", "Utilisateurs"),
    ("USER_UPDATE", "Modifier un utilisateur", "Utilisateurs"),

    # Rôles
    ("ROLE_VIEW", "Consulter les rôles", "Rôles"),
    ("ROLE_CREATE", "Créer un rôle", "Rôles"),
    ("ROLE_UPDATE", "Modifier un rôle", "Rôles"),
    ("ROLE_PERMISSION", "Gérer les permissions d'un rôle", "Rôles"),
]


class Command
(BaseCommand):
    help = "Crée les permissions manquantes dans la base"

    def handle(self, *args, **options):
        crees = 0
        existants = 0

        for code, libelle, module in PERMISSIONS:
            obj, created = Permission.objects.update_or_create(
                code_permission=code,
                defaults={
                    "libelle": libelle,
                    "module": module,
                    "statut": "ACTIF",
                }
            )
            if created:
                crees += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ {code}"))
            else:
                existants += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{crees} permission(s) créée(s), "
                f"{existants} déjà existante(s)."
            )
        )