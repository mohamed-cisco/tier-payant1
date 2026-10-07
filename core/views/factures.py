# core/views/factures.py
"""
Vues de gestion des factures.

Fonctions :
- factures : liste
- facture_create : créer
- facture_detail : détail
- facture_valider : valider
- facture_export_excel : export Excel
- facture_export_pdf : export PDF
- facture_pdf : PDF facture
- _generer_numero_facture : helper
"""

from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import FactureForm
from core.models import (
    Consommation,
    DetailFacture,
    Facture,
    Prestataire,
    RolePermission,
)
from core.views.champs import (
    get_champs_pour_entite,
    sauvegarder_valeurs_champs,
)
from core.views.dashboard import enregistrer_audit


def _generer_numero_facture():
    """Génère un numéro unique de facture."""
    annee = timezone.now().year
    prefixe = f"FAC-{annee}-"

    numeros = (
        Facture.objects
        .filter(numero_facture__startswith=prefixe)
        .values_list("numero_facture", flat=True)
    )

    valeurs = []
    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_facture = f"{prefixe}{prochain:04d}"

    while Facture.objects.filter(numero_facture=numero_facture).exists():
        prochain += 1
        numero_facture = f"{prefixe}{prochain:04d}"

    return numero_facture


def factures(request):
    """Liste des factures."""
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

    if "FACTURE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les factures."
        )
        return redirect("accueil")

    factures_liste = (
        Facture.objects
        .select_related("id_prestataire")
        .order_by("-id_facture")
    )

    return render(
        request,
        "core/factures.html",
        {
            "factures": factures_liste,
            "permissions": permissions,
            "page": "factures",
        }
    )


def facture_create(request):
    """Créer une nouvelle facture."""
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

    if "FACTURE_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("factures")

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    consommations = (
        Consommation.objects
        .filter(statut="VALIDEE")
        .select_related("id_prestataire", "id_acte", "id_personne_beneficiaire")
        .order_by("date_prestation", "id_consommation")
    )

    if request.method == "POST":
        form = FactureForm(request.POST)

        form.fields["id_prestataire"].choices = [
            (str(p.id_prestataire), f"{p.code_prestataire} - {p.raison_sociale}")
            for p in prestataires
        ]

        if form.is_valid():
            try:
                id_prestataire = form.cleaned_data["id_prestataire"]
                prestataire = Prestataire.objects.get(
                    id_prestataire=id_prestataire, statut="ACTIF"
                )

                # Détection de doublon
                date_limite = timezone.now().date() - timedelta(days=30)

                doublon = Facture.objects.filter(
                    id_prestataire=prestataire,
                    date_facture__gte=date_limite,
                    statut__in=["EN_ATTENTE", "VALIDEE"],
                ).order_by("-date_facture").first()

                if doublon and not request.POST.get("confirmer_doublon"):
                    messages.warning(
                        request,
                        f"⚠️ Une facture récente existe déjà pour ce prestataire : "
                        f"{doublon.numero_facture} "
                        f"({doublon.date_facture.strftime('%d/%m/%Y')}, "
                        f"{doublon.montant_valide} DA, statut {doublon.statut}). "
                        f"Voulez-vous vraiment créer une nouvelle facture ?"
                    )
                    return render(
                        request,
                        "core/facture_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle facture",
                            "consommations": consommations,
                            "page": "factures",
                            "doublon_detecte": doublon,
                            "champs_disponibles": get_champs_pour_entite("FACTURE"),
                        }
                    )

                # Traiter les consommations
                consommations_prestataire = [
                    c for c in consommations if c.id_prestataire_id == int(id_prestataire)
                ]

                consommations_deja_facturees = set(
                    DetailFacture.objects.values_list("id_consommation_id", flat=True)
                )

                consommations_prestataire = [
                    c for c in consommations_prestataire
                    if c.id_consommation not in consommations_deja_facturees
                    and c.montant_prise_en_charge > 0
                ]

                if not consommations_prestataire:
                    messages.error(
                        request,
                        "Aucune consommation disponible pour ce prestataire."
                    )
                    return render(
                        request,
                        "core/facture_form.html",
                        {
                            "form": form,
                            "titre": "Nouvelle facture",
                            "consommations": consommations,
                            "page": "factures",
                            "champs_disponibles": get_champs_pour_entite("FACTURE"),
                        }
                    )

                montant_total = sum(c.montant_base for c in consommations_prestataire)
                montant_valide = sum(c.montant_prise_en_charge for c in consommations_prestataire)
                montant_rejete = sum(c.montant_reste for c in consommations_prestataire)

                facture = Facture.objects.create(
                    id_prestataire=prestataire,
                    numero_facture=_generer_numero_facture(),
                    date_facture=form.cleaned_data["date_facture"],
                    date_reception=form.cleaned_data["date_reception"],
                    montant_total=montant_total,
                    montant_valide=montant_valide,
                    montant_rejete=montant_rejete,
                    statut="EN_ATTENTE",
                    date_validation=None,
                    utilisateur_validation=None,
                    observation=form.cleaned_data["observation"] or None,
                )

                for consommation in consommations_prestataire:
                    DetailFacture.objects.create(
                        id_facture=facture,
                        id_consommation=consommation,
                        id_acte=consommation.id_acte,
                        quantite=consommation.quantite,
                        montant_unitaire=(consommation.montant_base / consommation.quantite),
                        montant_total=consommation.montant_base,
                        montant_valide=consommation.montant_prise_en_charge,
                        montant_rejete=consommation.montant_reste,
                        statut="EN_ATTENTE",
                        id_motif_rejet=None,
                    )

                sauvegarder_valeurs_champs(request, "FACTURE", facture.id_facture)

                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="FACTURE",
                    table_cible="facture",
                    id_enregistrement=facture.id_facture,
                    nouvelle_valeur=facture.numero_facture,
                    description=f"Création de la facture {facture.numero_facture}",
                )

                messages.success(
                    request,
                    f"Facture {facture.numero_facture} créée avec succès."
                )
                return redirect("factures")

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = FactureForm()
        form.fields["id_prestataire"].choices = [
            (str(p.id_prestataire), f"{p.code_prestataire} - {p.raison_sociale}")
            for p in prestataires
        ]

    champs = get_champs_pour_entite("FACTURE")
    for c in champs:
        c.valeur_actuelle = None
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/facture_form.html",
        {
            "form": form,
            "titre": "Nouvelle facture",
            "consommations": consommations,
            "page": "factures",
            "champs_disponibles": champs,
        }
    )