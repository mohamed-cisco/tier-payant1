from django import forms

from .models import (
    Utilisateur,
    Recours,
    Personne,
    DecisionRecours,
    Prestataire,
    Convention,
    Plafond,
    SousActe,
)


class LoginForm(forms.Form):
    nom_utilisateur = forms.CharField(
        label="Nom utilisateur",
        max_length=50
    )

    mot_de_passe = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput
    )


class UtilisateurForm(forms.ModelForm):

    mot_de_passe = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        required=False
    )

    class Meta:
        model = Utilisateur
        fields = [
            "nom_utilisateur",
            "nom",
            "prenom",
            "email",
            "telephone",
            "mot_de_passe",
            "statut",
        ]

class AdherentForm(forms.Form):

    numero_adherent = forms.CharField(
    label="Numéro adhérent",
    max_length=30,
    required=False,
    widget=forms.HiddenInput()
)

    numero_personne = forms.CharField(
       label="Numéro personne",
       max_length=30,
       required=False,
       widget=forms.HiddenInput()
)

    nom = forms.CharField(
        label="Nom",
        max_length=100
    )

    prenom = forms.CharField(
        label="Prénom",
        max_length=100
    )

    date_naissance = forms.DateField(
        label="Date de naissance",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    sexe = forms.ChoiceField(
        label="Sexe",
        choices=[
            ("", "---------"),
            ("M", "Masculin"),
            ("F", "Féminin"),
        ],
        required=False
    )

    adresse = forms.CharField(
        label="Adresse",
        max_length=300,
        required=False
    )

    telephone = forms.CharField(
        label="Téléphone",
        max_length=30,
        required=False
    )

    email = forms.EmailField(
        label="Email",
        max_length=150,
        required=False
    )

    date_adhesion = forms.DateField(
        label="Date d'adhésion",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    statut = forms.CharField(
    label="Statut",
    max_length=20,
    required=False,
    initial="ACTIF",
    widget=forms.HiddenInput()
)
class SouscripteurForm(forms.Form):

    code_souscripteur = forms.CharField(
    label="Code souscripteur",
    max_length=30,
    required=False,
    widget=forms.HiddenInput()
)

    raison_sociale = forms.CharField(
        label="Raison sociale",
        max_length=200
    )

    type_souscripteur = forms.CharField(
        label="Type de souscripteur",
        max_length=50
    )

    nif = forms.CharField(
        label="NIF",
        max_length=30,
        required=False
    )

    registre_commerce = forms.CharField(
        label="Registre de commerce",
        max_length=50,
        required=False
    )

    adresse = forms.CharField(
        label="Adresse",
        max_length=300,
        required=False
    )

    telephone = forms.CharField(
        label="Téléphone",
        max_length=30,
        required=False
    )

    email = forms.EmailField(
        label="Email",
        max_length=150,
        required=False
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        required=False,
        initial="ACTIF",
        widget=forms.HiddenInput()
    )
class ContratForm(forms.Form):

    numero_contrat = forms.CharField(
    label="Numéro de contrat",
    max_length=50,
    required=False,
    widget=forms.HiddenInput()
)

    id_souscripteur = forms.ChoiceField(
        label="Souscripteur",
        choices=[]
    )

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_fin = forms.DateField(
        label="Date de fin",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    type_contrat = forms.CharField(
        label="Type de contrat",
        max_length=50
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )

    objet = forms.CharField(
        label="Objet",
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3}
        )
    )

    date_signature = forms.DateField(
        label="Date de signature",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )
class ContratGarantieForm(forms.Form):

    id_garantie = forms.ChoiceField(
        label="Garantie",
        choices=[]
    )

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_fin = forms.DateField(
        label="Date de fin",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )

class GarantieForm(forms.Form):

    code_garantie = forms.CharField(
    label="Code garantie",
    max_length=30,
    required=False,
    widget=forms.HiddenInput()
)

    libelle = forms.CharField(
        label="Libellé",
        max_length=150
    )

    description = forms.CharField(
        label="Description",
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3}
        )
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )
class ActeForm(forms.Form):

    id_type_prestation = forms.ChoiceField(
        label="Type de prestation",
        choices=[]
    )

    code_acte = forms.CharField(
    label="Code acte",
    max_length=30,
    required=False,
    widget=forms.HiddenInput()
)

    libelle = forms.CharField(
        label="Libellé",
        max_length=200
    )

    description = forms.CharField(
        label="Description",
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3}
        )
    )

    unite = forms.CharField(
        label="Unité",
        max_length=30,
        required=False
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )
class SousActeForm(forms.Form):

    id_acte = forms.ChoiceField(
        label="Acte",
        choices=[]
    )

    code_sous_acte = forms.CharField(
        label="Code sous-acte",
        max_length=30,
        required=False,
        widget=forms.HiddenInput()
    )

    libelle = forms.CharField(
        label="Libellé",
        max_length=200
    )

    description = forms.CharField(
        label="Description",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3})
    )

    unite = forms.CharField(
        label="Unité",
        max_length=30,
        required=False
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )

class GarantieActeForm(forms.Form):

    id_garantie = forms.ChoiceField(
        label="Garantie",
        choices=[]
    )

    id_acte = forms.ChoiceField(
        label="Acte",
        choices=[]
    )

    taux_prise_en_charge = forms.DecimalField(
        label="Taux de prise en charge (%)",
        max_digits=5,
        decimal_places=2,
        required=False
    )

    franchise = forms.DecimalField(
        label="Franchise",
        max_digits=12,
        decimal_places=2,
        required=False
    )

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_fin = forms.DateField(
        label="Date de fin",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )
class AdhesionForm(forms.Form):

    id_adherent = forms.ChoiceField(
        label="Adhérent",
        choices=[]
    )

    id_contrat = forms.ChoiceField(
        label="Contrat",
        choices=[]
    )

    numero_adhesion = forms.CharField(
    label="Numéro d'adhésion",
    max_length=50,
    required=False,
    widget=forms.HiddenInput()
)

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_fin = forms.DateField(
        label="Date de fin",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )
class PersonneForm(forms.Form):

    numero_personne = forms.CharField(
        label="Numéro personne",
        max_length=30,
        required=False
    )

    nom = forms.CharField(
        label="Nom",
        max_length=100
    )

    prenom = forms.CharField(
        label="Prénom",
        max_length=100
    )

    date_naissance = forms.DateField(
        label="Date de naissance",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    sexe = forms.ChoiceField(
        label="Sexe",
        choices=[
            ("", "---------"),
            ("M", "Masculin"),
            ("F", "Féminin"),
        ],
        required=False
    )

    adresse = forms.CharField(
        label="Adresse",
        max_length=300,
        required=False
    )

    telephone = forms.CharField(
        label="Téléphone",
        max_length=30,
        required=False
    )

    email = forms.EmailField(
        label="Email",
        max_length=150,
        required=False
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )
class AyantDroitForm(forms.Form):

    id_adherent = forms.IntegerField(
        label="Adhérent",
        required=False,
        widget=forms.HiddenInput()
    )

    nom = forms.CharField(
        label="Nom",
        max_length=100
    )

    prenom = forms.CharField(
        label="Prénom",
        max_length=100
    )

    date_naissance = forms.DateField(
        label="Date de naissance",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    sexe = forms.ChoiceField(
        label="Sexe",
        choices=[
            ("M", "Masculin"),
            ("F", "Féminin"),
        ],
        required=False
    )

    type_lien = forms.ChoiceField(
        label="Type de lien",
        choices=[
            ("CONJOINT", "Conjoint(e)"),
            ("ENFANT", "Enfant"),
            ("PARENT", "Parent"),
            ("AUTRE", "Autre"),
        ]
    )

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_fin = forms.DateField(
        label="Date de fin",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        initial="ACTIF"
    )

    def __init__(
        self,
        *args,
        nom_adherent=None,
        date_adhesion=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.nom_adherent = (
            (nom_adherent or "").strip()
        )

        self.date_adhesion = date_adhesion

    def clean(self):
        cleaned_data = super().clean()

        nom = cleaned_data.get("nom", "").strip()
        type_lien = cleaned_data.get("type_lien")

        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        if (
            type_lien == "ENFANT"
            and self.nom_adherent
            and nom.casefold() != self.nom_adherent.casefold()
        ):
            self.add_error(
                "nom",
                f"Pour un enfant, le nom doit être : {self.nom_adherent}"
            )

        if date_debut and date_fin and date_fin < date_debut:
            self.add_error(
                "date_fin",
                "La date de fin ne peut pas être antérieure à la date de début."
            )
        if (
            date_debut
            and self.date_adhesion
            and date_debut < self.date_adhesion
        ):
            self.add_error(
                "date_debut",
                "La date de début de l'ayant droit ne peut pas "
                "être antérieure à la date d'adhésion du titulaire."
            )

        return cleaned_data


class PrestataireForm(forms.Form):

    code_prestataire = forms.CharField(
    label="Code prestataire",
    max_length=30,
    required=False,
    widget=forms.HiddenInput()
)

    raison_sociale = forms.CharField(
        label="Raison sociale",
        max_length=200
    )

    type_prestataire = forms.ChoiceField(
        label="Type de prestataire",
        choices=[
            ("PHARMACIE", "Pharmacie"),
            ("MEDECIN", "Médecin"),
            ("CLINIQUE", "Clinique"),
            ("LABORATOIRE", "Laboratoire"),
            ("CENTRE_RADIOLOGIE", "Centre de radiologie"),
            ("DENTAIRE", "Centre dentaire"),
            ("OPTIQUE", "Centre optique"),
            ("AUTRE", "Autre"),
        ]
    )

    nif = forms.CharField(
        label="NIF",
        max_length=30,
        required=False
    )

    registre_commerce = forms.CharField(
        label="Registre de commerce",
        max_length=50,
        required=False
    )

    adresse = forms.CharField(
        label="Adresse",
        max_length=300,
        required=False
    )

    telephone = forms.CharField(
        label="Téléphone",
        max_length=30,
        required=False
    )

    email = forms.EmailField(
        label="Email",
        max_length=150,
        required=False
    )

    statut = forms.ChoiceField(
        label="Statut",
        choices=[
            ("ACTIF", "Actif"),
            ("INACTIF", "Inactif"),
        ],
        initial="ACTIF"
    )
class DemandeTpForm(forms.Form):

    id_personne_beneficiaire = forms.ChoiceField(
        label="Bénéficiaire",
        choices=[]
    )

    id_contrat = forms.ChoiceField(
        label="Contrat",
        choices=[]
    )

    id_prestataire = forms.ChoiceField(
        label="Prestataire",
        choices=[]
    )

    numero_demande = forms.CharField(
    label="Numéro de demande",
    max_length=50,
    required=False,
    widget=forms.HiddenInput()
)

    montant_demande = forms.DecimalField(
        label="Montant demandé",
        max_digits=15,
        decimal_places=2,
        min_value=0
    )

    statut = forms.ChoiceField(
        label="Statut",
        choices=[
            ("EN_ATTENTE", "En attente"),
            ("ACCEPTEE", "Acceptée"),
            ("REJETEE", "Rejetée"),
            ("ANNULEE", "Annulée"),
        ],
        initial="EN_ATTENTE"
    )

    motif_rejet = forms.CharField(
        label="Motif du rejet",
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 4})
    )
class DemandeTpDetailForm(forms.Form):

    id_acte = forms.ChoiceField(
        label="Acte",
        choices=[]
    )

    quantite = forms.DecimalField(
        label="Quantité",
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        initial=1
    )

    montant_unitaire = forms.DecimalField(
        label="Montant unitaire",
        max_digits=15,
        decimal_places=2,
        min_value=0
    )

    observation = forms.CharField(
        label="Observation",
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 4})
    )
class ConsommationForm(forms.Form):

    id_detail_pec = forms.ChoiceField(
        label="Détail de prise en charge",
        choices=[]
    )

    id_sous_acte = forms.ChoiceField(
        label="Sous-acte",
        choices=[]
    )

    date_prestation = forms.DateField(
        label="Date de prestation",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    quantite = forms.DecimalField(
        label="Quantité",
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        initial=1
    )

    statut = forms.ChoiceField(
        label="Statut",
        choices=[
            ("A_TRAITER", "À traiter"),
            ("VALIDEE", "Validée"),
            ("ANNULEE", "Annulée"),
        ],
        initial="A_TRAITER"
    )
class FactureForm(forms.Form):

    id_prestataire = forms.ChoiceField(
        label="Prestataire",
        choices=[]
    )

    numero_facture = forms.CharField(
    label="Numéro de facture",
    max_length=50,
    required=False,
    widget=forms.HiddenInput()
)

    date_facture = forms.DateField(
        label="Date de facture",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_reception = forms.DateField(
        label="Date de réception",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    observation = forms.CharField(
        label="Observation",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4})
    )
class ReglementForm(forms.Form):

    id_facture = forms.ChoiceField(
        label="Facture",
        choices=[]
    )

    numero_reglement = forms.CharField(
        label="NumÃ©ro de rÃ¨glement",
        max_length=50,
        required=False,
        widget=forms.HiddenInput()
    )

    date_reglement = forms.DateField(
        label="Date de règlement",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    montant = forms.DecimalField(
        label="Montant",
        max_digits=15,
        decimal_places=2,
        min_value=0.01
    )

    mode_reglement = forms.ChoiceField(
        label="Mode de règlement",
        choices=[
            ("VIREMENT", "Virement"),
            ("CHEQUE", "Chèque"),
            ("ESPECES", "Espèces"),
        ]
    )

    reference_reglement = forms.CharField(
        label="Référence du règlement",
        max_length=100,
        required=False
    )

    observation = forms.CharField(
        label="Observation",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 4}
        )
    )
class RecoursForm(forms.ModelForm):

    id_personne = forms.ModelChoiceField(
        queryset=Personne.objects.all(),
        label="Personne",
        empty_label="-- Sélectionner une personne --"
    )

    class Meta:
        model = Recours
        fields = [
            "id_personne",
            "type_recours",
            "date_recours",
            "objet",
            "motif",
            "observation",
        ]

        widgets = {
            "date_recours": forms.DateInput(
                attrs={"type": "date"}
            ),
            "motif": forms.Textarea(
                attrs={"rows": 4}
            ),
            "observation": forms.Textarea(
                attrs={"rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["id_personne"].label_from_instance = (
            lambda personne:
                f"{personne.nom} {personne.prenom}"
        )

        self.fields["type_recours"].choices = [
            ("RECOURS_MEDICAL", "Recours médical"),
            ("RECOURS_FACTURATION", "Recours facturation"),
            ("RECOURS_ADMINISTRATIF", "Recours administratif"),
            ("AUTRE", "Autre"),
        ]
class DecisionRecoursForm(forms.ModelForm):

    type_decision = forms.ChoiceField(
        label="Type décision",
        choices=[
            ("ACCEPTEE", "Acceptée"),
            ("REJETEE", "Rejetée"),
            ("ACCEPTEE_PARTIELLEMENT", "Acceptée partiellement"),
        ]
    )

    class Meta:
        model = DecisionRecours
        fields = [
            "date_decision",
            "type_decision",
            "motif_decision",
            "montant_accorde",
            "observation",
        ]

        widgets = {
            "date_decision": forms.DateInput(
                attrs={"type": "date"}
            ),
            "motif_decision": forms.Textarea(
                attrs={"rows": 4}
            ),
            "montant_accorde": forms.NumberInput(
                attrs={"step": "0.01"}
            ),
            "observation": forms.Textarea(
                attrs={"rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["type_decision"].choices = [
            ("ACCEPTEE", "Acceptée"),
            ("REJETEE", "Rejetée"),
            ("ACCEPTEE_PARTIELLEMENT", "Acceptée partiellement"),
        ]
class ConventionForm(forms.Form):

    id_prestataire = forms.ModelChoiceField(
        label="Prestataire",
        queryset=Prestataire.objects.filter(
            statut="ACTIF"
        ).order_by("raison_sociale"),
        empty_label="--- Sélectionner un prestataire ---"
    )

    numero_convention = forms.CharField(
    label="Numéro de convention",
    max_length=50,
    required=False,
    widget=forms.HiddenInput()
)

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_fin = forms.DateField(
        label="Date de fin",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    statut = forms.ChoiceField(
        label="Statut",
        choices=[
            ("ACTIF", "Actif"),
            ("CLOTUREE", "Clôturée"),
            ("EXPIREE", "Expirée"),
        ],
        initial="ACTIF"
    )

    description = forms.CharField(
        label="Description",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 4}
        )
    )

    def clean(self):
        cleaned_data = super().clean()

        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        if date_debut and date_fin and date_fin < date_debut:
            self.add_error(
                "date_fin",
                "La date de fin doit être postérieure ou égale à la date de début."
            )

        return cleaned_data
class DocumentForm(forms.Form):

    fichier = forms.FileField(
        label="Fichier"
    )

    type_document = forms.CharField(
        label="Type de document",
        max_length=100,
        required=False
    )

    statut = forms.ChoiceField(
        label="Statut",
        choices=[
            ("ACTIF", "Actif"),
            ("ARCHIVE", "Archivé"),
        ],
        initial="ACTIF"
    )
class PlafondForm(forms.Form):

    id_garantie_acte = forms.ChoiceField(
        label="Garantie / Acte",
        choices=[]
    )

    type_plafond = forms.ChoiceField(
        label="Type de plafond",
        choices=[
            ("MONTANT", "Montant maximum"),
            ("QUANTITE", "Quantité maximum"),
            ("MIXTE", "Montant + quantité"),
        ],
        initial="MONTANT"
    )

    niveau_application = forms.ChoiceField(
        label="Niveau d'application",
        choices=[
            ("ADHERENT", "Adhérent"),
            ("PERSONNE", "Personne bénéficiaire"),
            ("CONTRAT", "Contrat"),
        ],
        initial="ADHERENT"
    )

    periode = forms.ChoiceField(
        label="Période",
        choices=[
            ("JOUR", "Journalier"),
            ("MOIS", "Mensuel"),
            ("TRIMESTRE", "Trimestriel"),
            ("SEMESTRE", "Semestriel"),
            ("ANNEE", "Annuel"),
        ],
        initial="ANNEE"
    )

    montant_max = forms.DecimalField(
        label="Montant maximum (DA)",
        max_digits=15,
        decimal_places=2,
        required=False,
        min_value=0
    )

    quantite_max = forms.IntegerField(
        label="Quantité maximum",
        required=False,
        min_value=0
    )

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_fin = forms.DateField(
        label="Date de fin",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    statut = forms.ChoiceField(
        label="Statut",
        choices=[
            ("ACTIF", "Actif"),
            ("INACTIF", "Inactif"),
        ],
        initial="ACTIF"
    )

    def clean(self):
        cleaned_data = super().clean()

        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        type_plafond = cleaned_data.get("type_plafond")
        montant_max = cleaned_data.get("montant_max")
        quantite_max = cleaned_data.get("quantite_max")

        if date_debut and date_fin and date_fin < date_debut:
            self.add_error(
                "date_fin",
                "La date de fin doit être postérieure ou égale à la date de début."
            )

        if type_plafond == "MONTANT" and montant_max is None:
            self.add_error(
                "montant_max",
                "Le montant maximum est obligatoire pour ce type de plafond."
            )

        if type_plafond == "QUANTITE" and quantite_max is None:
            self.add_error(
                "quantite_max",
                "La quantité maximum est obligatoire pour ce type de plafond."
            )

        if type_plafond == "MIXTE":
            if montant_max is None:
                self.add_error(
                    "montant_max",
                    "Le montant maximum est obligatoire pour un plafond mixte."
                )

            if quantite_max is None:
                self.add_error(
                    "quantite_max",
                    "La quantité maximum est obligatoire pour un plafond mixte."
                )

        return cleaned_data

class ImportAdherentForm(forms.Form):

    fichier = forms.FileField(
        label="Fichier Excel"
    )

class TarifSousActeForm(forms.Form):

    id_sous_acte = forms.ChoiceField(
        label="Sous-acte",
        choices=[]
    )

    id_prestataire = forms.ChoiceField(
        label="Prestataire",
        choices=[]
    )

    montant = forms.DecimalField(
        label="Montant",
        max_digits=15,
        decimal_places=2,
        min_value=0
    )

    date_debut = forms.DateField(
        label="Date début",
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    date_fin = forms.DateField(
        label="Date fin",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    statut = forms.CharField(
        label="Statut",
        max_length=20,
        required=False,
        initial="ACTIF",
        widget=forms.HiddenInput()
    )
