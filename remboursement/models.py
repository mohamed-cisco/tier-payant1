from django.db import models

# Create your models here.
# remboursement/models.py
"""
Module Remboursement Classique - SAGPS
Utilise les modèles existants de core (Souscripteur, Contrat, Adhesion, etc.)
"""
from django.db import models
from django.conf import settings


# ============================================================
# BULLETIN DE SOINS
# ============================================================

class BulletinSoins(models.Model):
    """Bulletin de soins déposé par l'adhérent chez SAGPS."""
    
    STATUT_CHOICES = [
        ('RECU',            'Reçu'),
        ('EN_VERIFICATION', 'En élaboration'),
        ('VALIDE',          'Validé (contrôlé)'),
        ('TRANSMIS',        'Transmis au souscripteur'),
        ('REMBOURSE',       'Remboursé par le souscripteur'),
        ('REVERSE',         'Reversé à l\'adhérent'),
        ('REJETE',          'Rejeté'),
    ]
    
    LIEN_CHOICES = [
        ('ASSURE',    'Assuré principal'),
        ('CONJOINT',  'Conjoint(e)'),
        ('ENFANT',    'Enfant'),
        ('ASCENDANT', 'Ascendant'),
    ]
    
    DEPOSANT_CHOICES = [
        ('ADHERENT',    'Adhérent'),
        ('PRESTATAIRE', 'Prestataire'),
        ('AGENT',       'Agent SAGPS'),
    ]
    
    numero = models.CharField(max_length=30, unique=True)
    
    # Bénéficiaire
    adhesion = models.ForeignKey(
        'core.Adhesion', on_delete=models.PROTECT,
        related_name='bulletins_remboursement',
        db_column='id_adhesion',
    )
    patient = models.ForeignKey(
        'core.Personne', on_delete=models.PROTECT,
        related_name='bulletins_remboursement',
        db_column='id_patient',
    )
    lien_patient = models.CharField(
        max_length=20, choices=LIEN_CHOICES, default='ASSURE'
    )
    
    # Contrat
    contrat = models.ForeignKey(
        'core.Contrat', on_delete=models.PROTECT,
        related_name='bulletins_remboursement',
        db_column='id_contrat',
    )
    souscripteur = models.ForeignKey(
        'core.Souscripteur', on_delete=models.PROTECT,
        related_name='bulletins_remboursement',
        db_column='id_souscripteur',
    )
    
    # Dates
    date_soins = models.DateField()
    date_depot = models.DateTimeField(auto_now_add=True)
    
    # Statut
    statut = models.CharField(
        max_length=30, choices=STATUT_CHOICES, default='RECU'
    )
    
    # Déposant
    deposant_type = models.CharField(
        max_length=20, choices=DEPOSANT_CHOICES, default='ADHERENT'
    )
    deposant_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='bulletins_deposes',
        db_column='id_user_deposant',
    )
    
    # Traçabilité workflow
    saisi_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='bulletins_saisis',
        db_column='id_user_saisie',
    )
    date_saisie = models.DateTimeField(null=True, blank=True)
    
    elabore_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='bulletins_elabores',
        db_column='id_user_elaboration',
    )
    date_elaboration = models.DateTimeField(null=True, blank=True)
    
    controle_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='bulletins_controles',
        db_column='id_user_controle',
    )
    date_controle = models.DateTimeField(null=True, blank=True)
    
    # Récap
    recap = models.ForeignKey(
        'RecapSouscripteur', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bulletins',
        db_column='id_recap',
    )
    
    # Totaux
    montant_total_facture = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    montant_total_cnas = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    montant_total_rembourse = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    montant_a_charge = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    
    # Notes
    observations = models.TextField(blank=True)
    motif_rejet = models.TextField(blank=True)
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = True
        db_table = 'remb_bulletin_soins'
        verbose_name = "Bulletin de soins"
        verbose_name_plural = "Bulletins de soins"
        ordering = ['-date_depot']
    
    def __str__(self):
        return f"{self.numero}"


# ============================================================
# LIGNE DE BULLETIN
# ============================================================

class LigneBulletin(models.Model):
    """Une ligne du bulletin = 1 acte médical."""
    
    SECTION_CHOICES = [
        ('A', 'A - Actes médicaux'),
        ('B', 'B - Ordonnances'),
        ('C', 'C - Hospitalisation'),
        ('D', 'D - Dentaire'),
    ]
    
    TYPE_VIGNETTE_CHOICES = [
        ('AUCUNE',  'Aucune'),
        ('VERTE',   'Verte'),
        ('ROUGE',   'Rouge'),
        ('BLANCHE', 'Blanche'),
    ]
    
    TYPE_SOIN_DENT_CHOICES = [
        ('', ''),
        ('SOIN',      'Soin'),
        ('PROTHESE',  'Prothèse'),
        ('CHIRURGIE', 'Chirurgie'),
    ]
    
    STATUT_CALCUL_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('CALCULE',    'Calculé'),
        ('REJETE',     'Rejeté'),
        ('MANUEL',     'Saisi manuellement'),
    ]
    
    bulletin = models.ForeignKey(
        BulletinSoins, on_delete=models.CASCADE,
        related_name='lignes', db_column='id_bulletin'
    )
    
    section = models.CharField(max_length=1, choices=SECTION_CHOICES)
    date_acte = models.DateField()
    
    # Liens avec core
    acte = models.ForeignKey(
        'core.Acte', on_delete=models.PROTECT,
        related_name='lignes_bulletins',
        db_column='id_acte',
    )
    sous_acte = models.ForeignKey(
        'core.SousActe', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='lignes_bulletins',
        db_column='id_sous_acte',
    )
    prestataire = models.ForeignKey(
        'core.Prestataire', on_delete=models.PROTECT,
        related_name='lignes_bulletins',
        db_column='id_prestataire',
    )
    
    # Détail
    quantite = models.IntegerField(default=1)
    montant_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Pharmacie
    type_vignette = models.CharField(
        max_length=10, choices=TYPE_VIGNETTE_CHOICES, default='AUCUNE'
    )
    
    # Hospitalisation
    date_admission = models.DateField(null=True, blank=True)
    date_sortie = models.DateField(null=True, blank=True)
    etablissement = models.CharField(max_length=255, blank=True)
    nb_nuits = models.IntegerField(null=True, blank=True)
    
    # Dentaire
    numero_dent = models.CharField(max_length=50, blank=True)
    type_soin_dent = models.CharField(
        max_length=20, choices=TYPE_SOIN_DENT_CHOICES, blank=True
    )
    
    # Snapshot calcul
    garantie_acte_utilisee = models.ForeignKey(
        'core.GarantieActe', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lignes_bulletins',
        db_column='id_garantie_acte',
    )
    plafond_utilise = models.ForeignKey(
        'core.Plafond', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lignes_bulletins',
        db_column='id_plafond',
    )
    
    taux_applique = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    franchise_appliquee = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    
    montant_cnas = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    base_calcul = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    montant_rembourse = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    montant_a_charge = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    
    statut_calcul = models.CharField(
        max_length=20, choices=STATUT_CALCUL_CHOICES, default='EN_ATTENTE'
    )
    motif_rejet = models.TextField(blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = True
        db_table = 'remb_ligne_bulletin'
        verbose_name = "Ligne de bulletin"
        verbose_name_plural = "Lignes de bulletin"
        ordering = ['section', 'date_acte']
    
    def __str__(self):
        return f"{self.get_section_display()} - {self.montant_total} DA"


# ============================================================
# PIÈCE JOINTE
# ============================================================

class PieceJointe(models.Model):
    """Pièce justificative jointe au bulletin."""
    
    TYPE_PIECE_CHOICES = [
        ('ORDONNANCE',        'Ordonnance visée'),
        ('VIGNETTES',         'Vignettes originales'),
        ('FACTURE',           'Facture'),
        ('COMPTE_RENDU',      'Compte rendu médical'),
        ('PRESCRIPTION',      'Prescription médicale'),
        ('FICHE_DENTAIRE',    'Fiche dentaire'),
        ('PRISE_CHARGE_CNAS', 'Prise en charge CNAS'),
        ('AUTRE',             'Autre'),
    ]
    
    bulletin = models.ForeignKey(
        BulletinSoins, on_delete=models.CASCADE,
        related_name='pieces_jointes', db_column='id_bulletin'
    )
    ligne = models.ForeignKey(
        LigneBulletin, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='pieces_jointes',
        db_column='id_ligne',
    )
    
    type_piece = models.CharField(max_length=30, choices=TYPE_PIECE_CHOICES)
    fichier = models.FileField(upload_to='remboursement/pieces/%Y/%m/')
    description = models.CharField(max_length=255, blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = True
        db_table = 'remb_piece_jointe'
        verbose_name = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"
        ordering = ['-date_ajout']
    
    def __str__(self):
        return f"{self.get_type_piece_display()} - {self.bulletin.numero}"


# ============================================================
# RÉCAP SOUSCRIPTEUR
# ============================================================

class RecapSouscripteur(models.Model):
    """Récap mensuel envoyé au souscripteur (TALA, AMANA...)."""
    
    STATUT_CHOICES = [
        ('BROUILLON',   'Brouillon'),
        ('ENVOYE',      'Envoyé au souscripteur'),
        ('EN_CONTROLE', 'En contrôle'),
        ('VALIDE',      'Validé'),
        ('REJETE',      'Rejeté'),
        ('PAYE',        'Payé'),
    ]
    
    numero = models.CharField(max_length=30, unique=True)
    
    souscripteur = models.ForeignKey(
        'core.Souscripteur', on_delete=models.PROTECT,
        related_name='recaps_remboursement',
        db_column='id_souscripteur',
    )
    
    periode_debut = models.DateField()
    periode_fin = models.DateField()
    
    nb_bulletins = models.IntegerField(default=0)
    nb_adherents = models.IntegerField(default=0)
    montant_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='BROUILLON'
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_envoi = models.DateField(null=True, blank=True)
    date_validation = models.DateField(null=True, blank=True)
    date_paiement = models.DateField(null=True, blank=True)
    
    reference_virement = models.CharField(max_length=100, blank=True)
    montant_recu = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    
    fichier_pdf = models.FileField(
        upload_to='remboursement/recaps/%Y/%m/', null=True, blank=True
    )
    fichier_excel = models.FileField(
        upload_to='remboursement/recaps/%Y/%m/', null=True, blank=True
    )
    
    observations = models.TextField(blank=True)
    motif_rejet = models.TextField(blank=True)
    
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='recaps_crees',
        db_column='id_user_creation',
    )
    
    class Meta:
        managed = True
        db_table = 'remb_recap_souscripteur'
        verbose_name = "Récap souscripteur"
        verbose_name_plural = "Récaps souscripteur"
        ordering = ['-periode_debut']
        unique_together = [('souscripteur', 'periode_debut', 'periode_fin')]
    
    def __str__(self):
        return f"{self.numero}"


# ============================================================
# VIREMENT ADHÉRENT
# ============================================================

class VirementAdherent(models.Model):
    """Virement individuel à un adhérent."""
    
    STATUT_CHOICES = [
        ('A_PAYER',  'À payer'),
        ('EN_COURS', 'En cours'),
        ('PAYE',     'Payé'),
        ('ECHEC',    'Échec'),
        ('ANNULE',   'Annulé'),
    ]
    
    MODE_CHOICES = [
        ('VIREMENT', 'Virement bancaire'),
        ('CCP',      'Versement CCP'),
        ('CHEQUE',   'Chèque'),
        ('ESPECES',  'Espèces'),
    ]
    
    numero = models.CharField(max_length=30, unique=True)
    
    adherent = models.ForeignKey(
        'core.Adherent', on_delete=models.PROTECT,
        related_name='virements_remboursement',
        db_column='id_adherent',
    )
    
    bulletins = models.ManyToManyField(
        BulletinSoins,
        related_name='virements_adherent',
        db_table='remb_virement_bulletins'
    )
    
    recap = models.ForeignKey(
        RecapSouscripteur, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='virements',
        db_column='id_recap',
    )
    
    montant = models.DecimalField(max_digits=14, decimal_places=2)
    
    mode_paiement = models.CharField(
        max_length=20, choices=MODE_CHOICES, default='VIREMENT'
    )
    
    banque = models.CharField(max_length=100, blank=True)
    rib = models.CharField(max_length=50, blank=True)
    
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='A_PAYER'
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_paiement = models.DateField(null=True, blank=True)
    
    reference_paiement = models.CharField(max_length=100, blank=True)
    observations = models.TextField(blank=True)
    
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='virements_crees',
        db_column='id_user_creation',
    )
    paye_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='virements_payes',
        db_column='id_user_paiement',
    )
    
    class Meta:
        managed = True
        db_table = 'remb_virement_adherent'
        verbose_name = "Virement adhérent"
        verbose_name_plural = "Virements adhérents"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.numero} - {self.montant} DA"