def recours_pdf(request, id_recours):
    """Génère le PDF détaillé d'un recours."""
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

    if "RECOURS_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("recours")

    try:
        recours_obj = (
            Recours.objects
            .select_related("id_personne")
            .get(id_recours=id_recours)
        )
    except Recours.DoesNotExist:
        messages.error(request, "Recours introuvable.")
        return redirect("recours")

    # Récupérer la décision si elle existe
    decision = (
        DecisionRecours.objects
        .filter(id_recours=recours_obj)
        .order_by("-date_decision")
        .first()
    )

    documents_lies = (
        RecoursDocument.objects
        .select_related("id_document")
        .filter(id_recours=recours_obj)
        .order_by("-date_ajout")
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
        f'attachment; filename="Recours-{recours_obj.numero_recours}.pdf"'
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
        "<b>RECOURS</b><br/>"
        f"<font size=11>N° {recours_obj.numero_recours}</font>",
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

    # Infos recours
    elements.append(Paragraph("INFORMATIONS DU RECOURS", style_section))

    infos_data = [
        ["N° Recours", recours_obj.numero_recours],
        ["Type", recours_obj.type_recours],
        ["Date", recours_obj.date_recours.strftime("%d/%m/%Y") if recours_obj.date_recours else "-"],
        ["Statut", recours_obj.statut],
        ["Date de clôture",
         recours_obj.date_cloture.strftime("%d/%m/%Y") if recours_obj.date_cloture else "-"],
    ]
    infos_table = Table(infos_data, colWidths=[4.5 * cm, 13 * cm])
    infos_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(infos_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Personne
    elements.append(Paragraph("PERSONNE CONCERNÉE", style_section))
    personne = recours_obj.id_personne
    pers_data = [
        ["Nom et Prénom", f"{personne.nom} {personne.prenom}"],
        ["N° Personne", personne.numero_personne or "-"],
        ["Date de naissance",
         personne.date_naissance.strftime("%d/%m/%Y") if personne.date_naissance else "-"],
        ["Téléphone", personne.telephone or "-"],
    ]
    pers_table = Table(pers_data, colWidths=[4.5 * cm, 13 * cm])
    pers_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(pers_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Objet + Motif
    elements.append(Paragraph("OBJET DU RECOURS", style_section))

    objet_data = [
        ["Objet", recours_obj.objet or "-"],
        ["Motif", recours_obj.motif or "-"],
        ["Observation", recours_obj.observation or "-"],
    ]
    objet_table = Table(objet_data, colWidths=[4.5 * cm, 13 * cm])
    objet_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(objet_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Décision (si elle existe)
    if decision:
        elements.append(Paragraph("DÉCISION", style_section))

        dec_data = [
            ["Date décision",
             decision.date_decision.strftime("%d/%m/%Y") if decision.date_decision else "-"],
            ["Type de décision", decision.type_decision],
            ["Montant accordé",
             f"{decision.montant_accorde:.2f} DA" if decision.montant_accorde else "-"],
            ["Motif de la décision", decision.motif_decision or "-"],
            ["Observation", decision.observation or "-"],
        ]
        dec_table = Table(dec_data, colWidths=[4.5 * cm, 13 * cm])
        dec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(dec_table)
        elements.append(Spacer(1, 0.5 * cm))

    # Documents joints
    if documents_lies:
        elements.append(Paragraph("DOCUMENTS JOINTS", style_section))

        doc_data = [["Nom du fichier", "Type", "Date d'ajout"]]
        for d in documents_lies:
            doc_data.append([
                d.id_document.nom_fichier,
                d.type_document or "-",
                d.date_ajout.strftime("%d/%m/%Y") if d.date_ajout else "-",
            ])

        doc_table = Table(doc_data, repeatRows=1, colWidths=[
            8 * cm, 5 * cm, 4.5 * cm,
        ])
        doc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(doc_table)
        elements.append(Spacer(1, 0.5 * cm))

    # Signatures
    elements.append(Spacer(1, 1 * cm))
    sig_data = [[
        "Signature du demandeur", "Cachet de l'organisme"
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

