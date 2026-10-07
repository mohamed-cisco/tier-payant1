def prise_en_charge_pdf(request, id_pec):
    """Génère le PDF d'une prise en charge."""
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
            "Vous n'avez pas l'autorisation de générer le PDF."
        )
        return redirect("prises_en_charge")

    try:
        pec = (
            PriseEnCharge.objects
            .select_related(
                "id_demande",
                "id_demande__id_personne_beneficiaire",
                "id_demande__id_contrat",
                "id_demande__id_prestataire",
            )
            .get(id_pec=id_pec)
        )
    except PriseEnCharge.DoesNotExist:
        messages.error(request, "Prise en charge introuvable.")
        return redirect("prises_en_charge")

    details = (
        PriseEnChargeDetail.objects
        .select_related("id_pec", "id_detail_demande", "id_acte")
        .filter(id_pec=pec)
        .order_by("id_detail_pec")
    )

    # Imports reportlab
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="PEC-{pec.numero_pec}.pdf"'
    )

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    # Charger le logo
    import os
    from django.conf import settings
    from reportlab.platypus import Image

    logo_path = os.path.join(
        settings.BASE_DIR,
        "core", "static", "core", "img", "logo-sagps.png"
    )

    elements = []
    styles = getSampleStyleSheet()

    # Style personnalisé
    style_titre = ParagraphStyle(
        "Titre",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#123b65"),
        alignment=1,
        spaceAfter=10,
    )
    style_section = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#123b65"),
        spaceAfter=8,
        spaceBefore=10,
    )
    style_normal = styles["Normal"]

       # =========================
    # EN-TÊTE COMBINÉ
    # =========================
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=5 * cm, height=2.2 * cm)
    else:
        logo = ""

    titre_header = Paragraph(
        "<b>PRISE EN CHARGE</b><br/>"
        f"<font size=11>N° {pec.numero_pec}</font>",
        ParagraphStyle(
            "HeaderTitle",
            parent=styles["Title"],
            fontSize=20,
            textColor=colors.HexColor("#123b65"),
            alignment=2,
            leading=26,
        )
    )

    header_table = Table(
        [[logo, titre_header]],
        colWidths=[7 * cm, 10.5 * cm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#123b65")),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.6 * cm))
    

    # =========================
    # INFOS GÉNÉRALES
    # =========================
    infos_data = [
        ["Date de PEC", pec.date_pec.strftime("%d/%m/%Y") if pec.date_pec else "-",
         "Date d'expiration", pec.date_expiration.strftime("%d/%m/%Y") if pec.date_expiration else "-"],
        ["Statut", pec.statut, "N° Demande", pec.id_demande.numero_demande],
    ]
    infos_table = Table(infos_data, colWidths=[3.5 * cm, 5 * cm, 4 * cm, 5 * cm])
    infos_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(infos_table)
    elements.append(Spacer(1, 0.5 * cm))

    # =========================
    # BÉNÉFICIAIRE
    # =========================
    elements.append(Paragraph("BÉNÉFICIAIRE", style_section))
    benef = pec.id_demande.id_personne_beneficiaire
    benef_data = [
        ["Nom et Prénom", f"{benef.nom} {benef.prenom}"],
        ["Date de naissance", benef.date_naissance.strftime("%d/%m/%Y") if benef.date_naissance else "-"],
        ["Téléphone", benef.telephone or "-"],
        ["Contrat", pec.id_demande.id_contrat.numero_contrat],
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

    # =========================
    # PRESTATAIRE
    # =========================
    elements.append(Paragraph("PRESTATAIRE", style_section))
    prest = pec.id_demande.id_prestataire
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

    # =========================
    # ACTES PRIS EN CHARGE
    # =========================
    elements.append(Paragraph("ACTES PRIS EN CHARGE", style_section))

    actes_data = [[
        "Code Acte", "Libellé", "Qté",
        "Montant demandé", "Taux", "Franchise", "Montant accordé"
    ]]

    for d in details:
        actes_data.append([
            d.id_acte.code_acte,
            d.id_acte.libelle[:40],
            f"{d.quantite:.2f}",
            f"{d.montant_demande:.2f}",
            f"{d.taux_applique:.2f} %" if d.taux_applique else "-",
            f"{d.franchise_appliquee:.2f}" if d.franchise_appliquee else "0.00",
            f"{d.montant_accorde:.2f}",
        ])

        actes_table = Table(actes_data, repeatRows=1, colWidths=[
        2.2 * cm,   # Code Acte
        4.8 * cm,   # Libellé
        1.3 * cm,   # Qté
        2.4 * cm,   # Montant demandé
        1.5 * cm,   # Taux
        1.8 * cm,   # Franchise
        3.0 * cm,   # Montant accordé
    ])
    actes_table.setStyle(TableStyle([
        # En-tête
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Alignements
        ("ALIGN", (0, 1), (0, -1), "LEFT"),     # Code
        ("ALIGN", (1, 1), (1, -1), "LEFT"),     # Libellé
        ("ALIGN", (2, 1), (2, -1), "CENTER"),   # Qté
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),   # Montants
        # Bordures
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(actes_table)
    elements.append(Spacer(1, 0.5 * cm))

    # =========================
    # TOTAUX
    # =========================
    totaux_data = [
        ["Montant demandé", f"{pec.montant_demande:.2f} DA"],
        ["Montant accordé", f"{pec.montant_accepte:.2f} DA"],
        ["Montant rejeté", f"{pec.montant_rejete:.2f} DA"],
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

    # =========================
    # SIGNATURES
    # =========================
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
