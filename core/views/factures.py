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
    get_valeurs_champs_entite,
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


def facture_export_excel(request):
    """Export Excel de la liste des factures."""
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
            "Vous n'avez pas l'autorisation d'exporter les factures."
        )
        return redirect("factures")

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from django.http import HttpResponse

    # Récupérer les factures
    factures_liste = (
        Facture.objects
        .select_related("id_prestataire")
        .order_by("-date_facture", "-id_facture")
    )

    # Créer le classeur
    workbook = openpyxl.Workbook()
    feuille = workbook.active
    feuille.title = "Factures"

    # Styles
    font_titre = Font(bold=True, size=14, color="123B65")
    font_entete = Font(bold=True, color="FFFFFF", size=11)
    font_total = Font(bold=True, size=11, color="123B65")
    fill_entete = PatternFill(start_color="123B65", end_color="123B65", fill_type="solid")
    fill_total = PatternFill(start_color="EAF2FB", end_color="EAF2FB", fill_type="solid")
    fill_alt = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    # Titre
    feuille["A1"] = "LISTE DES FACTURES"
    feuille["A1"].font = font_titre
    feuille["A1"].alignment = Alignment(horizontal="center")
    feuille.merge_cells("A1:I1")

    # Sous-titre : date d'export
    feuille["A2"] = f"Exporté le {timezone.now().strftime('%d/%m/%Y à %H:%M')}"
    feuille["A2"].font = Font(italic=True, size=9, color="666666")
    feuille["A2"].alignment = Alignment(horizontal="center")
    feuille.merge_cells("A2:I2")

    # En-têtes (ligne 4)
    entetes = [
        "N° Facture",
        "Prestataire",
        "Date facture",
        "Date réception",
        "Montant total",
        "Montant validé",
        "Montant rejeté",
        "Statut",
        "Date validation",
    ]

    ligne_entete = 4
    for col_num, entete in enumerate(entetes, start=1):
        cellule = feuille.cell(row=ligne_entete, column=col_num, value=entete)
        cellule.font = font_entete
        cellule.fill = fill_entete
        cellule.alignment = Alignment(horizontal="center", vertical="center")
        cellule.border = border

    # Données
    ligne = ligne_entete + 1
    total_montant = 0
    total_valide = 0
    total_rejete = 0

    for idx, facture in enumerate(factures_liste):
        ligne_courante = ligne + idx
        values = [
            facture.numero_facture,
            facture.id_prestataire.raison_sociale,
            facture.date_facture.strftime("%d/%m/%Y") if facture.date_facture else "-",
            facture.date_reception.strftime("%d/%m/%Y") if facture.date_reception else "-",
            float(facture.montant_total or 0),
            float(facture.montant_valide or 0),
            float(facture.montant_rejete or 0),
            facture.statut,
            facture.date_validation.strftime("%d/%m/%Y") if facture.date_validation else "-",
        ]

        for col_num, val in enumerate(values, start=1):
            cellule = feuille.cell(row=ligne_courante, column=col_num, value=val)
            cellule.border = border
            cellule.alignment = Alignment(vertical="center", horizontal="center")
            if idx % 2 == 1:
                cellule.fill = fill_alt

        total_montant += float(facture.montant_total or 0)
        total_valide += float(facture.montant_valide or 0)
        total_rejete += float(facture.montant_rejete or 0)

    # Ligne de totaux
    ligne_total = ligne + len(factures_liste)
    feuille.cell(row=ligne_total, column=1, value="TOTAL").font = font_total
    feuille.merge_cells(
        start_row=ligne_total, start_column=1,
        end_row=ligne_total, end_column=4
    )
    feuille.cell(row=ligne_total, column=1).alignment = Alignment(horizontal="right", vertical="center")

    for col_num, val in enumerate([total_montant, total_valide, total_rejete], start=5):
        cellule = feuille.cell(row=ligne_total, column=col_num, value=val)
        cellule.font = font_total
        cellule.fill = fill_total
        cellule.border = border
        cellule.alignment = Alignment(horizontal="center", vertical="center")

    for col_num in [8, 9]:
        cellule = feuille.cell(row=ligne_total, column=col_num, value="")
        cellule.fill = fill_total
        cellule.border = border

    # Ajuster la largeur des colonnes
    largeurs = [16, 25, 13, 14, 15, 15, 15, 14, 15]
    for i, largeur in enumerate(largeurs, start=1):
        feuille.column_dimensions[chr(64 + i)].width = largeur

    # Figer l'en-tête
    feuille.freeze_panes = "A5"

    # Envoyer le fichier
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="factures_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
    )
    workbook.save(response)
    return response




def facture_valider(request, id_facture):
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

    if "FACTURE_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider une facture."
        )
        return redirect("factures")

    try:
        facture = Facture.objects.get(
            id_facture=id_facture
        )
    except Facture.DoesNotExist:
        messages.error(
            request,
            "Facture introuvable."
        )
        return redirect("factures")

    if request.method == "POST":

        if facture.statut != "EN_ATTENTE":
            messages.error(
                request,
                "Cette facture a déjÃ  été traitée."
            )
            return redirect("factures")

        facture.statut = "VALIDEE"
        facture.date_validation = timezone.now()
        facture.utilisateur_validation = str(
            request.session.get("id_utilisateur")
        )
        facture.save()

        # Validation des détails de la facture
        DetailFacture.objects.filter(
            id_facture=facture
        ).update(
            statut="VALIDEE"
        )

        messages.success(
            request,
            "Facture validée avec succès."
        )

    return redirect("factures")



def facture_detail(request, id_facture):
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
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("factures")

    try:
        facture = (
            Facture.objects
            .select_related("id_prestataire")
            .get(id_facture=id_facture)
        )
    except Facture.DoesNotExist:
        messages.error(request, "Facture introuvable.")
        return redirect("factures")

    details = (
        DetailFacture.objects
        .select_related("id_consommation", "id_acte")
        .filter(id_facture=facture)
        .order_by("id_detail_facture")
    )

    champs = get_valeurs_champs_entite("FACTURE", facture.id_facture)
    champs = [c for c in champs if c["valeur"] and str(c["valeur"]).strip()]

    return render(
        request,
        "core/facture_detail.html",
        {
            "facture": facture,
            "details": details,
            "champs_personnalises": champs,
            "page": "factures",
        }
    )



def _generer_reference_reglement(mode_reglement):
    """Génère une référence unique pour un règlement selon son mode."""
    annee = timezone.now().year

    prefixes = {
        "VIREMENT": f"VIR-{annee}-",
        "CHEQUE": f"CHQ-{annee}-",
        "ESPECES": f"ESP-{annee}-",
    }

    prefixe = prefixes.get(mode_reglement, f"REF-{annee}-")

    # Récupère toutes les références existantes pour ce préfixe
    references = (
        Reglement.objects
        .filter(reference_reglement__startswith=prefixe)
        .values_list("reference_reglement", flat=True)
    )

    valeurs = []
    for ref in references:
        try:
            valeurs.append(int(ref.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    reference = f"{prefixe}{prochain:04d}"

    # Vérifie l'unicité
    while Reglement.objects.filter(
        reference_reglement=reference
    ).exists():
        prochain += 1
        reference = f"{prefixe}{prochain:04d}"

    return reference
def _generer_numero_reglement():
    """Génère un numéro de règlement unique."""
    annee = timezone.now().year
    prefixe = f"REG-{annee}-"

    numeros = (
        Reglement.objects
        .filter(numero_reglement__startswith=prefixe)
        .values_list("numero_reglement", flat=True)
    )




def facture_export_pdf(request):

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

    if "FACTURE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les factures."
        )
        return redirect("factures")

    from django.http import HttpResponse

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = 'attachment; filename="factures.pdf"'

    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    elements = []

    styles = getSampleStyleSheet()

    titre = Paragraph(
        "Liste des factures",
        styles["Title"]
    )

    elements.append(titre)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    factures_list = (
        Facture.objects
        .select_related("id_prestataire")
        .order_by("-date_facture")
    )

    data = [
        [
            "N° Facture",
            "Prestataire",
            "Date",
            "Montant total",
            "Montant validé",
            "Montant rejeté",
            "Statut",
        ]
    ]

    for facture in factures_list:

        data.append([
            facture.numero_facture,
            facture.id_prestataire.raison_sociale,
            facture.date_facture.strftime("%d/%m/%Y")
            if facture.date_facture else "",
            f"{facture.montant_total:.2f}",
            f"{facture.montant_valide:.2f}",
            f"{facture.montant_rejete:.2f}",
            facture.statut,
        ])

    tableau = Table(
        data,
        repeatRows=1,
        colWidths=[
            3 * cm,
            5 * cm,
            3 * cm,
            3.5 * cm,
            3.5 * cm,
            3.5 * cm,
            3 * cm,
        ]
    )

    tableau.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.grey
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, 0),
                10
            ),
        ])
    )

    elements.append(tableau)

    document.build(elements)

    return response




def facture_pdf(request, id_facture):
    """Génère le PDF détaillé d'une facture."""
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
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("factures")

    try:
        facture = (
            Facture.objects
            .select_related("id_prestataire")
            .get(id_facture=id_facture)
        )
    except Facture.DoesNotExist:
        messages.error(request, "Facture introuvable.")
        return redirect("factures")

    details = (
        DetailFacture.objects
        .select_related(
            "id_consommation",
            "id_consommation__id_personne_beneficiaire",
            "id_acte",
        )
        .filter(id_facture=facture)
        .order_by("id_detail_facture")
    )

    import os
    from django.conf import settings
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Facture-{facture.numero_facture}.pdf"'
    )

    document = SimpleDocTemplate(
        response, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    elements = []
    styles = getSampleStyleSheet()

    style_titre = ParagraphStyle(
        "Titre", parent=styles["Title"], fontSize=20,
        textColor=colors.HexColor("#123b65"), alignment=2, leading=26,
    )
    style_section = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=12,
        textColor=colors.HexColor("#123b65"), spaceAfter=8, spaceBefore=10,
    )

    # En-tête
    logo_path = os.path.join(
        settings.BASE_DIR, "core", "static", "core", "img", "logo-sagps.png"
    )
    logo = Image(logo_path, width=5 * cm, height=2.2 * cm) if os.path.exists(logo_path) else ""

    titre_header = Paragraph(
        "<b>FACTURE</b><br/>"
        f"<font size=11>N° {facture.numero_facture}</font>",
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

    # Infos facture
    infos_data = [
        ["Date de facture",
         facture.date_facture.strftime("%d/%m/%Y") if facture.date_facture else "-",
         "Date de réception",
         facture.date_reception.strftime("%d/%m/%Y") if facture.date_reception else "-"],
        ["Statut", facture.statut,
         "N° Prestataire",
         facture.id_prestataire.code_prestataire],
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

    # Prestataire
    elements.append(Paragraph("PRESTATAIRE", style_section))
    prest = facture.id_prestataire
    prest_data = [
        ["Raison sociale", prest.raison_sociale],
        ["Type", prest.type_prestataire or "-"],
        ["NIF", prest.nif or "-"],
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

    # Détails
    elements.append(Paragraph("DÉTAILS DE LA FACTURE", style_section))

       # Style pour les cellules (retour à la ligne automatique)
    style_cell = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontSize=8, leading=10,
    )
    style_cell_center = ParagraphStyle(
        "CellC", parent=styles["Normal"], fontSize=8, leading=10, alignment=1,
    )
    style_cell_right = ParagraphStyle(
        "CellR", parent=styles["Normal"], fontSize=8, leading=10, alignment=2,
    )
    style_head = ParagraphStyle(
        "Head", parent=styles["Normal"], fontSize=8, leading=10,
        textColor=colors.white, fontName="Helvetica-Bold", alignment=1,
    )

    details_data = [[
        Paragraph("Code acte", style_head),
        Paragraph("Libellé", style_head),
        Paragraph("Bénéficiaire", style_head),
        Paragraph("Qté", style_head),
        Paragraph("Montant total", style_head),
        Paragraph("Montant validé", style_head),
        Paragraph("Montant rejeté", style_head),
    ]]

    for d in details:
        conso = d.id_consommation
        benef = conso.id_personne_beneficiaire if conso else None
        benef_nom = f"{benef.nom} {benef.prenom}" if benef else "-"

        details_data.append([
            Paragraph(d.id_acte.code_acte if d.id_acte else "-", style_cell),
            Paragraph(d.id_acte.libelle if d.id_acte else "-", style_cell),
            Paragraph(benef_nom, style_cell),
            Paragraph(f"{d.quantite:.2f}", style_cell_center),
            Paragraph(f"{d.montant_total:.2f}", style_cell_right),
            Paragraph(f"{d.montant_valide:.2f}", style_cell_right),
            Paragraph(f"{d.montant_rejete:.2f}", style_cell_right),
        ])

        details_table = Table(details_data, repeatRows=1, colWidths=[
        1.8 * cm, 4.8 * cm, 3.3 * cm, 1.1 * cm, 2.1 * cm, 2.1 * cm, 2.3 * cm,
    ])
    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Totaux
    totaux_data = [
        ["Montant total", f"{facture.montant_total:.2f} DA"],
        ["Montant validé", f"{facture.montant_valide:.2f} DA"],
        ["Montant rejeté", f"{facture.montant_rejete:.2f} DA"],
    ]
    totaux_table = Table(totaux_data, colWidths=[5 * cm, 5 * cm], hAlign="RIGHT")
    totaux_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#166534")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(totaux_table)
    elements.append(Spacer(1, 1 * cm))

    # Signatures
    sig_data = [[
        "Cachet du prestataire", "Cachet de l'organisme"
    ], [
        "\n\n\n_________________", "\n\n\n_________________",
    ]]
    sig_table = Table(sig_data, colWidths=[8.75 * cm, 8.75 * cm])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))
    elements.append(sig_table)

    document.build(elements)
    return response

