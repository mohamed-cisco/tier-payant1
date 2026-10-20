# core/views/adhesions.py
"""
Vues de gestion des adhésions et personnes.

Fonctions :
- adhesions : liste
- adhesion_create : créer
- adhesion_modifier : modifier
- adhesion_radier : radier
- adhesion_export_excel : export Excel
- adhesion_pdf : PDF
- personne_create : créer une personne
- _generer_numero_adhesion : helper
"""

import openpyxl
from openpyxl.styles import Font
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import (
    AdhesionForm,
    PersonneForm,
)
from core.models import (
    Adherent,
    Adhesion,
    AyantDroit,
    Contrat,
    Personne,
    RolePermission,
)
from core.views.champs import (
    get_champs_pour_entite,
    sauvegarder_valeurs_champs,
)
from core.views.dashboard import enregistrer_audit

# Imports PDF
from django.conf import settings
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


def _generer_numero_adhesion():
    annee = timezone.now().year
    prefixe = f"ADHES-{annee}-"

    numeros = (
        Adhesion.objects
        .filter(numero_adhesion__startswith=prefixe)
        .values_list("numero_adhesion", flat=True)
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

    numero_adhesion = f"{prefixe}{prochain:04d}"

    while Adhesion.objects.filter(
        numero_adhesion=numero_adhesion
    ).exists():
        prochain += 1
        numero_adhesion = f"{prefixe}{prochain:04d}"

    return numero_adhesion




def adhesions(request):
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

    if "ADHESION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les adhésions."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    adhesions = (
        Adhesion.objects
        .select_related(
            "id_adherent",
            "id_adherent__id_personne",
            "id_contrat",
            "id_contrat__id_souscripteur",
        )
        .all()
        .order_by("-id_adhesion")
    )
    
    
    if recherche:
        from django.db.models import Q

        adhesions = adhesions.filter(
            Q(numero_adhesion__icontains=recherche)
            | Q(
                id_adherent__numero_adherent__icontains=recherche
            )
            | Q(
                id_contrat__numero_contrat__icontains=recherche
            )
            | Q(
                id_contrat__id_souscripteur__raison_sociale__icontains=recherche
            )
        )

    if statut:
        adhesions = adhesions.filter(
            statut=statut
        )

    return render(
        request,
        "core/adhesions.html",
        {
            "adhesions": adhesions,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "adhesions",
        }
    )



def adhesion_create(request):
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

    if "ADHESION_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer une adhésion."
        )
        return redirect("adhesions")

    adherents = (
        Adherent.objects
        .filter(statut="ACTIF")
        .order_by("numero_adherent")
    )

    contrats = (
        Contrat.objects
        .filter(statut="ACTIF")
        .select_related("id_souscripteur")
        .order_by("numero_contrat")
    )
    id_contrat_preselectionne = request.GET.get(
        "id_contrat",
        ""
    ).strip()

    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects
            .filter(
                id_contrat=id_contrat_preselectionne,
                statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )    
    id_contrat_preselectionne = request.GET.get(
        "id_contrat",
        ""
    ).strip()

    contrat_preselectionne = None

    if id_contrat_preselectionne:
        contrat_preselectionne = (
            Contrat.objects
            .filter(
                id_contrat=id_contrat_preselectionne,
                statut="ACTIF"
            )
            .select_related("id_souscripteur")
            .first()
        )

    if request.method == "POST":
        form = AdhesionForm(request.POST)

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                f"{a.numero_adherent}"
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]
        if contrat_preselectionne:
            form.initial["id_contrat"] = (
                str(contrat_preselectionne.id_contrat)
                
            )

        if form.is_valid():
            try:
                adherent = Adherent.objects.get(
                    id_adherent=form.cleaned_data["id_adherent"],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.get(
                    id_contrat=form.cleaned_data["id_contrat"],
                    statut="ACTIF"
                )

                Adhesion.objects.create(
                    id_adherent=adherent,
                    id_contrat=contrat,
                    numero_adhesion=_generer_numero_adhesion(),
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                messages.success(
                    request,
                    "Adhésion créée avec succès."
                )

                return redirect("adhesions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = AdhesionForm()

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                f"{a.numero_adherent}"
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

    return render(
        request,
        "core/adhesion_form.html",
        {
            "form": form,
            "titre": "Nouvelle adhésion",
            "contrat_preselectionne": contrat_preselectionne,
            "page": "adhesions",
        }
    )




def adhesion_modifier(request, id_adhesion):
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

    if "ADHESION_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier une adhésion."
        )
        return redirect("adhesions")

    try:
        adhesion = Adhesion.objects.get(
            id_adhesion=id_adhesion
        )
    except Adhesion.DoesNotExist:
        messages.error(
            request,
            "Adhésion introuvable."
        )
        return redirect("adhesions")

    adherents = (
        Adherent.objects
        .filter(statut="ACTIF")
        .order_by("numero_adherent")
    )

    contrats = (
        Contrat.objects
        .filter(statut="ACTIF")
        .select_related("id_souscripteur")
        .order_by("numero_contrat")
    )

    if request.method == "POST":
        form = AdhesionForm(request.POST)

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                a.numero_adherent
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

        if form.is_valid():
            try:
                adherent = Adherent.objects.get(
                    id_adherent=form.cleaned_data["id_adherent"],
                    statut="ACTIF"
                )

                contrat = Contrat.objects.get(
                    id_contrat=form.cleaned_data["id_contrat"],
                    statut="ACTIF"
                )

                adhesion.id_adherent = adherent
                adhesion.id_contrat = contrat
               

                adhesion.date_debut = (
                    form.cleaned_data["date_debut"]
                )
                adhesion.date_fin = (
                    form.cleaned_data["date_fin"]
                )
                adhesion.statut = (
                    form.cleaned_data["statut"]
                )

                adhesion.save()

                messages.success(
                    request,
                    "Adhésion modifiée avec succès."
                )

                return redirect("adhesions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = AdhesionForm(
            initial={
                "id_adherent": str(
                    adhesion.id_adherent_id
                ),
                "id_contrat": str(
                    adhesion.id_contrat_id
                ),
                "numero_adhesion": adhesion.numero_adhesion,
                "date_debut": adhesion.date_debut,
                "date_fin": adhesion.date_fin,
                "statut": adhesion.statut,
            }
        )

        form.fields["id_adherent"].choices = [
            (
                str(a.id_adherent),
                a.numero_adherent
            )
            for a in adherents
        ]

        form.fields["id_contrat"].choices = [
            (
                str(c.id_contrat),
                f"{c.numero_contrat} - {c.id_souscripteur.raison_sociale}"
            )
            for c in contrats
        ]

    return render(
        request,
        "core/adhesion_form.html",
        {
            "form": form,
            "titre": "Modifier l'adhésion",
        }
    )



def adhesion_radier(request, id_adhesion):
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

    if "ADHESION_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une adhésion."
        )
        return redirect("adhesions")

    try:
        adhesion = Adhesion.objects.get(
            id_adhesion=id_adhesion
        )
    except Adhesion.DoesNotExist:
        messages.error(
            request,
            "Adhésion introuvable."
        )
        return redirect("adhesions")

    if request.method == "POST":
        adhesion.statut = "RADIE"
        adhesion.save()

        messages.success(
            request,
            "Adhésion radiée avec succès."
        )

    return redirect("adhesions")



def adhesion_export_excel(request):

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

    if "ADHESION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les adhésions."
        )
        return redirect("adhesions")

    import openpyxl
    from openpyxl.styles import Font
    from django.http import HttpResponse

    adhesions_list = (
        Adhesion.objects
        .select_related(
            "id_adherent",
            "id_adherent__id_personne",
            "id_contrat",
            "id_contrat__id_souscripteur",
        )
        .all()
        .order_by("numero_adhesion")
    )

    workbook = openpyxl.Workbook()
    feuille = workbook.active
    feuille.title = "Adhesions"

    entetes = [
        "Numéro adhésion",
        "Numéro adhérent",
        "Nom",
        "Prénom",
        "Numéro contrat",
        "Souscripteur",
        "Date début",
        "Date fin",
        "Statut",
        "Date création",
    ]

    feuille.append(entetes)

    for cellule in feuille[1]:
        cellule.font = Font(bold=True)

    for adhesion in adhesions_list:

        personne = adhesion.id_adherent.id_personne
        contrat = adhesion.id_contrat
        souscripteur = contrat.id_souscripteur

        feuille.append([
            adhesion.numero_adhesion,
            adhesion.id_adherent.numero_adherent,
            personne.nom,
            personne.prenom,
            contrat.numero_contrat,
            souscripteur.raison_sociale,
            adhesion.date_debut,
            adhesion.date_fin,
            adhesion.statut,
            adhesion.date_creation,
        ])

    for colonne in feuille.columns:

        longueur_max = 0
        lettre_colonne = colonne[0].column_letter

        for cellule in colonne:

            try:
                longueur = (
                    len(str(cellule.value))
                    if cellule.value
                    else 0
                )

                if longueur > longueur_max:
                    longueur_max = longueur

            except Exception:
                pass

        feuille.column_dimensions[
            lettre_colonne
        ].width = min(longueur_max + 2, 50)

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response[
        "Content-Disposition"
    ] = 'attachment; filename="adhesions.xlsx"'

    workbook.save(response)

    return response




def adhesion_pdf(request, id_adhesion):
    """Génère le PDF d'une adhésion."""
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

    if "ADHESION_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("adhesions")

    try:
        adhesion = (
            Adhesion.objects
            .select_related(
                "id_adherent",
                "id_adherent__id_personne",
                "id_contrat",
                "id_contrat__id_souscripteur",
            )
            .get(id_adhesion=id_adhesion)
        )
    except Adhesion.DoesNotExist:
        messages.error(request, "Adhésion introuvable.")
        return redirect("adhesions")

    ayants_droit = (
        AyantDroit.objects
        .select_related("id_personne")
        .filter(id_adherent=adhesion.id_adherent, statut="ACTIF")
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
        f'attachment; filename="Adhesion-{adhesion.numero_adhesion}.pdf"'
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

    titre = Paragraph(
        "<b>ATTESTATION D'ADHÉSION</b><br/>"
        f"<font size=11>N° {adhesion.numero_adhesion}</font>",
        style_titre,
    )

    header = Table([[logo, titre]], colWidths=[7 * cm, 10.5 * cm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#123b65")),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 0.6 * cm))

    # Adhérent
    elements.append(Paragraph("ADHÉRENT", style_section))
    personne = adhesion.id_adherent.id_personne
    info_data = [
        ["Nom et Prénom", f"{personne.nom} {personne.prenom}"],
        ["N° Adhérent", adhesion.id_adherent.numero_adherent],
        ["Date de naissance", personne.date_naissance.strftime("%d/%m/%Y") if personne.date_naissance else "-"],
        ["Téléphone", personne.telephone or "-"],
        ["Email", personne.email or "-"],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, 13.5 * cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Contrat
    elements.append(Paragraph("CONTRAT", style_section))
    contrat = adhesion.id_contrat
    contrat_data = [
        ["N° Contrat", contrat.numero_contrat],
        ["Souscripteur", contrat.id_souscripteur.raison_sociale],
        ["Type", contrat.type_contrat],
        ["Date début", adhesion.date_debut.strftime("%d/%m/%Y") if adhesion.date_debut else "-"],
        ["Date fin", adhesion.date_fin.strftime("%d/%m/%Y") if adhesion.date_fin else "Illimité"],
        ["Statut", adhesion.statut],
    ]
    contrat_table = Table(contrat_data, colWidths=[4 * cm, 13.5 * cm])
    contrat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(contrat_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Ayants droit
    if ayants_droit:
        elements.append(Paragraph("AYANTS DROIT", style_section))
        ad_data = [["Nom", "Prénom", "Type de lien", "Date début"]]
        for ad in ayants_droit:
            ad_data.append([
                ad.id_personne.nom,
                ad.id_personne.prenom,
                ad.type_lien,
                ad.date_debut.strftime("%d/%m/%Y") if ad.date_debut else "-",
            ])
        ad_table = Table(ad_data, repeatRows=1, colWidths=[
            4 * cm, 4 * cm, 5 * cm, 4.5 * cm,
        ])
        ad_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(ad_table)
        elements.append(Spacer(1, 0.5 * cm))

    # Signatures
    elements.append(Spacer(1, 1 * cm))
    sig_data = [[
        "Signature de l'adhérent", "Cachet de l'organisme"
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




def personne_create(request):
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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer une personne."
        )
        return redirect("adherents")

    if request.method == "POST":
        form = PersonneForm(request.POST)

        if form.is_valid():
            try:
                Personne.objects.create(
                    numero_personne=_generer_numero_personne(),
                    nom=form.cleaned_data["nom"],
                    prenom=form.cleaned_data["prenom"],
                    date_naissance=form.cleaned_data["date_naissance"],
                    sexe=form.cleaned_data["sexe"] or None,
                    adresse=form.cleaned_data["adresse"] or None,
                    telephone=form.cleaned_data["telephone"] or None,
                    email=form.cleaned_data["email"] or None,
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                messages.success(
                    request,
                    "Personne créée avec succès."
                )

                return redirect("personne_create")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = PersonneForm()

    return render(
        request,
        "core/personne_form.html",
        {
            "form": form,
            "titre": "Nouvelle personne",
            "page": "adherents",
        }
    )

