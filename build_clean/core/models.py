# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from datetime import date

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)

# ============================================================
# ÉNUMÉRATIONS (TextChoices) — valeurs autorisées pour les statuts
# ============================================================

class Statut(models.TextChoices):
    """Statuts génériques pour toutes les entités (cycle de vie)."""
    ACTIF = "ACTIF", "Actif"
    INACTIF = "INACTIF", "Inactif"
    RADIE = "RADIE", "Radié"


class StatutValidation(models.TextChoices):
    """Statuts de validation (demandes, factures, prises en charge)."""
    EN_ATTENTE = "EN_ATTENTE", "En attente"
    ACCEPTEE = "ACCEPTEE", "Acceptée"
    VALIDEE = "VALIDEE", "Validée"
    REJETEE = "REJETEE", "Rejetée"
    ANNULEE = "ANNULEE", "Annulée"
    PAYEE = "PAYEE", "Payée"


class StatutRecours(models.TextChoices):
    """Statuts spécifiques aux recours."""
    EN_COURS = "EN_COURS", "En cours"
    TRAITE = "TRAITE", "Traité"
    CLOTURE = "CLOTURE", "Clôturé"
    REJETE = "REJETE", "Rejeté"

class Acte(models.Model):
    id_acte = models.BigAutoField(primary_key=True)
    id_type_prestation = models.ForeignKey('TypePrestation', models.DO_NOTHING, db_column='id_type_prestation')
    code_acte = models.CharField(unique=True, max_length=30)
    libelle = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    unite = models.CharField(max_length=30, blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'acte'

class SousActe(models.Model):
    id_sous_acte = models.BigAutoField(primary_key=True)

    id_acte = models.ForeignKey(
        Acte,
        models.DO_NOTHING,
        db_column='id_acte'
    )

    code_sous_acte = models.CharField(
        max_length=30,
        unique=True
    )

    libelle = models.CharField(max_length=200)

    description = models.TextField(
        blank=True,
        null=True
    )

    unite = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'sous_acte'
        unique_together = (('id_acte', 'libelle'),)

class TarifSousActe(models.Model):
    id_tarif_sous_acte = models.BigAutoField(primary_key=True)

    id_sous_acte = models.ForeignKey(
        'SousActe',
        models.DO_NOTHING,
        db_column='id_sous_acte'
    )

    id_prestataire = models.ForeignKey(
        'Prestataire',
        models.DO_NOTHING,
        db_column='id_prestataire'
    )

    montant = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    date_debut = models.DateField()

    date_fin = models.DateField(
        blank=True,
        null=True
    )

    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'tarif_sous_acte'
        unique_together = (
            ('id_sous_acte', 'id_prestataire', 'date_debut'),
        )

class Adherent(models.Model):
    id_adherent = models.BigAutoField(primary_key=True)
    id_personne = models.OneToOneField('Personne', models.DO_NOTHING, db_column='id_personne')
    numero_adherent = models.CharField(unique=True, max_length=30)
    date_creation = models.DateTimeField()
    statut = models.CharField(max_length=20)
    date_adhesion = models.DateField(blank=True, null=True)
    date_radiation = models.DateField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'adherent'


class Adhesion(models.Model):
    id_adhesion = models.BigAutoField(primary_key=True)
    id_adherent = models.ForeignKey(Adherent, models.DO_NOTHING, db_column='id_adherent')
    id_contrat = models.ForeignKey('Contrat', models.DO_NOTHING, db_column='id_contrat')
    numero_adhesion = models.CharField(unique=True, max_length=50)
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=20)
    date_creation = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'adhesion'


class AuditLog(models.Model):
    id_audit = models.BigAutoField(primary_key=True)
    id_utilisateur = models.ForeignKey('Utilisateur', models.DO_NOTHING, db_column='id_utilisateur', blank=True, null=True)
    date_action = models.DateTimeField()
    type_action = models.CharField(max_length=30)
    module = models.CharField(max_length=100, blank=True, null=True)
    table_cible = models.CharField(max_length=100, blank=True, null=True)
    id_enregistrement = models.BigIntegerField(blank=True, null=True)
    ancienne_valeur = models.TextField(blank=True, null=True)
    nouvelle_valeur = models.TextField(blank=True, null=True)
    adresse_ip = models.CharField(max_length=45, blank=True, null=True)
    poste = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'audit_log'




class AyantDroit(models.Model):
    id_ayant_droit = models.BigAutoField(primary_key=True)
    id_personne = models.OneToOneField('Personne', models.DO_NOTHING, db_column='id_personne')
    id_adherent = models.ForeignKey(Adherent, models.DO_NOTHING, db_column='id_adherent')
    type_lien = models.CharField(max_length=30)
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'ayant_droit'


class Consommation(models.Model):
    id_consommation = models.BigAutoField(primary_key=True)
    id_detail_pec = models.ForeignKey('PriseEnChargeDetail', models.DO_NOTHING, db_column='id_detail_pec')
    id_personne_beneficiaire = models.ForeignKey('Personne', models.DO_NOTHING, db_column='id_personne_beneficiaire')
    id_adhesion = models.ForeignKey(Adhesion, models.DO_NOTHING, db_column='id_adhesion')
    id_acte = models.ForeignKey(Acte, models.DO_NOTHING, db_column='id_acte')
    id_sous_acte = models.ForeignKey(
      'SousActe',
      models.DO_NOTHING,
      db_column='id_sous_acte',
      blank=True,
      null=True
)
    id_garantie = models.ForeignKey('Garantie', models.DO_NOTHING, db_column='id_garantie')
    id_prestataire = models.ForeignKey('Prestataire', models.DO_NOTHING, db_column='id_prestataire')
    date_prestation = models.DateField()
    date_validation = models.DateTimeField(blank=True, null=True)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    montant_base = models.DecimalField(max_digits=15, decimal_places=2)
    montant_prise_en_charge = models.DecimalField(max_digits=15, decimal_places=2)
    montant_reste = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=30)
    exercice = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'consommation'


class Contrat(models.Model):
    id_contrat = models.BigAutoField(primary_key=True)
    id_souscripteur = models.ForeignKey('Souscripteur', models.DO_NOTHING, db_column='id_souscripteur')
    numero_contrat = models.CharField(unique=True, max_length=50)
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    type_contrat = models.CharField(max_length=50)
    statut = models.CharField(max_length=20)
    date_creation = models.DateTimeField()
    objet = models.CharField(max_length=500, blank=True, null=True)
    date_signature = models.DateField(blank=True, null=True)
    date_modification = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'contrat'


class ContratGarantie(models.Model):
    id_contrat_garantie = models.BigAutoField(primary_key=True)
    id_contrat = models.ForeignKey(Contrat, models.DO_NOTHING, db_column='id_contrat')
    id_garantie = models.ForeignKey('Garantie', models.DO_NOTHING, db_column='id_garantie')
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'contrat_garantie'
        unique_together = (('id_contrat', 'id_garantie', 'date_debut'),)


class Convention(models.Model):
    id_convention = models.BigAutoField(primary_key=True)
    id_prestataire = models.ForeignKey('Prestataire', models.DO_NOTHING, db_column='id_prestataire')
    numero_convention = models.CharField(unique=True, max_length=50)
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'convention'


class DecisionRecours(models.Model):
    id_decision = models.BigAutoField(primary_key=True)
    id_recours = models.ForeignKey('Recours', models.DO_NOTHING, db_column='id_recours')
    date_decision = models.DateField()
    type_decision = models.CharField(max_length=50)
    motif_decision = models.TextField(blank=True, null=True)
    montant_accorde = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    observation = models.TextField(blank=True, null=True)
    utilisateur_decision = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'decision_recours'


class DemandeTp(models.Model):
    id_demande = models.BigAutoField(primary_key=True)
    numero_demande = models.CharField(unique=True, max_length=50)
    id_personne_beneficiaire = models.ForeignKey('Personne', models.DO_NOTHING, db_column='id_personne_beneficiaire')
    id_contrat = models.ForeignKey(Contrat, models.DO_NOTHING, db_column='id_contrat')
    id_prestataire = models.ForeignKey('Prestataire', models.DO_NOTHING, db_column='id_prestataire')
    date_demande = models.DateTimeField()
    montant_demande = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=30)
    motif_rejet = models.TextField(blank=True, null=True)
    date_decision = models.DateTimeField(blank=True, null=True)
    utilisateur_creation = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'demande_tp'



class DemandeTpDetail(models.Model):
    id_detail = models.BigAutoField(primary_key=True)
    id_demande = models.ForeignKey(DemandeTp, models.DO_NOTHING, db_column='id_demande')
    id_acte = models.ForeignKey(Acte, models.DO_NOTHING, db_column='id_acte')
    id_sous_acte = models.ForeignKey('SousActe', models.DO_NOTHING, db_column='id_sous_acte', blank=True, null=True)
    id_prestataire = models.ForeignKey('Prestataire', models.DO_NOTHING, db_column='id_prestataire', blank=True, null=True)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    montant_unitaire = models.DecimalField(max_digits=15, decimal_places=2)
    montant_total = models.DecimalField(max_digits=15, decimal_places=2)
    observation = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'demande_tp_detail'


class DetailFacture(models.Model):
    id_detail_facture = models.BigAutoField(primary_key=True)
    id_facture = models.ForeignKey('Facture', models.DO_NOTHING, db_column='id_facture')
    id_consommation = models.ForeignKey(Consommation, models.DO_NOTHING, db_column='id_consommation')
    id_acte = models.ForeignKey(Acte, models.DO_NOTHING, db_column='id_acte')
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    montant_unitaire = models.DecimalField(max_digits=15, decimal_places=2)
    montant_total = models.DecimalField(max_digits=15, decimal_places=2)
    montant_valide = models.DecimalField(max_digits=15, decimal_places=2)
    montant_rejete = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=30)
    id_motif_rejet = models.ForeignKey('MotifRejet', models.DO_NOTHING, db_column='id_motif_rejet', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'detail_facture'



class Document(models.Model):
    id_document = models.BigAutoField(primary_key=True)
    nom_fichier = models.CharField(max_length=255)
    type_document = models.CharField(max_length=100, blank=True, null=True)
    extension = models.CharField(max_length=20, blank=True, null=True)
    taille = models.BigIntegerField(blank=True, null=True)
    emplacement = models.TextField()
    hash_fichier = models.CharField(max_length=128, blank=True, null=True)
    date_depot = models.DateTimeField()
    id_utilisateur = models.ForeignKey('Utilisateur', models.DO_NOTHING, db_column='id_utilisateur', blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'document'


class Facture(models.Model):
    id_facture = models.BigAutoField(primary_key=True)
    id_prestataire = models.ForeignKey('Prestataire', models.DO_NOTHING, db_column='id_prestataire')
    numero_facture = models.CharField(unique=True, max_length=50)
    date_facture = models.DateField()
    date_reception = models.DateField(blank=True, null=True)
    montant_total = models.DecimalField(max_digits=15, decimal_places=2)
    montant_valide = models.DecimalField(max_digits=15, decimal_places=2)
    montant_rejete = models.DecimalField(max_digits=15, decimal_places=2)
        # ===== TVA (nouveau) =====
    taux_tva = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Taux de TVA appliqué à cette facture (snapshot)"
    )
    montant_tva = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Montant de la TVA"
    )
    montant_ttc = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Montant total TTC (total + TVA)"
    )
    statut = models.CharField(max_length=30)
    date_validation = models.DateTimeField(blank=True, null=True)
    utilisateur_validation = models.CharField(max_length=100, blank=True, null=True)
    observation = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'facture'


class Garantie(models.Model):
    id_garantie = models.BigAutoField(primary_key=True)
    code_garantie = models.CharField(unique=True, max_length=30)
    libelle = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'garantie'


class GarantieActe(models.Model):
    id_garantie_acte = models.BigAutoField(primary_key=True)
    id_garantie = models.ForeignKey(Garantie, models.DO_NOTHING, db_column='id_garantie')
    id_acte = models.ForeignKey(Acte, models.DO_NOTHING, db_column='id_acte')
    taux_prise_en_charge = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    franchise = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    MODES_CALCUL = [
        ("POURCENTAGE", "Pourcentage du montant"),
        ("FORFAIT", "Montant fixe"),
        ("FRAIS_REELS", "Frais réels (sans calcul)"),
    ]

    mode_calcul = models.CharField(
        max_length=20,
        choices=MODES_CALCUL,
        default="POURCENTAGE",
    )
    montant_forfait = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Utilisé uniquement si mode_calcul = FORFAIT",
    )
    plafond_forfait = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Plafond max à appliquer même en mode forfait",
    )
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'garantie_acte'
        unique_together = (('id_garantie', 'id_acte', 'date_debut'),)


class MotifRejet(models.Model):
    id_motif_rejet = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=30)
    libelle = models.CharField(max_length=150)
    type_rejet = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'motif_rejet'


class Permission(models.Model):
    id_permission = models.BigAutoField(primary_key=True)
    code_permission = models.CharField(unique=True, max_length=50)
    libelle = models.CharField(max_length=150)
    module = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'permission'


class Personne(models.Model):
    id_personne = models.BigAutoField(primary_key=True)
    numero_personne = models.CharField(unique=True, max_length=30, blank=True, null=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField(blank=True, null=True)
    sexe = models.CharField(max_length=1, blank=True, null=True)
    adresse = models.CharField(max_length=300, blank=True, null=True)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)
    statut = models.CharField(max_length=20)
    date_creation = models.DateTimeField()
    date_modification = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'personne'


class Plafond(models.Model):
    id_plafond = models.BigAutoField(primary_key=True)
    id_garantie_acte = models.ForeignKey(GarantieActe, models.DO_NOTHING, db_column='id_garantie_acte')
    type_plafond = models.CharField(max_length=30)
    niveau_application = models.CharField(max_length=30)
    periode = models.CharField(max_length=30)
    montant_max = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    quantite_max = models.IntegerField(blank=True, null=True)
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=20)
    libelle = models.CharField(max_length=255, blank=True, null=True,
                               help_text="Nom lisible pour l'admin")
    comportement = models.CharField(max_length=20, blank=True, null=True,
                                    help_text="ECRETER / REJETER / BLOQUER / ALERTER")
    priorite = models.IntegerField(default=100,
                                   help_text="Ordre d'application (1 = premier)")

    class Meta:
        managed = True
        db_table = 'plafond'


class Prestataire(models.Model):
    id_prestataire = models.BigAutoField(primary_key=True)
    code_prestataire = models.CharField(unique=True, max_length=30)
    raison_sociale = models.CharField(max_length=200)
    type_prestataire = models.CharField(max_length=50)
    nif = models.CharField(max_length=30, blank=True, null=True)
    registre_commerce = models.CharField(max_length=50, blank=True, null=True)
    adresse = models.CharField(max_length=300, blank=True, null=True)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)
    statut = models.CharField(max_length=20)
    date_creation = models.DateTimeField()
    def __str__(self):
        return f"{self.code_prestataire} - {self.raison_sociale}"

    class Meta:
        managed = True
        db_table = 'prestataire'


class PriseEnCharge(models.Model):
    id_pec = models.BigAutoField(primary_key=True)
    numero_pec = models.CharField(unique=True, max_length=50)
    id_demande = models.OneToOneField(DemandeTp, models.DO_NOTHING, db_column='id_demande')
    date_pec = models.DateTimeField()
    montant_demande = models.DecimalField(max_digits=15, decimal_places=2)
    montant_accepte = models.DecimalField(max_digits=15, decimal_places=2)
    montant_rejete = models.DecimalField(max_digits=15, decimal_places=2)
        # Statuts possibles :
    # EN_ATTENTE  → PEC créée, en attente de validation
    # ACCEPTEE    → PEC validée, consommations créées
    # REJETEE     → PEC rejetée
    # EXPIREE     → PEC expirée
    statut = models.CharField(max_length=30)
    date_expiration = models.DateField(blank=True, null=True)
    utilisateur_validation = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'prise_en_charge'


class PriseEnChargeDetail(models.Model):
    id_detail_pec = models.BigAutoField(primary_key=True)
    id_pec = models.ForeignKey(PriseEnCharge, models.DO_NOTHING, db_column='id_pec')
    id_detail_demande = models.ForeignKey(DemandeTpDetail, models.DO_NOTHING, db_column='id_detail_demande')
    id_acte = models.ForeignKey(Acte, models.DO_NOTHING, db_column='id_acte')
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    montant_demande = models.DecimalField(max_digits=15, decimal_places=2)
    montant_accorde = models.DecimalField(max_digits=15, decimal_places=2)
    montant_rejete = models.DecimalField(max_digits=15, decimal_places=2)
    taux_applique = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    franchise_appliquee = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=30)
    motif_rejet = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'prise_en_charge_detail'


class Recours(models.Model):
    id_recours = models.BigAutoField(primary_key=True)
    numero_recours = models.CharField(unique=True, max_length=50)
    id_personne = models.ForeignKey(Personne, models.DO_NOTHING, db_column='id_personne')
    type_recours = models.CharField(max_length=50)
    date_recours = models.DateField()
    objet = models.CharField(max_length=300)
    motif = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=30)
    date_cloture = models.DateField(blank=True, null=True)
    observation = models.TextField(blank=True, null=True)
    utilisateur_creation = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'recours'
class DemandeTpDocument(models.Model):
    pk = models.CompositePrimaryKey(
        'id_demande',
        'id_document'
    )

    id_demande = models.ForeignKey(
        DemandeTp,
        models.DO_NOTHING,
        db_column='id_demande'
    )

    id_document = models.ForeignKey(
        Document,
        models.DO_NOTHING,
        db_column='id_document'
    )

    type_document = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    date_ajout = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'demande_tp_document'

class RecoursDocument(models.Model):
    pk = models.CompositePrimaryKey('id_recours', 'id_document')
    id_recours = models.ForeignKey(Recours, models.DO_NOTHING, db_column='id_recours')
    id_document = models.ForeignKey(Document, models.DO_NOTHING, db_column='id_document')
    type_document = models.CharField(max_length=50, blank=True, null=True)
    date_ajout = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'recours_document'

class Reglement(models.Model):
    id_reglement = models.BigAutoField(primary_key=True)
    id_facture = models.ForeignKey(Facture, models.DO_NOTHING, db_column='id_facture'
)
    numero_reglement = models.CharField(unique=True, max_length=50
)
    date_reglement = models.DateField()
    montant = models.DecimalField(max_digits=15, decimal_places=2
)
    mode_reglement = models.CharField(max_length=30
)
    reference_reglement = models.CharField(max_length=100, blank=True, null=True
)
    statut = models.CharField(max_length=30
)
    observation = models.TextField(blank=True, null=True
)

    class Meta:
        managed = True
        db_table = 'reglement'


class Role(models.Model):
    id_role = models.BigAutoField(primary_key=True)
    code_role = models.CharField(unique=True, max_length=30)
    libelle = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'role'


class RolePermission(models.Model):
    pk = models.CompositePrimaryKey('id_role', 'id_permission')
    id_role = models.ForeignKey(Role, models.DO_NOTHING, db_column='id_role')
    id_permission = models.ForeignKey(Permission, models.DO_NOTHING, db_column='id_permission')

    class Meta:
        managed = True
        db_table = 'role_permission'


class Souscripteur(models.Model):
    id_souscripteur = models.BigAutoField(primary_key=True)
    code_souscripteur = models.CharField(unique=True, max_length=30)
    raison_sociale = models.CharField(max_length=200)
    type_souscripteur = models.CharField(max_length=50)
    nif = models.CharField(max_length=30, blank=True, null=True)
    registre_commerce = models.CharField(max_length=50, blank=True, null=True)
    adresse = models.CharField(max_length=300, blank=True, null=True)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)
    statut = models.CharField(max_length=20)
    date_creation = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'souscripteur'


class TypePrestation(models.Model):
    id_type_prestation = models.BigAutoField(primary_key=True)
    code_type = models.CharField(unique=True, max_length=30)
    libelle = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'type_prestation'


class UtilisateurManager(BaseUserManager):
    """Manager pour le modèle Utilisateur custom."""

    def create_user(self, nom_utilisateur, password=None, **extra_fields):
        if not nom_utilisateur:
            raise ValueError("Le nom d'utilisateur est obligatoire.")

        utilisateur = self.model(
            nom_utilisateur=nom_utilisateur,
            **extra_fields
        )
        utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, nom_utilisateur, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('statut', 'ACTIF')

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Un superutilisateur doit avoir is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Un superutilisateur doit avoir is_superuser=True.")

        return self.create_user(nom_utilisateur, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    id_utilisateur = models.BigAutoField(primary_key=True)
    nom_utilisateur = models.CharField(unique=True, max_length=50)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.CharField(unique=True, max_length=150, blank=True, null=True)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    statut = models.CharField(max_length=20, default='ACTIF')
    date_creation = models.DateTimeField(auto_now_add=True)
    derniere_connexion = models.DateTimeField(blank=True, null=True)

    # Champs requis par Django
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # On garde ton ancien champ pour la migration
    mot_de_passe_hash = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = 'nom_utilisateur'
    REQUIRED_FIELDS = ['nom', 'prenom']

    objects = UtilisateurManager()

    class Meta:
        managed = True
        db_table = 'utilisateur'

    def __str__(self):
        return f"{self.nom_utilisateur} ({self.nom} {self.prenom})"
class UtilisateurRole(models.Model):
    pk = models.CompositePrimaryKey('id_utilisateur', 'id_role')

    id_utilisateur = models.ForeignKey(
        Utilisateur,
        models.DO_NOTHING,
        db_column='id_utilisateur'
    )

    id_role = models.ForeignKey(
        Role,
        models.DO_NOTHING,
        db_column='id_role'
    )

    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)
    statut = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'utilisateur_role'

# ============================================================
# CHAMPS PERSONNALISÉS (paramétrage dynamique)
# ============================================================

class ChampPersonnalise(models.Model):
    """Définit un champ personnalisé ajoutable à une entité."""

    ENTITES = [
        ("ADHERENT", "Adhérent"),
        ("AYANT_DROIT", "Ayant droit"),
        ("PRESTATAIRE", "Prestataire"),
        ("SOUSCRIPTEUR", "Souscripteur"),
        ("CONTRAT", "Contrat"),
        ("FACTURE", "Facture"),
        ("DEMANDE_TP", "Demande TP"),
    ]

    TYPES = [
        ("TEXT", "Texte court"),
        ("TEXT_LONG", "Texte long"),
        ("NUMBER", "Nombre"),
        ("DECIMAL", "Nombre décimal"),
        ("DATE", "Date"),
        ("BOOLEAN", "Oui / Non"),
        ("CHOICE", "Liste de choix"),
    ]

    entite = models.CharField(max_length=30, choices=ENTITES)
    nom_technique = models.CharField(max_length=50)
    libelle = models.CharField(max_length=200)
    type_champ = models.CharField(max_length=20, choices=TYPES)
    obligatoire = models.BooleanField(default=False)
    valeur_defaut = models.CharField(max_length=200, blank=True, null=True)
    choix_possibles = models.TextField(
        blank=True, null=True,
        help_text="Pour le type CHOICE : une valeur par ligne"
    )
    ordre_affichage = models.IntegerField(default=0)
    statut = models.CharField(max_length=20, default="ACTIF")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "champ_personnalise"
        unique_together = (("entite", "nom_technique"),)
        ordering = ["entite", "ordre_affichage", "id"]

    def __str__(self):
        return f"{self.get_entite_display()} → {self.libelle}"


class ValeurChampPersonnalise(models.Model):
    """Contient la valeur d'un champ personnalisé pour un enregistrement."""

    champ = models.ForeignKey(
        ChampPersonnalise,
        models.CASCADE,
        db_column="id_champ",
        related_name="valeurs",
    )
    id_enregistrement = models.BigIntegerField()
    valeur = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "valeur_champ_personnalise"
        unique_together = (("champ", "id_enregistrement"),)
        indexes = [
            models.Index(fields=["champ", "id_enregistrement"]),
        ]

    def __str__(self):
        return f"{self.champ.libelle} = {self.valeur}"
    # ============================================================
# NOUVEAUX MODÈLES POUR LE REMBOURSEMENT
# ============================================================




class CoordonneesBancaires(models.Model):
    """
    Coordonnées bancaires d'un adhérent (pour les virements).
    """
    TYPE_COMPTE_CHOICES = [
        ('CCP',      'Compte CCP (Algérie Poste)'),
        ('BANCAIRE', 'Compte bancaire'),
    ]
    
    # Lien avec l'adhérent
    adherent          = models.OneToOneField(
        Adherent, on_delete=models.CASCADE,
        related_name='coordonnees_bancaires',
        db_column='id_adherent'
    )
    
    # Type de compte
    type_compte       = models.CharField(max_length=20, choices=TYPE_COMPTE_CHOICES, default='CCP')
    
    # Informations bancaires
    banque            = models.CharField(max_length=100, blank=True,
                                         help_text="Nom de la banque ou 'Algérie Poste'")
    rib               = models.CharField(max_length=50,
                                         help_text="RIB complet (20-24 chiffres)")
    titulaire         = models.CharField(max_length=255, blank=True,
                                         help_text="Nom du titulaire du compte")
    
    # Statut
    valide            = models.BooleanField(default=False,
                                            help_text="Validé par l'agent SAGPS")
    
    # Métadonnées
    date_creation     = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = True
        db_table = 'coordonnees_bancaires'
        verbose_name = "Coordonnées bancaires"
        verbose_name_plural = "Coordonnées bancaires"
    
    def __str__(self):
        return f"{self.adherent} - {self.get_type_compte_display()} - {self.rib[-6:]}"

# ============================================================
# CONFIGURATION CNAS (paramétrable)
# ============================================================

class ConfigCNAS(models.Model):
    """
    Configuration des forfaits et taux CNAS.
    Lié à un TypePrestation pour matcher automatiquement les actes.
    """
    # Lien avec le TypePrestation
    type_prestation = models.OneToOneField(
        'TypePrestation',
        on_delete=models.CASCADE,
        related_name='config_cnas',
        db_column='id_type_prestation',
        help_text="Type de prestation auquel cette config s'applique"
    )
    
    # Montant fixe
    forfait = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Montant fixe (ex: 120 DA)"
    )
    
    # Taux %
    taux_pourcentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Taux en % (ex: 80 pour médicaments)"
    )
    
    actif = models.BooleanField(default=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = True
        db_table = 'config_cnas'
        verbose_name = "Configuration CNAS"
        verbose_name_plural = "Configurations CNAS"
        ordering = ['type_prestation__libelle']
    
    def __str__(self):
        if self.taux_pourcentage > 0:
            return f"{self.type_prestation.libelle} : {self.taux_pourcentage}%"
        return f"{self.type_prestation.libelle} : {self.forfait} DA"
    
    def __str__(self):
        if self.taux_pourcentage > 0:
            return f"{self.libelle} : {self.taux_pourcentage}%"
        return f"{self.libelle} : {self.forfait} DA"
    
    def get_mots_cles_list(self):
        """Retourne la liste des mots-clés."""
        if not self.mots_cles:
            return []
        return [m.strip().lower() for m in self.mots_cles.split(',') if m.strip()]
  # ============================================================
# CONFIGURATION TVA
# ============================================================

class ConfigTVA(models.Model):
    """
    Configuration du taux de TVA applicable aux factures.
    Un seul enregistrement actif à la fois.
    """
    taux = models.DecimalField(
        max_digits=5, decimal_places=2, default=19.00,
        help_text="Taux de TVA en % (ex: 19.00)"
    )
    actif = models.BooleanField(default=True)
    date_debut = models.DateField(
        default=date.today,
        help_text="Date à partir de laquelle ce taux s'applique"
    )
    date_fin = models.DateField(
        null=True, blank=True,
        help_text="Laisser vide si toujours actif"
    )
    commentaire = models.CharField(
        max_length=255, blank=True,
        help_text="Ex: 'Taux normal 19%'"
    )
    cree_par = models.ForeignKey(
        'Utilisateur', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='configs_tva_creees',
        db_column='id_user_creation'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'config_tva'
        verbose_name = "Configuration TVA"
        verbose_name_plural = "Configurations TVA"
        ordering = ['-date_debut']

    def __str__(self):
        return f"TVA {self.taux}% ({self.date_debut})"  