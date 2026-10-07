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

