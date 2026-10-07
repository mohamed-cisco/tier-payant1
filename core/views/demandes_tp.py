# core/views/demandes_tp.py
"""
Vues de gestion des demandes de tiers payant.

Fonctions :
- demandes_tp : liste
- demande_tp_details : détail
- _libelle_beneficiaire : helper
- _generer_numero_demande : helper
- demande_tp_create : créer
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.forms import (
    DemandeTpForm,
    DemandeTpDetailForm,
   
)
from core.models import (
    Acte,
    Adherent,
    AyantDroit,
    Adhesion,
    Consommation,
    DemandeTp,
    DemandeTpDetail,
    DemandeTpDocument,
    Document,
    Garantie,
    GarantieActe,
    PriseEnCharge,
    PriseEnChargeDetail,
    Prestataire,
    RolePermission,
    SousActe,
    TarifSousActe,
)
from core.services.calculs import calculer_pour_demande
from core.views.champs import (
    get_champs_pour_entite,
    get_valeur_champ,
    sauvegarder_valeurs_champs,
)
from core.views.dashboard import enregistrer_audit

# Imports PDF
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)


def demandes_tp(request):
    """Liste des demandes TP."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "DEMANDE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les demandes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    demandes = (
        DemandeTp.objects
        .select_related(
            "id_personne_beneficiaire",
            "id_contrat",
            "id_prestataire",
        )
        .all()
        .order_by("-id_demande")
    )

    if recherche:
        demandes = demandes.filter(
            Q(numero_demande__icontains=recherche)
            | Q(id_personne_beneficiaire__nom__icontains=recherche)
            | Q(id_personne_beneficiaire__prenom__icontains=recherche)
            | Q(id_contrat__numero_contrat__icontains=recherche)
            | Q(id_prestataire__raison_sociale__icontains=recherche)
        )

    if statut:
        demandes = demandes.filter(statut=statut)

    statuts = [
        ("EN_ATTENTE", "En attente"),
        ("ACCEPTEE", "Acceptée"),
        ("REJETEE", "Rejetée"),
        ("ANNULEE", "Annulée"),
    ]

    return render(
        request,
        "core/demandes_tp.html",
        {
            "demandes": demandes,
            "recherche": recherche,
            "statut": statut,
            "statuts": statuts,
            "permissions": permissions,
            "page": "demandes_tp",
        }
    )


def _libelle_beneficiaire(personne):
    """Retourne le libellé du bénéficiaire (adhérent ou ayant droit)."""
    try:
        adherent = personne.adherent
        if adherent.statut == "ACTIF":
            return (
                f"{adherent.numero_adherent} - "
                f"{personne.nom} {personne.prenom}"
            )
    except Adherent.DoesNotExist:
        pass

    try:
        ayant_droit = personne.ayantdroit
        if ayant_droit.statut == "ACTIF":
            return (
                f"{ayant_droit.id_adherent.numero_adherent} - "
                f"{personne.nom} {personne.prenom} "
                f"(Ayant droit)"
            )
    except AyantDroit.DoesNotExist:
        pass

    return f"{personne.nom} {personne.prenom}"


def _generer_numero_demande():
    """Génère un numéro unique de demande TP."""
    annee = timezone.now().year
    prefixe = f"DTP-{annee}-"

    numeros = (
        DemandeTp.objects
        .filter(numero_demande__startswith=prefixe)
        .values_list("numero_demande", flat=True)
    )

    valeurs = []
    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_demande = f"{prefixe}{prochain:04d}"

    while DemandeTp.objects.filter(numero_demande=numero_demande).exists():
        prochain += 1
        numero_demande = f"{prefixe}{prochain:04d}"

    return numero_demande


def demande_tp_details(request, id_demande):
    """Détail d'une demande TP."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "DEMANDE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les détails de la demande."
        )
        return redirect("demandes_tp")

    try:
        demande = DemandeTp.objects.get(id_demande=id_demande)
    except DemandeTp.DoesNotExist:
        messages.error(request, "Demande de tiers payant introuvable.")
        return redirect("demandes_tp")

    details = (
        DemandeTpDetail.objects
        .select_related("id_acte")
        .filter(id_demande=demande)
        .order_by("id_detail")
    )

    documents_lies = (
        DemandeTpDocument.objects
        .select_related(
            "id_document",
            "id_document__id_utilisateur",
        )
        .filter(id_demande=demande)
        .order_by("-date_ajout")
    )

    pec_details = (
        PriseEnChargeDetail.objects
        .select_related(
            "id_pec",
            "id_acte",
            "id_detail_demande",
        )
        .filter(id_pec__id_demande=demande)
        .order_by("id_detail_pec")
    )

    consommations_existantes = set(
        Consommation.objects
        .filter(id_detail_pec__in=pec_details)
        .values_list("id_detail_pec_id", flat=True)
    )

    montant_total = sum(
        detail.montant_total for detail in details
    )

    return render(
        request,
        "core/demande_tp_details.html",
        {
            "demande": demande,
            "details": details,
            "documents_lies": documents_lies,
            "pec_details": pec_details,
            "montant_total": montant_total,
            "permissions": permissions,
            "consommations_existantes": consommations_existantes,
        }
    )


def demande_tp_create(request):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "DEMANDE_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("demandes_tp")

    contrats = (
        Contrat.objects.filter(statut="ACTIF")
        .select_related("id_souscripteur")
        .order_by("numero_contrat")
    )

    id_contrat_preselectionne = request.GET.get("id_contrat", "").strip()
    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects.filter(
                id_contrat=id_contrat_preselectionne, statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )

    id_contrat_beneficiaires = id_contrat_preselectionne

    if not id_contrat_beneficiaires:
        premier_contrat = contrats.first()
        if premier_contrat:
            id_contrat_beneficiaires = str(premier_contrat.id_contrat)

    if request.method == "POST":
        id_contrat_beneficiaires = request.POST.get("id_contrat", "").strip()

    personnes = Personne.objects.none()

    if id_contrat_beneficiaires:
        ids_adherents = (
            Adhesion.objects
            .filter(id_contrat=id_contrat_beneficiaires, statut="ACTIF")
            .values_list("id_adherent", flat=True)
        )

        ids_personnes_titulaires = (
            Adherent.objects
            .filter(id_adherent__in=ids_adherents, statut="ACTIF")
            .values_list("id_personne", flat=True)
        )

        ids_personnes_ayants_droit = (
            AyantDroit.objects
            .filter(id_adherent__in=ids_adherents, statut="ACTIF")
            .values_list("id_personne", flat=True)
        )

        ids_beneficiaires = list(ids_personnes_titulaires) + list(ids_personnes_ayants_droit)

        personnes = (
            Personne.objects
            .filter(id_personne__in=ids_beneficiaires, statut="ACTIF")
            .order_by("nom", "prenom")
        )

    prestataires = (
        Prestataire.objects.filter(statut="ACTIF").order_by("raison_sociale")
    )

    if request.method == "POST":
        form = DemandeTpForm(request.POST)
        form.fields["statut"].initial = "EN_ATTENTE"
        form.fields["statut"].widget = forms.HiddenInput()

        form.fields["id_personne_beneficiaire"].choices = [
            (str(p.id_personne), _libelle_beneficiaire(p)) for p in personnes
        ]

        form.fields["id_contrat"].choices = [
            (str(c.id_contrat), f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}")
            for c in contrats
        ]

        form.fields["id_prestataire"].choices = [
            (str(p.id_prestataire), f"{p.code_prestataire} - {p.raison_sociale}")
            for p in prestataires
        ]

        if form.is_valid():
            try:
                personne = Personne.objects.get(
                    id_personne=form.cleaned_data["id_personne_beneficiaire"],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.get(
                    id_contrat=form.cleaned_data["id_contrat"],
                    statut="ACTIF"
                )

                prestataire = Prestataire.objects.get(
                    id_prestataire=form.cleaned_data["id_prestataire"],
                    statut="ACTIF"
                )

                # Vérifier bénéficiaire rattaché
                titulaire_valide = Adhesion.objects.filter(
                    id_contrat=contrat,
                    id_adherent__id_personne=personne,
                    statut="ACTIF"
                ).exists()

                ayant_droit_valide = Adhesion.objects.filter(
                    id_contrat=contrat,
                    id_adherent__ayantdroit__id_personne=personne,
                    statut="ACTIF"
                ).exists()

                if not titulaire_valide and not ayant_droit_valide:
                    messages.error(
                        request,
                        "Le bénéficiaire sélectionné n'est pas rattaché "
                        "à une adhésion active de ce contrat."
                    )
                    return render(
                        request,
                        "core/demande_tp_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle demande",
                            "contrats": contrats,
                            "prestataires": prestataires,
                            "personnes": personnes,
                            "contrat_preselectionne": contrat_preselectionne,
                        }
                    )

                # Vérifier convention active
                date_demande = timezone.now().date()
                convention_active = Convention.objects.filter(
                    id_prestataire=prestataire,
                    statut="ACTIF",
                    date_debut__lte=date_demande
                ).filter(
                    Q(date_fin__isnull=True) | Q(date_fin__gte=date_demande)
                ).exists()

                if not convention_active:
                    messages.error(
                        request,
                        "Impossible de créer la demande TP : aucune convention "
                        "active avec ce prestataire à la date de la demande."
                    )
                    return render(
                        request,
                        "core/demande_tp_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle demande",
                            "contrats": contrats,
                            "prestataires": prestataires,
                            "personnes": personnes,
                            "contrat_preselectionne": contrat_preselectionne,
                        }
                    )

                # 🔍 DÉTECTION DE DOUBLON
                doublon = DemandeTp.objects.filter(
                    id_personne_beneficiaire=personne,
                    id_prestataire=prestataire,
                    date_demande__date=date_demande,
                    statut__in=["EN_ATTENTE", "ACCEPTEE"],
                ).first()

                if doublon and not request.POST.get("confirmer_doublon"):
                    messages.warning(
                        request,
                        f"⚠️ Une demande existe déjà aujourd'hui pour ce "
                        f"bénéficiaire chez ce prestataire : "
                        f"{doublon.numero_demande} "
                        f"({doublon.montant_demande} DA, statut {doublon.statut}). "
                        f"Cliquez à nouveau sur Enregistrer pour créer quand même."
                    )
                    return render(
                        request,
                        "core/demande_tp_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle demande",
                            "contrats": contrats,
                            "prestataires": prestataires,
                            "personnes": personnes,
                            "contrat_preselectionne": contrat_preselectionne,
                            "doublon_detecte": doublon,
                        }
                    )

                demande = DemandeTp.objects.create(
                    numero_demande=_generer_numero_demande(),
                    id_personne_beneficiaire=personne,
                    id_contrat=contrat,
                    id_prestataire=prestataire,
                    date_demande=timezone.now(),
                    montant_demande=Decimal("0.00"),
                    statut="EN_ATTENTE",
                    motif_rejet=form.cleaned_data["motif_rejet"] or None,
                    date_decision=None,
                    utilisateur_creation=str(request.session.get("id_utilisateur")),
                )
                                # 🔄 Créer la PEC automatiquement
                numero_pec = _generer_numero_pec()
                pec = PriseEnCharge.objects.create(
                    numero_pec=numero_pec,
                    id_demande=demande,
                    date_pec=timezone.now(),
                    montant_demande=Decimal("0.00"),
                    montant_accepte=Decimal("0.00"),
                    montant_rejete=Decimal("0.00"),
                    statut="EN_ATTENTE",   # ← En attente de validation
                    date_expiration=timezone.now().date() + timedelta(days=30),
                    utilisateur_validation=None,
                )

                # Passer la demande à ACCEPTEE (la PEC prend le relais)
                demande.statut = "ACCEPTEE"
                demande.date_decision = timezone.now()
                demande.save()

                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="DEMANDE TP",
                    table_cible="demande_tp",
                    id_enregistrement=demande.id_demande,
                    nouvelle_valeur=demande.numero_demande,
                    description=f"Création de la demande {demande.numero_demande}",
                )

                messages.success(
                    request,
                    f"Demande {demande.numero_demande} créée. "
                    f"PEC {numero_pec} générée automatiquement. "
                    f"Validez la PEC pour créer les consommations."
                )
                return redirect("prise_en_charge_details", id_pec=pec.id_pec)

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = DemandeTpForm()
        form.fields["statut"].initial = "EN_ATTENTE"
        form.fields["statut"].widget = forms.HiddenInput()

        form.fields["id_personne_beneficiaire"].choices = [
            (str(p.id_personne), _libelle_beneficiaire(p)) for p in personnes
        ]

        form.fields["id_contrat"].choices = [
            (str(c.id_contrat), f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}")
            for c in contrats
        ]

        if contrat_preselectionne:
            form.initial["id_contrat"] = str(contrat_preselectionne.id_contrat)

        form.fields["id_prestataire"].choices = [
            (str(p.id_prestataire), f"{p.code_prestataire} - {p.raison_sociale}")
            for p in prestataires
        ]

    return render(
        request,
        "core/demande_tp_form.html",
        {
            "form": form,
            "titre": "Nouvelle demande de Tiers Payant",
            "contrat_preselectionne": contrat_preselectionne,
            "page": "demandes_tp",
        }
    )



def demande_tp_detail_create(request, id_demande):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "DEMANDE_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation d'ajouter un détail à une demande.")
        return redirect("demandes_tp")

    try:
        demande = DemandeTp.objects.get(id_demande=id_demande)
    except DemandeTp.DoesNotExist:
        messages.error(request, "Demande de tiers payant introuvable.")
        return redirect("demandes_tp")

    # Récupérer tous les actes actifs
    actes = Acte.objects.filter(statut="ACTIF").order_by("libelle")

    def _remplir_choices(form):
        """Remplit les choices des champs du formulaire."""
        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
            for a in actes
        ]

        # Si un acte est déjà sélectionné, charger ses sous-actes
        id_acte_selectionne = None
        if request.method == "POST":
            id_acte_selectionne = request.POST.get("id_acte")
        else:
            id_acte_selectionne = request.GET.get("id_acte")

        if id_acte_selectionne:
            sous_actes = (
                SousActe.objects
                .filter(id_acte_id=id_acte_selectionne, statut="ACTIF")
                .order_by("libelle")
            )
            form.fields["id_sous_acte"].choices = [
                (str(s.id_sous_acte), f"{s.code_sous_acte} - {s.libelle}")
                for s in sous_actes
            ]
        else:
            form.fields["id_sous_acte"].choices = []

    if request.method == "POST":
        form = DemandeTpDetailForm(request.POST)
        _remplir_choices(form)

        if form.is_valid():
            try:
                acte = Acte.objects.get(
                    id_acte=form.cleaned_data["id_acte"],
                    statut="ACTIF"
                )
                sous_acte = SousActe.objects.get(
                    id_sous_acte=form.cleaned_data["id_sous_acte"],
                    statut="ACTIF"
                )
                # Le prestataire est hérité de la demande
                prestataire = demande.id_prestataire

                # Vérifier que l'acte est couvert par une garantie active du contrat
                acte_couvert = (
                    GarantieActe.objects
                    .filter(
                        id_acte=acte,
                        statut="ACTIF",
                        id_garantie__contratgarantie__id_contrat=demande.id_contrat,
                        id_garantie__contratgarantie__statut="ACTIF",
                    )
                    .exists()
                )

                if not acte_couvert:
                    messages.error(
                        request,
                        "Cet acte n'est pas couvert par une garantie active "
                        "du contrat de cette demande."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                            "page": "demandes_tp",
                        }
                    )

                # Récupérer le tarif applicable
                date_aujourdhui = timezone.now().date()
                tarif = (
                    TarifSousActe.objects
                    .filter(
                        id_sous_acte=sous_acte,
                        id_prestataire=prestataire,
                        statut="ACTIF",
                        date_debut__lte=date_aujourdhui,
                    )
                    .filter(
                        Q(date_fin__isnull=True) | Q(date_fin__gte=date_aujourdhui)
                    )
                    .order_by("-date_debut")
                    .first()
                )

                if not tarif:
                    messages.error(
                        request,
                        "Aucun tarif actif pour ce sous-acte chez ce prestataire."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                        }
                    )

                quantite = form.cleaned_data["quantite"]
                montant_unitaire = tarif.montant
                montant_total = quantite * montant_unitaire

                # Créer le détail
                DemandeTpDetail.objects.create(
                    id_demande=demande,
                    id_acte=acte,
                    id_sous_acte=sous_acte,
                    quantite=quantite,
                    montant_unitaire=montant_unitaire,
                    montant_total=montant_total,
                    observation=form.cleaned_data["observation"] or None,
                )

                # Recalculer le montant total de la demande
                total_details = (
                    DemandeTpDetail.objects
                    .filter(id_demande=demande)
                    .aggregate(total=Sum("montant_total"))["total"]
                    or Decimal("0.00")
                )
                demande.montant_demande = total_details
                demande.save(update_fields=["montant_demande"])

                messages.success(request, "Acte ajouté à la demande avec succès.")
                return redirect("demande_tp_details", id_demande=demande.id_demande)

            except Exception as e:
                messages.error(request, f"Erreur lors de l'ajout de l'acte : {e}")
    else:
        form = DemandeTpDetailForm(initial={
            "id_acte": request.GET.get("id_acte", ""),
            "id_sous_acte": request.GET.get("id_sous_acte", ""),
        })
        _remplir_choices(form)

    # ⬅️ LE RETURN FINAL — OBLIGATOIRE
    return render(
        request,
        "core/demande_tp_detail_form.html",
        {
            "form": form,
            "demande": demande,
            "titre": "Ajouter un acte à la demande",
            "page": "demandes_tp",
        }
    )

def _remplir_choices(form):
        """Remplit les choices des champs du formulaire."""
        form.fields["id_acte"].choices = [
            (str(a.id_acte), f"{a.code_acte} - {a.libelle}")
            for a in actes
        ]

        # Si un acte est déjà sélectionné, charger ses sous-actes
        id_acte_selectionne = None
        if request.method == "POST":
            id_acte_selectionne = request.POST.get("id_acte")
        else:
            id_acte_selectionne = request.GET.get("id_acte")

        if id_acte_selectionne:
            sous_actes = (
                SousActe.objects
                .filter(id_acte_id=id_acte_selectionne, statut="ACTIF")
                .order_by("libelle")
            )
            form.fields["id_sous_acte"].choices = [
                (str(s.id_sous_acte), f"{s.code_sous_acte} - {s.libelle}")
                for s in sous_actes
            ]
        else:
            form.fields["id_sous_acte"].choices = []

        if request.method == "POST":
            form = DemandeTpDetailForm(request.POST)
        _remplir_choices(form)

        if form.is_valid():
            try:
                acte = Acte.objects.get(
                    id_acte=form.cleaned_data["id_acte"],
                    statut="ACTIF"
                )
                sous_acte = SousActe.objects.get(
                    id_sous_acte=form.cleaned_data["id_sous_acte"],
                    statut="ACTIF"
                )
                # ✅ Le prestataire est hérité de la demande
                prestataire = demande.id_prestataire

                # Vérifier que l'acte est couvert par une garantie active du contrat
                acte_couvert = (
                    GarantieActe.objects
                    .filter(
                        id_acte=acte,
                        statut="ACTIF",
                        id_garantie__contratgarantie__id_contrat=demande.id_contrat,
                        id_garantie__contratgarantie__statut="ACTIF",
                    )
                    .exists()
                )

                if not acte_couvert:
                    messages.error(
                        request,
                        "Cet acte n'est pas couvert par une garantie active "
                        "du contrat de cette demande."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                            "page": "demandes_tp"
                        }
                    )

                                # Récupérer le tarif applicable
                date_aujourdhui = timezone.now().date()
                tarif = (
                    TarifSousActe.objects
                    .filter(
                        id_sous_acte=sous_acte,
                        id_prestataire=prestataire,
                        statut="ACTIF",
                        date_debut__lte=date_aujourdhui,
                    )
                    .filter(
                        Q(date_fin__isnull=True) | Q(date_fin__gte=date_aujourdhui)
                    )
                    .order_by("-date_debut")
                    .first()
                )

                if not tarif:
                    messages.error(
                        request,
                        f"Aucun tarif actif pour ce sous-acte chez ce prestataire."
                    )
                    return render(
                        request,
                        "core/demande_tp_detail_form.html",
                        {
                            "form": form,
                            "demande": demande,
                            "titre": "Ajouter un acte à la demande",
                        }
                    )

                quantite = form.cleaned_data["quantite"]
                montant_unitaire = tarif.montant
                montant_total = quantite * montant_unitaire

                # Créer le détail
                DemandeTpDetail.objects.create(
                    id_demande=demande,
                    id_acte=acte,
                    id_sous_acte=sous_acte,
                    quantite=quantite,
                    montant_unitaire=montant_unitaire,
                    montant_total=montant_total,
                    observation=form.cleaned_data["observation"] or None,
                )

                # Recalculer le montant total de la demande
                total_details = (
                    DemandeTpDetail.objects
                    .filter(id_demande=demande)
                    .aggregate(total=Sum("montant_total"))["total"]
                    or Decimal("0.00")
                )
                demande.montant_demande = total_details
                demande.save(update_fields=["montant_demande"])

                messages.success(
                    request,
                    "Acte ajouté à la demande avec succès."
                )
                return redirect(
                    "demande_tp_details",
                    id_demande=demande.id_demande
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de l'ajout de l'acte : {e}"
                )

            else:
             form = DemandeTpDetailForm(initial={
               "id_acte": request.GET.get("id_acte", ""),
               "id_sous_acte": request.GET.get("id_sous_acte", ""),
})
        _remplir_choices(form)

        return render(
        request,
        "core/demande_tp_detail_form.html",
        {
            "form": form,
            "demande": demande,
            "titre": "Ajouter un acte à la demande",
        }
    )



def demande_tp_document_create(request, id_demande):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
    )

    if "DOCUMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter une pièce jointe."
        )
        return redirect(
            "demande_tp_details",
            id_demande=id_demande
        )

    try:
        demande = DemandeTp.objects.get(
            id_demande=id_demande
        )
    except DemandeTp.DoesNotExist:
        messages.error(
            request,
            "Demande de tiers payant introuvable."
        )
        return redirect("demandes_tp")

    if request.method == "POST":
        form = DocumentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            try:
                with transaction.atomic():

                    fichier = form.cleaned_data["fichier"]

                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    type_document = (
                        form.cleaned_data["type_document"]
                        or getattr(
                            fichier,
                            "content_type",
                            None
                        )
                        or "INCONNU"
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=type_document,
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    DemandeTpDocument.objects.create(
                        id_demande=demande,
                        id_document=document,
                        type_document=type_document,
                        date_ajout=timezone.now(),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="DEPOT_DOCUMENT",
                        module="DOCUMENT",
                        table_cible="document",
                        id_enregistrement=document.id_document,
                        nouvelle_valeur=(
                            f"Fichier : {document.nom_fichier}, "
                            f"Type : {document.type_document}, "
                            f"Demande : {demande.numero_demande}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="RATTACHEMENT_DOCUMENT",
                        module="DEMANDE TP",
                        table_cible="demande_tp_document",
                        id_enregistrement=demande.id_demande,
                        nouvelle_valeur=(
                            f"Document : {document.nom_fichier}, "
                            f"Demande : {demande.numero_demande}"
                        ),
                        description=(
                            f"Rattachement du document "
                            f"{document.nom_fichier} "
                            f"à la demande {demande.numero_demande}"
                        ),
                    )

                messages.success(
                    request,
                    "Pièce jointe ajoutée à la demande avec succès."
                )

                return redirect(
                    "demande_tp_details",
                    id_demande=demande.id_demande
                )

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de l'ajout de la pièce jointe : {e}"
                )

    else:
        form = DocumentForm()

    return render(
        request,
        "core/demande_tp_document_form.html",
        {
            "form": form,
            "demande": demande,
            "titre": "Ajouter une pièce jointe",
            "page": "demandes_tp",
        }
    )
def _dates_periode_plafond(date_reference, periode):
    """
    Retourne la date de début et la date de fin
    de la période correspondant au plafond.
    """

    if periode == "JOUR":
        return date_reference, date_reference

    if periode == "MOIS":
        debut = date_reference.replace(day=1)

        if date_reference.month == 12:
            fin = date(date_reference.year + 1, 1, 1) - timedelta(days=1)
        else:
            fin = date(
                date_reference.year,
                date_reference.month + 1,
                1
            ) - timedelta(days=1)

        return debut, fin

    if periode == "TRIMESTRE":
        mois_debut = ((date_reference.month - 1) // 3) * 3 + 1

        debut = date(
            date_reference.year,
            mois_debut,
            1
        )

        if mois_debut == 10:
            fin = date(
                date_reference.year + 1,
                1,
                1
            ) - timedelta(days=1)
        else:
            fin = date(
                date_reference.year,
                mois_debut + 3,
                1
            ) - timedelta(days=1)

        return debut, fin

    if periode == "SEMESTRE":
        if date_reference.month <= 6:
            debut = date(date_reference.year, 1, 1)
            fin = date(date_reference.year, 7, 1) - timedelta(days=1)
        else:
            debut = date(date_reference.year, 7, 1)
            fin = date(
                date_reference.year + 1,
                1,
                1
            ) - timedelta(days=1)

        return debut, fin

    # ANNEE par défaut
    debut = date(date_reference.year, 1, 1)
    fin = date(
        date_reference.year + 1,
        1,
        1
    ) - timedelta(days=1)

    return debut, fin


def _get_adhesion_demande(demande):
    """
    Retrouve l'adhésion active correspondant
    à la personne bénéficiaire et au contrat de la demande.

    Cas possibles :
    - la personne est directement l'adhérent ;
    - la personne est un ayant droit.
    """

    personne = demande.id_personne_beneficiaire

    adherent = (
        Adherent.objects
        .filter(
            id_personne=personne,
            statut="ACTIF"
        )
        .first()
    )

    if not adherent:
        ayant_droit = (
            AyantDroit.objects
            .select_related("id_adherent")
            .filter(
                id_personne=personne,
                statut="ACTIF"
            )
            .first()
        )

        if ayant_droit:
            adherent = ayant_droit.id_adherent

    if not adherent:
        return None

    date_demande = demande.date_demande.date()

    return (
        Adhesion.objects
        .filter(
            id_adherent=adherent,
            id_contrat=demande.id_contrat,
            statut="ACTIF",
            date_debut__lte=date_demande,
        )
        .filter(
            Q(date_fin__isnull=True)
            | Q(date_fin__gte=date_demande)
        )
        .order_by("-date_debut")
        .first()
    )
def _appliquer_plafonds_demande(
    demande,
    detail,
    garantie_acte,
    montant_accorde,
):
    date_reference = demande.date_demande.date()

    plafonds = list(
        Plafond.objects
        .select_related(
            "id_garantie_acte",
            "id_garantie_acte__id_garantie",
            "id_garantie_acte__id_acte",
        )
        .filter(
            id_garantie_acte=garantie_acte,
            statut="ACTIF",
            date_debut__lte=date_reference,
        )
        .filter(
            Q(date_fin__isnull=True)
            | Q(date_fin__gte=date_reference)
        )
        .order_by(
            "-date_debut",
            "-id_plafond",
        )
    )

    # Aucun plafond configuré pour cet acte.
    if not plafonds:
        return montant_accorde, [], None, detail.quantite

    adhesion = None
    montant_courant = montant_accorde
    informations = []

    quantite_autorisee = detail.quantite or Decimal("0.00")

    for plafond in plafonds:

        # Pour un plafond adhérent, il faut retrouver
        # l'adhérent principal, y compris si le bénéficiaire
        # est un ayant droit.
        if plafond.niveau_application == "ADHERENT":

            if adhesion is None:
                adhesion = _get_adhesion_demande(demande)

            if not adhesion:
                return (
                    Decimal("0.00"),
                    informations,
                    (
                        "Impossible d'appliquer le plafond adhérent : "
                        "aucune adhésion active trouvée pour cette demande."
                    ),
                    Decimal("0.00"),
                )

        date_debut_periode, date_fin_periode = (
            _dates_periode_plafond(
                date_reference,
                plafond.periode,
            )
        )

        consommations = (
            Consommation.objects
            .filter(
                id_acte=garantie_acte.id_acte,
                id_garantie=garantie_acte.id_garantie,
                statut="VALIDEE",
                date_prestation__gte=date_debut_periode,
                date_prestation__lte=date_fin_periode,
            )
        )

        if plafond.niveau_application == "ADHERENT":

            consommations = consommations.filter(
                id_adhesion__id_adherent=adhesion.id_adherent
            )

        elif plafond.niveau_application == "PERSONNE":

            consommations = consommations.filter(
                id_personne_beneficiaire=(
                    demande.id_personne_beneficiaire
                )
            )

        elif plafond.niveau_application == "CONTRAT":

            consommations = consommations.filter(
                id_adhesion__id_contrat=demande.id_contrat
            )

        else:
            return (
                Decimal("0.00"),
                informations,
                (
                    f"Niveau d'application inconnu : "
                    f"{plafond.niveau_application}"
                ),
                Decimal("0.00"),
            )

        totaux = consommations.aggregate(
            montant_consomme=Sum("montant_prise_en_charge"),
            quantite_consommee=Sum("quantite"),
        )

        montant_consomme = (
            totaux["montant_consomme"]
            or Decimal("0.00")
        )

        quantite_consommee = (
            totaux["quantite_consommee"]
            or Decimal("0.00")
        )

        montant_avant = montant_courant
        quantite_avant = quantite_autorisee

        reste_montant = None
        reste_quantite = None

        # -------------------------------------------------
        # PLAFOND DE QUANTITE
        # -------------------------------------------------

        if (
            plafond.type_plafond in ("QUANTITE", "MIXTE")
            and plafond.quantite_max is not None
        ):

            reste_quantite = max(
                Decimal("0.00"),
                Decimal(plafond.quantite_max)
                - quantite_consommee,
            )

            quantite_autorisee = min(
                quantite_autorisee,
                reste_quantite,
            )

            # Recalcul financier sur la quantité réellement autorisée
            if detail.quantite and detail.quantite > 0:

                montant_unitaire = (
                    detail.montant_total
                    / detail.quantite
                )

                taux = (
                    garantie_acte.taux_prise_en_charge
                    or Decimal("0.00")
                )

                franchise = (
                    garantie_acte.franchise
                    or Decimal("0.00")
                )

                montant_couvert_quantite = (
                    montant_unitaire
                    * quantite_autorisee
                    * taux
                    / Decimal("100")
                )

                montant_courant = max(
                    Decimal("0.00"),
                    montant_couvert_quantite - franchise,
                )

        # -------------------------------------------------
        # PLAFOND DE MONTANT
        # -------------------------------------------------

        if (
            plafond.type_plafond in ("MONTANT", "MIXTE")
            and plafond.montant_max is not None
        ):

            reste_montant = max(
                Decimal("0.00"),
                Decimal(plafond.montant_max)
                - montant_consomme,
            )

            montant_courant = min(
                montant_courant,
                reste_montant,
            )

        informations.append({
            "plafond": plafond,
            "montant_consomme": montant_consomme,
            "quantite_consommee": quantite_consommee,
            "reste_montant": reste_montant,
            "reste_quantite": reste_quantite,
            "montant_avant": montant_avant,
            "montant_apres": montant_courant,
            "quantite_avant": quantite_avant,
            "quantite_apres": quantite_autorisee,
            "date_debut_periode": date_debut_periode,
            "date_fin_periode": date_fin_periode,
        })

    montant_courant = max(
        Decimal("0.00"),
        montant_courant,
    )

    return (
        montant_courant,
        informations,
        None,
        quantite_autorisee,
    )



def demande_tp_pdf(request, id_demande):
    """Génère le PDF récapitulatif d'une demande de tiers payant."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("demandes_tp")

    try:
        demande = (
            DemandeTp.objects
            .select_related(
                "id_personne_beneficiaire",
                "id_contrat",
                "id_contrat__id_souscripteur",
                "id_prestataire",
            )
            .get(id_demande=id_demande)
        )
    except DemandeTp.DoesNotExist:
        messages.error(request, "Demande introuvable.")
        return redirect("demandes_tp")

    details = (
        DemandeTpDetail.objects
        .select_related("id_acte")
        .filter(id_demande=demande)
        .order_by("id_detail")
    )

    # Imports reportlab
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
    )
    import os
    from django.conf import settings

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Demande-{demande.numero_demande}.pdf"'
    )

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    elements = []
    styles = getSampleStyleSheet()

    style_titre = ParagraphStyle(
        "Titre", parent=styles["Title"], fontSize=18,
        textColor=colors.HexColor("#123b65"), alignment=2, leading=22,
    )
    style_section = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=12,
        textColor=colors.HexColor("#123b65"), spaceAfter=8, spaceBefore=10,
    )
    style_normal = styles["Normal"]

    # Logo
    logo_path = os.path.join(
        settings.BASE_DIR, "core", "static", "core", "img", "logo-sagps.png"
    )

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=5 * cm, height=2.2 * cm)
    else:
        logo = ""

    titre_header = Paragraph(
        "<b>DEMANDE DE TIERS PAYANT</b><br/>"
        f"<font size=11>N° {demande.numero_demande}</font>",
        style_titre,
    )

    header_table = Table([[logo, titre_header]], colWidths=[7 * cm, 10.5 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#123b65")),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Infos générales
    infos_data = [
        ["Date de demande", demande.date_demande.strftime("%d/%m/%Y %H:%M") if demande.date_demande else "-",
         "Statut", demande.statut],
        ["Date de décision", demande.date_decision.strftime("%d/%m/%Y") if demande.date_decision else "-",
         "Créé par", demande.utilisateur_creation or "-"],
    ]
    infos_table = Table(infos_data, colWidths=[3.5 * cm, 5 * cm, 3.5 * cm, 5.5 * cm])
    infos_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(infos_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Bénéficiaire
    elements.append(Paragraph("BÉNÉFICIAIRE", style_section))
    benef = demande.id_personne_beneficiaire
    benef_data = [
        ["Nom et Prénom", f"{benef.nom} {benef.prenom}"],
        ["Date de naissance", benef.date_naissance.strftime("%d/%m/%Y") if benef.date_naissance else "-"],
        ["Téléphone", benef.telephone or "-"],
        ["Contrat", demande.id_contrat.numero_contrat],
    ]
    benef_table = Table(benef_data, colWidths=[4 * cm, 13.5 * cm])
    benef_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(benef_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Prestataire
    elements.append(Paragraph("PRESTATAIRE", style_section))
    prest = demande.id_prestataire
    prest_data = [
        ["Raison sociale", prest.raison_sociale],
        ["Type", prest.type_prestataire or "-"],
        ["Adresse", prest.adresse or "-"],
        ["Téléphone", prest.telephone or "-"],
    ]
    prest_table = Table(prest_data, colWidths=[4 * cm, 13.5 * cm])
    prest_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(prest_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Actes demandés
    elements.append(Paragraph("ACTES DEMANDÉS", style_section))

    actes_data = [[
        "Code Acte", "Libellé", "Qté", "Montant unitaire", "Montant total"
    ]]

    for d in details:
        actes_data.append([
            d.id_acte.code_acte,
            d.id_acte.libelle[:45],
            f"{d.quantite:.2f}",
            f"{d.montant_unitaire:.2f}",
            f"{d.montant_total:.2f}",
        ])

    actes_table = Table(actes_data, repeatRows=1, colWidths=[
        2.5 * cm, 7 * cm, 1.5 * cm, 3.5 * cm, 3 * cm,
    ])
    actes_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(actes_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Total
    total_data = [["MONTANT TOTAL DEMANDÉ", f"{demande.montant_demande:.2f} DA"]]
    total_table = Table(total_data, colWidths=[5 * cm, 5 * cm], hAlign="RIGHT")
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 1 * cm))

    # Signatures
    signature_data = [[
        "Signature du bénéficiaire", "Cachet du prestataire", "Cachet de l'organisme"
    ], [
        "\n\n\n_________________",
        "\n\n\n_________________",
        "\n\n\n_________________",
    ]]
    signature_table = Table(signature_data, colWidths=[5.8 * cm, 5.8 * cm, 5.8 * cm])
    signature_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))
    elements.append(signature_table)

    document.build(elements)

    return response

def _generer_numero_pec():
    annee = timezone.now().year
    prefixe = f"PEC-{annee}-"

    numeros = (
        PriseEnCharge.objects
        .filter(numero_pec__startswith=prefixe)
        .values_list("numero_pec", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_pec = f"{prefixe}{prochain:04d}"

    while PriseEnCharge.objects.filter(
        numero_pec=numero_pec
    ).exists():
        prochain += 1
        numero_pec = f"{prefixe}{prochain:04d}"

    return numero_pec
  



def demande_tp_valider(request, id_demande):
    """
    Valide une demande TP et crée la PEC automatiquement.
    
    Utilise le module centralisé core.services.calculs pour TOUS les calculs.
    """
    # ============================================================
    # 1. VÉRIFICATIONS
    # ============================================================
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    id_utilisateur = request.session["id_utilisateur"]

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "DEMANDE_VALIDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de valider une demande.")
        return redirect("demandes_tp")

    # ============================================================
    # 2. RÉCUPÉRATION DE LA DEMANDE
    # ============================================================
    try:
        demande = (
            DemandeTp.objects
            .select_related(
                "id_personne_beneficiaire",
                "id_contrat",
                "id_prestataire",
            )
            .get(id_demande=id_demande)
        )
    except DemandeTp.DoesNotExist:
        messages.error(request, "Demande de tiers payant introuvable.")
        return redirect("demandes_tp")

    if demande.statut != "EN_ATTENTE":
        messages.error(request, "Cette demande n'est plus en attente de validation.")
        return redirect("demande_tp_details", id_demande=demande.id_demande)

    # ============================================================
    # 3. CALCUL VIA LE MODULE CENTRALISÉ
    # ============================================================
    from core.services.calculs import calculer_pour_demande

    resultats = calculer_pour_demande(demande)

    # Vérifier que la demande a des actes
    if resultats["nb_actes"] == 0:
        messages.error(request, "Impossible de valider une demande sans acte.")
        return redirect("demande_tp_details", id_demande=demande.id_demande)

    # Afficher les erreurs éventuelles
    if resultats["erreurs"]:
        for erreur in resultats["erreurs"]:
            messages.warning(request, erreur)

    # ============================================================
    # 4. TRAITEMENT DU POST
    # ============================================================
    if request.method == "POST":
        # Bloquer si un acte a une erreur critique
        if resultats["erreurs"]:
            messages.error(
                request,
                "La demande ne peut pas être validée car un acte "
                "n'a pas de garantie applicable."
            )
            return redirect("demande_tp_valider", id_demande=demande.id_demande)

        try:
            # 4.1 — Générer le numéro de PEC
            numero_pec = _generer_numero_pec()

            # 4.2 — Créer la PEC
            pec = PriseEnCharge.objects.create(
                numero_pec=numero_pec,
                id_demande=demande,
                date_pec=timezone.now(),
                montant_demande=resultats["total_demande"],
                montant_accepte=resultats["total_accepte"],
                montant_rejete=resultats["total_rejete"],
                statut="EN_ATTENTE",
                date_expiration=timezone.now().date() + timedelta(days=30),
                utilisateur_validation=str(id_utilisateur),
            )

            # 4.3 — Mettre à jour le statut de la demande
            demande.statut = "ACCEPTEE"
            demande.date_decision = timezone.now()
            demande.save()

            # 4.4 — Audit
            enregistrer_audit(
                request=request,
                type_action="VALIDATION",
                module="DEMANDES TP",
                table_cible="demande_tp",
                id_enregistrement=demande.id_demande,
                ancienne_valeur="Statut : EN_ATTENTE",
                nouvelle_valeur=f"Statut : ACCEPTEE, PEC : {pec.numero_pec}",
                description=(
                    f"Validation de la demande {demande.numero_demande} "
                    f"et création de la PEC {pec.numero_pec}"
                ),
            )

            # 4.5 — Message de succès
            messages.success(
                request,
                f"✅ Demande {demande.numero_demande} validée. "
                f"PEC {pec.numero_pec} créée avec succès."
            )

            # 4.6 — Rediriger vers la PEC
            return redirect("prise_en_charge_details", id_pec=pec.id_pec)

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la création de la prise en charge : {e}"
            )
            return redirect("demande_tp_details", id_demande=demande.id_demande)

    # ============================================================
    # 5. AFFICHAGE (GET)
    # ============================================================
    return render(
        request,
        "core/demande_tp_valider.html",
        {
            "demande": demande,
            "calculs": resultats["calculs"],
            "montant_accepte_total": resultats["total_accepte"],
            "montant_rejete_total": resultats["total_rejete"],
            "erreurs": resultats["erreurs"],
        }
    )


