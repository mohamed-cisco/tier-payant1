# core/views/rapports.py
"""
Module de rapports professionnels.

Fonctions :
- rapports : page principale
- rapport_mensuel : vue du rapport mensuel
- rapport_mensuel_pdf : export PDF
- rapport_mensuel_excel : export Excel
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDay, TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import (
    Consommation,
    DemandeTp,
    Facture,
    Prestataire,
    PriseEnCharge,
    Reglement,
    RolePermission,
)


def _get_permissions(request):
    """Récupère les permissions de l'utilisateur connecté."""
    if not request.session.get("id_utilisateur"):
        return None

    id_utilisateur = request.session["id_utilisateur"]

    return set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )


def rapports(request):
    """Page principale des rapports."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions and "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de consulter les rapports.")
        return redirect("accueil")

    return render(
        request,
        "core/rapports.html",
        {
            "permissions": permissions,
            "page": "rapports",
        }
    )


def rapport_mensuel(request):
    """Rapport mensuel global."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions and "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")

    # Récupérer le mois et l'année depuis les paramètres GET
    aujourd_hui = timezone.now().date()

    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year

    # Bornes du mois
    date_debut = date(annee, mois, 1)
    if mois == 12:
        date_fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin = date(annee, mois + 1, 1) - timedelta(days=1)

    # ============================================================
    # STATISTIQUES GÉNÉRALES
    # ============================================================
    demandes = DemandeTp.objects.filter(
        date_demande__date__gte=date_debut,
        date_demande__date__lte=date_fin,
    )

    pec = PriseEnCharge.objects.filter(
        date_pec__date__gte=date_debut,
        date_pec__date__lte=date_fin,
    )

    consommations = Consommation.objects.filter(
        date_prestation__gte=date_debut,
        date_prestation__lte=date_fin,
    )

    factures = Facture.objects.filter(
        date_facture__gte=date_debut,
        date_facture__lte=date_fin,
    )

    reglements = Reglement.objects.filter(
        date_reglement__gte=date_debut,
        date_reglement__lte=date_fin,
    )

    # KPIs
    nb_demandes = demandes.count()
    nb_pec = pec.count()
    nb_consommations = consommations.count()
    nb_factures = factures.count()
    nb_reglements = reglements.count()

    # Montants
    montant_demandes = demandes.aggregate(total=Sum("montant_demande"))["total"] or Decimal("0.00")
    montant_pec_accepte = pec.aggregate(total=Sum("montant_accepte"))["total"] or Decimal("0.00")
    montant_pec_rejete = pec.aggregate(total=Sum("montant_rejete"))["total"] or Decimal("0.00")
    montant_consommations = consommations.aggregate(
        total=Sum("montant_prise_en_charge")
    )["total"] or Decimal("0.00")
    montant_factures_valide = factures.aggregate(
        total=Sum("montant_valide")
    )["total"] or Decimal("0.00")
    montant_reglements = reglements.aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0.00")

    # Taux d'acceptation
    demandes_acceptees = demandes.filter(statut="ACCEPTEE").count()
    if nb_demandes > 0:
        taux_acceptation = round((demandes_acceptees / nb_demandes) * 100, 1)
    else:
        taux_acceptation = 0

    # ============================================================
    # TOP 10 PRESTATAIRES
    # ============================================================
    top_prestataires = (
        Facture.objects
        .filter(
            date_facture__gte=date_debut,
            date_facture__lte=date_fin,
        )
        .values("id_prestataire__raison_sociale")
        .annotate(
            total=Sum("montant_valide"),
            nb_factures=Count("id_facture"),
        )
        .order_by("-total")[:10]
    )

    # ============================================================
    # TOP 10 ACTES
    # ============================================================
    top_actes = (
        Consommation.objects
        .filter(
            date_prestation__gte=date_debut,
            date_prestation__lte=date_fin,
        )
        .values("id_acte__code_acte", "id_acte__libelle")
        .annotate(
            total=Sum("montant_prise_en_charge"),
            nb=Count("id_consommation"),
        )
        .order_by("-nb")[:10]
    )

    # ============================================================
    # ÉVOLUTION JOURNALIÈRE
    # ============================================================
    evolution_demandes = (
        demandes
        .annotate(jour=TruncDay("date_demande"))
        .values("jour")
        .annotate(total=Count("id_demande"))
        .order_by("jour")
    )

    graphique_labels = [item["jour"].strftime("%d/%m") for item in evolution_demandes]
    graphique_demandes = [item["total"] for item in evolution_demandes]

    # ============================================================
    # COMPARAISON MOIS PRÉCÉDENT
    # ============================================================
    if mois == 1:
        mois_precedent = 12
        annee_precedente = annee - 1
    else:
        mois_precedent = mois - 1
        annee_precedente = annee

    date_debut_prec = date(annee_precedente, mois_precedent, 1)
    if mois_precedent == 12:
        date_fin_prec = date(annee_precedente + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin_prec = date(annee_precedente, mois_precedent + 1, 1) - timedelta(days=1)

    demandes_prec = DemandeTp.objects.filter(
        date_demande__date__gte=date_debut_prec,
        date_demande__date__lte=date_fin_prec,
    ).count()

    if demandes_prec > 0:
        evolution_demandes_pct = round(((nb_demandes - demandes_prec) / demandes_prec) * 100, 1)
    else:
        evolution_demandes_pct = 0

    # Noms des mois
    noms_mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    return render(
        request,
        "core/rapport_mensuel.html",
        {
            "permissions": permissions,
            "page": "rapports",

            # Paramètres
            "mois": mois,
            "annee": annee,
            "nom_mois": noms_mois[mois - 1],
            "date_debut": date_debut,
            "date_fin": date_fin,

            # KPIs
            "nb_demandes": nb_demandes,
            "nb_pec": nb_pec,
            "nb_consommations": nb_consommations,
            "nb_factures": nb_factures,
            "nb_reglements": nb_reglements,

            # Montants
            "montant_demandes": montant_demandes,
            "montant_pec_accepte": montant_pec_accepte,
            "montant_pec_rejete": montant_pec_rejete,
            "montant_consommations": montant_consommations,
            "montant_factures_valide": montant_factures_valide,
            "montant_reglements": montant_reglements,

            # Taux
            "taux_acceptation": taux_acceptation,
            "evolution_demandes_pct": evolution_demandes_pct,
            "demandes_prec": demandes_prec,

            # Top
            "top_prestataires": top_prestataires,
            "top_actes": top_actes,

            # Graphique
            "graphique_labels": graphique_labels,
            "graphique_demandes": graphique_demandes,
        }
    )


def rapport_mensuel_pdf(request):
    """Export PDF du rapport mensuel."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions and "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")

    # Récupérer les paramètres
    aujourd_hui = timezone.now().date()

    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year

    # Bornes du mois
    date_debut = date(annee, mois, 1)
    if mois == 12:
        date_fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin = date(annee, mois + 1, 1) - timedelta(days=1)

    # Stats (mêmes calculs que rapport_mensuel)
    demandes = DemandeTp.objects.filter(
        date_demande__date__gte=date_debut,
        date_demande__date__lte=date_fin,
    )
    pec = PriseEnCharge.objects.filter(
        date_pec__date__gte=date_debut,
        date_pec__date__lte=date_fin,
    )
    consommations = Consommation.objects.filter(
        date_prestation__gte=date_debut,
        date_prestation__lte=date_fin,
    )
    factures = Facture.objects.filter(
        date_facture__gte=date_debut,
        date_facture__lte=date_fin,
    )
    reglements = Reglement.objects.filter(
        date_reglement__gte=date_debut,
        date_reglement__lte=date_fin,
    )

    nb_demandes = demandes.count()
    nb_pec = pec.count()
    nb_consommations = consommations.count()
    nb_factures = factures.count()
    nb_reglements = reglements.count()

    montant_demandes = demandes.aggregate(total=Sum("montant_demande"))["total"] or Decimal("0.00")
    montant_pec_accepte = pec.aggregate(total=Sum("montant_accepte"))["total"] or Decimal("0.00")
    montant_pec_rejete = pec.aggregate(total=Sum("montant_rejete"))["total"] or Decimal("0.00")
    montant_consommations = consommations.aggregate(
        total=Sum("montant_prise_en_charge")
    )["total"] or Decimal("0.00")
    montant_factures_valide = factures.aggregate(
        total=Sum("montant_valide")
    )["total"] or Decimal("0.00")
    montant_reglements = reglements.aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0.00")

    demandes_acceptees = demandes.filter(statut="ACCEPTEE").count()
    taux_acceptation = round((demandes_acceptees / nb_demandes) * 100, 1) if nb_demandes > 0 else 0

    top_prestataires = (
        Facture.objects
        .filter(date_facture__gte=date_debut, date_facture__lte=date_fin)
        .values("id_prestataire__raison_sociale")
        .annotate(total=Sum("montant_valide"), nb_factures=Count("id_facture"))
        .order_by("-total")[:10]
    )

    top_actes = (
        Consommation.objects
        .filter(date_prestation__gte=date_debut, date_prestation__lte=date_fin)
        .values("id_acte__code_acte", "id_acte__libelle")
        .annotate(total=Sum("montant_prise_en_charge"), nb=Count("id_consommation"))
        .order_by("-nb")[:10]
    )

    # Noms des mois
    noms_mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    # Génération PDF
    from django.http import HttpResponse
    from django.conf import settings
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="rapport_{mois:02d}_{annee}.pdf"'
    )

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    elements = []
    styles = getSampleStyleSheet()

    # Titre
    style_titre = ParagraphStyle(
        "Titre", parent=styles["Title"], fontSize=18,
        textColor=colors.HexColor("#123b65"), alignment=1,
    )
    elements.append(Paragraph(
        f"RAPPORT MENSUEL — {noms_mois[mois-1]} {annee}", style_titre
    ))
    elements.append(Spacer(1, 0.5*cm))

    # Période
    style_normal = ParagraphStyle("Normal", parent=styles["Normal"], fontSize=11)
    elements.append(Paragraph(
        f"Période : du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        style_normal
    ))
    elements.append(Spacer(1, 0.8*cm))

    # KPIs
    elements.append(Paragraph("<b>STATISTIQUES GÉNÉRALES</b>", styles["Heading2"]))
    kpi_data = [
        ["Indicateur", "Valeur"],
        ["Demandes TP", str(nb_demandes)],
        ["PEC", str(nb_pec)],
        ["Consommations", str(nb_consommations)],
        ["Factures", str(nb_factures)],
        ["Règlements", str(nb_reglements)],
        ["Taux d'acceptation", f"{taux_acceptation}%"],
    ]
    kpi_table = Table(kpi_data, colWidths=[8*cm, 8*cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.8*cm))

    # Situation financière
    elements.append(Paragraph("<b>SITUATION FINANCIÈRE</b>", styles["Heading2"]))
    fin_data = [
        ["Indicateur", "Montant"],
        ["Montant total demandé", f"{montant_demandes:,.2f} DA"],
        ["Montant accordé (PEC)", f"{montant_pec_accepte:,.2f} DA"],
        ["Montant rejeté (PEC)", f"{montant_pec_rejete:,.2f} DA"],
        ["Montant consommations", f"{montant_consommations:,.2f} DA"],
        ["Montant facturé validé", f"{montant_factures_valide:,.2f} DA"],
        ["Montant réglé", f"{montant_reglements:,.2f} DA"],
    ]
    fin_table = Table(fin_data, colWidths=[8*cm, 8*cm])
    fin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 0.8*cm))

    # Top prestataires
    if top_prestataires:
        elements.append(Paragraph("<b>TOP 10 PRESTATAIRES</b>", styles["Heading2"]))
        prest_data = [["#", "Prestataire", "Nb factures", "Montant validé"]]
        for i, p in enumerate(top_prestataires, 1):
            prest_data.append([
                str(i),
                p["id_prestataire__raison_sociale"][:40],
                str(p["nb_factures"]),
                f"{p['total']:,.2f} DA",
            ])
        prest_table = Table(prest_data, colWidths=[1*cm, 8*cm, 3*cm, 4*cm])
        prest_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(prest_table)

    document.build(elements)
    return response


def rapport_mensuel_excel(request):
    """Export Excel du rapport mensuel."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions and "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")

    # Récupérer les paramètres
    aujourd_hui = timezone.now().date()

    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year

    date_debut = date(annee, mois, 1)
    if mois == 12:
        date_fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin = date(annee, mois + 1, 1) - timedelta(days=1)

    # Stats
    demandes = DemandeTp.objects.filter(
        date_demande__date__gte=date_debut,
        date_demande__date__lte=date_fin,
    )
    pec = PriseEnCharge.objects.filter(
        date_pec__date__gte=date_debut,
        date_pec__date__lte=date_fin,
    )
    consommations = Consommation.objects.filter(
        date_prestation__gte=date_debut,
        date_prestation__lte=date_fin,
    )
    factures = Facture.objects.filter(
        date_facture__gte=date_debut,
        date_facture__lte=date_fin,
    )
    reglements = Reglement.objects.filter(
        date_reglement__gte=date_debut,
        date_reglement__lte=date_fin,
    )

    nb_demandes = demandes.count()
    nb_pec = pec.count()
    nb_consommations = consommations.count()
    nb_factures = factures.count()
    nb_reglements = reglements.count()

    montant_demandes = demandes.aggregate(total=Sum("montant_demande"))["total"] or Decimal("0.00")
    montant_pec_accepte = pec.aggregate(total=Sum("montant_accepte"))["total"] or Decimal("0.00")
    montant_pec_rejete = pec.aggregate(total=Sum("montant_rejete"))["total"] or Decimal("0.00")
    montant_consommations = consommations.aggregate(
        total=Sum("montant_prise_en_charge")
    )["total"] or Decimal("0.00")
    montant_factures_valide = factures.aggregate(
        total=Sum("montant_valide")
    )["total"] or Decimal("0.00")
    montant_reglements = reglements.aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0.00")

    demandes_acceptees = demandes.filter(statut="ACCEPTEE").count()
    taux_acceptation = round((demandes_acceptees / nb_demandes) * 100, 1) if nb_demandes > 0 else 0

    top_prestataires = (
        Facture.objects
        .filter(date_facture__gte=date_debut, date_facture__lte=date_fin)
        .values("id_prestataire__raison_sociale")
        .annotate(total=Sum("montant_valide"), nb_factures=Count("id_facture"))
        .order_by("-total")[:10]
    )

    # Génération Excel
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from django.http import HttpResponse

    noms_mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    workbook = openpyxl.Workbook()
    feuille = workbook.active
    feuille.title = "Rapport mensuel"

    # Styles
    font_titre = Font(bold=True, size=16, color="123B65")
    font_entete = Font(bold=True, color="FFFFFF", size=11)
    font_total = Font(bold=True, size=11, color="123B65")
    fill_entete = PatternFill(start_color="123B65", end_color="123B65", fill_type="solid")
    fill_total = PatternFill(start_color="EAF2FB", end_color="EAF2FB", fill_type="solid")

    # Titre
    feuille["A1"] = f"RAPPORT MENSUEL — {noms_mois[mois-1]} {annee}"
    feuille["A1"].font = font_titre
    feuille.merge_cells("A1:B1")

    feuille["A2"] = f"Du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
    feuille.merge_cells("A2:B2")

    # KPIs
    feuille["A4"] = "STATISTIQUES GÉNÉRALES"
    feuille["A4"].font = font_entete
    feuille["A4"].fill = fill_entete
    feuille["B4"].fill = fill_entete
    feuille.merge_cells("A4:B4")

    kpis = [
        ("Demandes TP", nb_demandes),
        ("PEC", nb_pec),
        ("Consommations", nb_consommations),
        ("Factures", nb_factures),
        ("Règlements", nb_reglements),
        ("Taux d'acceptation", f"{taux_acceptation}%"),
    ]

    ligne = 5
    for label, valeur in kpis:
        feuille.cell(row=ligne, column=1, value=label)
        feuille.cell(row=ligne, column=2, value=valeur)
        ligne += 1

    # Situation financière
    ligne += 1
    feuille.cell(row=ligne, column=1, value="SITUATION FINANCIÈRE")
    feuille.cell(row=ligne, column=1).font = font_entete
    feuille.cell(row=ligne, column=1).fill = fill_entete
    feuille.cell(row=ligne, column=2).fill = fill_entete
    ligne += 1

    finances = [
        ("Montant demandé", montant_demandes),
        ("Montant accordé (PEC)", montant_pec_accepte),
        ("Montant rejeté (PEC)", montant_pec_rejete),
        ("Montant consommations", montant_consommations),
        ("Montant facturé validé", montant_factures_valide),
        ("Montant réglé", montant_reglements),
    ]

    for label, montant in finances:
        feuille.cell(row=ligne, column=1, value=label)
        feuille.cell(row=ligne, column=2, value=float(montant))
        feuille.cell(row=ligne, column=2).number_format = '#,##0.00" DA"'
        ligne += 1

    # Top prestataires
    ligne += 1
    feuille.cell(row=ligne, column=1, value="TOP 10 PRESTATAIRES")
    feuille.cell(row=ligne, column=1).font = font_entete
    feuille.cell(row=ligne, column=1).fill = fill_entete
    for col in range(2, 5):
        feuille.cell(row=ligne, column=col).fill = fill_entete
    ligne += 1

    # En-têtes
    headers = ["#", "Prestataire", "Nb factures", "Montant validé"]
    for col, h in enumerate(headers, 1):
        feuille.cell(row=ligne, column=col, value=h)
        feuille.cell(row=ligne, column=col).font = font_total
    ligne += 1

    for i, p in enumerate(top_prestataires, 1):
        feuille.cell(row=ligne, column=1, value=i)
        feuille.cell(row=ligne, column=2, value=p["id_prestataire__raison_sociale"])
        feuille.cell(row=ligne, column=3, value=p["nb_factures"])
        feuille.cell(row=ligne, column=4, value=float(p["total"]))
        feuille.cell(row=ligne, column=4).number_format = '#,##0.00" DA"'
        ligne += 1

    # Ajuster largeurs
    feuille.column_dimensions["A"].width = 30
    feuille.column_dimensions["B"].width = 30
    feuille.column_dimensions["C"].width = 15
    feuille.column_dimensions["D"].width = 20

    # Réponse
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="rapport_{mois:02d}_{annee}.xlsx"'
    )
    workbook.save(response)
    return response



def rapport_prestataire(request):
    """Rapport d'activité par prestataire."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions and "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")

    # Récupérer les paramètres
    aujourd_hui = timezone.now().date()

    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year

    # Bornes du mois
    date_debut = date(annee, mois, 1)
    if mois == 12:
        date_fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin = date(annee, mois + 1, 1) - timedelta(days=1)

    # Prestataire sélectionné
    id_prestataire = request.GET.get("id_prestataire", "").strip()

    # Récupérer tous les prestataires pour le filtre
    prestataires = Prestataire.objects.filter(statut="ACTIF").order_by("raison_sociale")

    rapport_data = None
    prestataire_selectionne = None

    if id_prestataire:
        try:
            prestataire_selectionne = Prestataire.objects.get(
                id_prestataire=id_prestataire
            )
        except Prestataire.DoesNotExist:
            messages.error(request, "Prestataire introuvable.")

        if prestataire_selectionne:
            # Factures du prestataire
            factures = Facture.objects.filter(
                id_prestataire=prestataire_selectionne,
                date_facture__gte=date_debut,
                date_facture__lte=date_fin,
            )

            # Règlements liés
            reglements = Reglement.objects.filter(
                id_facture__id_prestataire=prestataire_selectionne,
                date_reglement__gte=date_debut,
                date_reglement__lte=date_fin,
            )

            # Demandes TP liées
            demandes = DemandeTp.objects.filter(
                id_prestataire=prestataire_selectionne,
                date_demande__date__gte=date_debut,
                date_demande__date__lte=date_fin,
            )

            # PEC liées
            pec = PriseEnCharge.objects.filter(
                id_demande__id_prestataire=prestataire_selectionne,
                date_pec__date__gte=date_debut,
                date_pec__date__lte=date_fin,
            )

            # Consommations liées
            consommations = Consommation.objects.filter(
                id_prestataire=prestataire_selectionne,
                date_prestation__gte=date_debut,
                date_prestation__lte=date_fin,
            )

            # Calculs
            nb_demandes = demandes.count()
            nb_pec = pec.count()
            nb_consommations = consommations.count()
            nb_factures = factures.count()
            nb_reglements = reglements.count()

            montant_demandes = demandes.aggregate(
                total=Sum("montant_demande")
            )["total"] or Decimal("0.00")

            montant_pec_accepte = pec.aggregate(
                total=Sum("montant_accepte")
            )["total"] or Decimal("0.00")

            montant_consommations = consommations.aggregate(
                total=Sum("montant_prise_en_charge")
            )["total"] or Decimal("0.00")

            montant_factures = factures.aggregate(
                total=Sum("montant_valide")
            )["total"] or Decimal("0.00")

            montant_reglements = reglements.aggregate(
                total=Sum("montant")
            )["total"] or Decimal("0.00")

            # Top actes du prestataire
            top_actes = (
                Consommation.objects
                .filter(
                    id_prestataire=prestataire_selectionne,
                    date_prestation__gte=date_debut,
                    date_prestation__lte=date_fin,
                )
                .values("id_acte__code_acte", "id_acte__libelle")
                .annotate(
                    total=Sum("montant_prise_en_charge"),
                    nb=Count("id_consommation"),
                )
                .order_by("-nb")[:10]
            )

            rapport_data = {
                "nb_demandes": nb_demandes,
                "nb_pec": nb_pec,
                "nb_consommations": nb_consommations,
                "nb_factures": nb_factures,
                "nb_reglements": nb_reglements,
                "montant_demandes": montant_demandes,
                "montant_pec_accepte": montant_pec_accepte,
                "montant_consommations": montant_consommations,
                "montant_factures": montant_factures,
                "montant_reglements": montant_reglements,
                "top_actes": top_actes,
            }

    # Noms des mois
    noms_mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    return render(
        request,
        "core/rapport_prestataire.html",
        {
            "permissions": permissions,
            "page": "rapports",
            "prestataires": prestataires,
            "prestataire_selectionne": prestataire_selectionne,
            "id_prestataire": id_prestataire,
            "rapport_data": rapport_data,
            "mois": mois,
            "annee": annee,
            "nom_mois": noms_mois[mois - 1],
            "date_debut": date_debut,
            "date_fin": date_fin,
        }
    )


def rapport_prestataire(request):
    """Rapport d'activité par prestataire."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions and "DEMANDE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")

    # Récupérer les paramètres
    aujourd_hui = timezone.now().date()

    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year

    # Bornes du mois
    date_debut = date(annee, mois, 1)
    if mois == 12:
        date_fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin = date(annee, mois + 1, 1) - timedelta(days=1)

    # Prestataire sélectionné
    id_prestataire = request.GET.get("id_prestataire", "").strip()

    # Récupérer tous les prestataires pour le filtre
    prestataires = Prestataire.objects.filter(statut="ACTIF").order_by("raison_sociale")

    rapport_data = None
    prestataire_selectionne = None

    if id_prestataire:
        try:
            prestataire_selectionne = Prestataire.objects.get(
                id_prestataire=id_prestataire
            )
        except Prestataire.DoesNotExist:
            messages.error(request, "Prestataire introuvable.")

        if prestataire_selectionne:
            # Factures du prestataire
            factures = Facture.objects.filter(
                id_prestataire=prestataire_selectionne,
                date_facture__gte=date_debut,
                date_facture__lte=date_fin,
            )

            # Règlements liés
            reglements = Reglement.objects.filter(
                id_facture__id_prestataire=prestataire_selectionne,
                date_reglement__gte=date_debut,
                date_reglement__lte=date_fin,
            )

            # Demandes TP liées
            demandes = DemandeTp.objects.filter(
                id_prestataire=prestataire_selectionne,
                date_demande__date__gte=date_debut,
                date_demande__date__lte=date_fin,
            )

            # PEC liées
            pec = PriseEnCharge.objects.filter(
                id_demande__id_prestataire=prestataire_selectionne,
                date_pec__date__gte=date_debut,
                date_pec__date__lte=date_fin,
            )

            # Consommations liées
            consommations = Consommation.objects.filter(
                id_prestataire=prestataire_selectionne,
                date_prestation__gte=date_debut,
                date_prestation__lte=date_fin,
            )

            # Calculs
            nb_demandes = demandes.count()
            nb_pec = pec.count()
            nb_consommations = consommations.count()
            nb_factures = factures.count()
            nb_reglements = reglements.count()

            montant_demandes = demandes.aggregate(
                total=Sum("montant_demande")
            )["total"] or Decimal("0.00")

            montant_pec_accepte = pec.aggregate(
                total=Sum("montant_accepte")
            )["total"] or Decimal("0.00")

            montant_consommations = consommations.aggregate(
                total=Sum("montant_prise_en_charge")
            )["total"] or Decimal("0.00")

            montant_factures = factures.aggregate(
                total=Sum("montant_valide")
            )["total"] or Decimal("0.00")

            montant_reglements = reglements.aggregate(
                total=Sum("montant")
            )["total"] or Decimal("0.00")

            # Top actes du prestataire
            top_actes = (
                Consommation.objects
                .filter(
                    id_prestataire=prestataire_selectionne,
                    date_prestation__gte=date_debut,
                    date_prestation__lte=date_fin,
                )
                .values("id_acte__code_acte", "id_acte__libelle")
                .annotate(
                    total=Sum("montant_prise_en_charge"),
                    nb=Count("id_consommation"),
                )
                .order_by("-nb")[:10]
            )

            rapport_data = {
                "nb_demandes": nb_demandes,
                "nb_pec": nb_pec,
                "nb_consommations": nb_consommations,
                "nb_factures": nb_factures,
                "nb_reglements": nb_reglements,
                "montant_demandes": montant_demandes,
                "montant_pec_accepte": montant_pec_accepte,
                "montant_consommations": montant_consommations,
                "montant_factures": montant_factures,
                "montant_reglements": montant_reglements,
                "top_actes": top_actes,
            }

    # Noms des mois
    noms_mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    return render(
        request,
        "core/rapport_prestataire.html",
        {
            "permissions": permissions,
            "page": "rapports",
            "prestataires": prestataires,
            "prestataire_selectionne": prestataire_selectionne,
            "id_prestataire": id_prestataire,
            "rapport_data": rapport_data,
            "mois": mois,
            "annee": annee,
            "nom_mois": noms_mois[mois - 1],
            "date_debut": date_debut,
            "date_fin": date_fin,
        }
    )


def rapport_financier(request):
    """Rapport financier global."""
    permissions = _get_permissions(request)
    if permissions is None:
        return redirect("connexion")

    if "FACTURE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")

    # Récupérer les paramètres
    aujourd_hui = timezone.now().date()

    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year

    # Bornes du mois
    date_debut = date(annee, mois, 1)
    if mois == 12:
        date_fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        date_fin = date(annee, mois + 1, 1) - timedelta(days=1)

    # ============================================================
    # FACTURES
    # ============================================================
    factures = Facture.objects.filter(
        date_facture__gte=date_debut,
        date_facture__lte=date_fin,
    )

    nb_factures = factures.count()
    montant_facture = factures.aggregate(total=Sum("montant_total"))["total"] or Decimal("0.00")
    montant_valide = factures.aggregate(total=Sum("montant_valide"))["total"] or Decimal("0.00")
    montant_rejete = factures.aggregate(total=Sum("montant_rejete"))["total"] or Decimal("0.00")

    # ============================================================
    # RÈGLEMENTS
    # ============================================================
    reglements = Reglement.objects.filter(
        date_reglement__gte=date_debut,
        date_reglement__lte=date_fin,
        statut="VALIDEE",
    )

    nb_reglements = reglements.count()
    montant_paye = reglements.aggregate(total=Sum("montant"))["total"] or Decimal("0.00")

    # ============================================================
    # RESTE À PAYER
    # ============================================================
    reste_a_payer = montant_valide - montant_paye

    # ============================================================
    # FACTURES NON PAYÉES
    # ============================================================
    factures_non_payees = factures.filter(
        statut__in=["VALIDEE", "EN_ATTENTE"]
    ).order_by("-date_facture")

    # ============================================================
    # TOP DÉBITEURS (prestataires avec reste à payer)
    # ============================================================
    top_debiteurs = []
    prestataires = Prestataire.objects.filter(statut="ACTIF")

    for prest in prestataires:
        factures_prest = Facture.objects.filter(
            id_prestataire=prest,
            statut__in=["VALIDEE", "EN_ATTENTE"],
        )
        montant_du = factures_prest.aggregate(total=Sum("montant_valide"))["total"] or Decimal("0.00")

        if montant_du > 0:
            # Règlements liés
            reglements_prest = Reglement.objects.filter(
                id_facture__id_prestataire=prest,
                statut="VALIDEE",
            )
            montant_regle = reglements_prest.aggregate(total=Sum("montant"))["total"] or Decimal("0.00")

            reste = montant_du - montant_regle

            if reste > 0:
                top_debiteurs.append({
                    "prestataire": prest,
                    "montant_du": montant_du,
                    "montant_regle": montant_regle,
                    "reste": reste,
                })

    # Trier par reste décroissant
    top_debiteurs.sort(key=lambda x: x["reste"], reverse=True)
    top_debiteurs = top_debiteurs[:10]

    # ============================================================
    # ÉVOLUTION JOURNALIÈRE
    # ============================================================
    evolution_factures = (
        factures
        .annotate(jour=TruncDay("date_facture"))
        .values("jour")
        .annotate(total=Sum("montant_valide"))
        .order_by("jour")
    )

    graphique_labels = [item["jour"].strftime("%d/%m") for item in evolution_factures]
    graphique_montants = [float(item["total"] or 0) for item in evolution_factures]

    # Noms des mois
    noms_mois = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    return render(
        request,
        "core/rapport_financier.html",
        {
            "permissions": permissions,
            "page": "rapports",

            # Paramètres
            "mois": mois,
            "annee": annee,
            "nom_mois": noms_mois[mois - 1],
            "date_debut": date_debut,
            "date_fin": date_fin,

            # Factures
            "nb_factures": nb_factures,
            "montant_facture": montant_facture,
            "montant_valide": montant_valide,
            "montant_rejete": montant_rejete,

            # Règlements
            "nb_reglements": nb_reglements,
            "montant_paye": montant_paye,

            # Reste
            "reste_a_payer": reste_a_payer,
            "factures_non_payees": factures_non_payees,
            "top_debiteurs": top_debiteurs,

            # Graphique
            "graphique_labels": graphique_labels,
            "graphique_montants": graphique_montants,
        }
    )