def contrat_pdf(request, id_contrat):
    """Génère le PDF d'un contrat."""
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

    if "CONTRAT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("contrats")

    try:
        contrat = (
            Contrat.objects
            .select_related("id_souscripteur")
            .get(id_contrat=id_contrat)
        )
    except Contrat.DoesNotExist:
        messages.error(request, "Contrat introuvable.")
        return redirect("contrats")

    garanties = (
        ContratGarantie.objects
        .select_related("id_garantie")
        .filter(id_contrat=contrat)
    )

    adhesions = (
        Adhesion.objects
        .select_related("id_adherent", "id_adherent__id_personne")
        .filter(id_contrat=contrat)
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
        f'attachment; filename="Contrat-{contrat.numero_contrat}.pdf"'
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
        "<b>CONTRAT DE TIERS PAYANT</b><br/>"
        f"<font size=11>N° {contrat.numero_contrat}</font>",
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

    # Infos générales
    elements.append(Paragraph("INFORMATIONS GÉNÉRALES", style_section))
    info_data = [
        ["N° Contrat", contrat.numero_contrat],
        ["Type de contrat", contrat.type_contrat],
        ["Statut", contrat.statut],
        ["Date de début", contrat.date_debut.strftime("%d/%m/%Y") if contrat.date_debut else "-"],
        ["Date de fin", contrat.date_fin.strftime("%d/%m/%Y") if contrat.date_fin else "Illimité"],
        ["Date de signature", contrat.date_signature.strftime("%d/%m/%Y") if contrat.date_signature else "-"],
        ["Objet", contrat.objet or "-"],
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

    # Souscripteur
    elements.append(Paragraph("SOUSCRIPTEUR", style_section))
    sous = contrat.id_souscripteur
    sous_data = [
        ["Raison sociale", sous.raison_sociale],
        ["NIF", sous.nif or "-"],
        ["Registre commercial", sous.registre_commerce or "-"],
        ["Adresse", sous.adresse or "-"],
        ["Téléphone", sous.telephone or "-"],
        ["Email", sous.email or "-"],
    ]
    sous_table = Table(sous_data, colWidths=[4 * cm, 13.5 * cm])
    sous_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(sous_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Garanties
    if garanties:
        elements.append(Paragraph("GARANTIES", style_section))
        g_data = [["Code", "Libellé", "Date début", "Date fin", "Statut"]]
        for cg in garanties:
            g_data.append([
                cg.id_garantie.code_garantie,
                cg.id_garantie.libelle,
                cg.date_debut.strftime("%d/%m/%Y") if cg.date_debut else "-",
                cg.date_fin.strftime("%d/%m/%Y") if cg.date_fin else "-",
                cg.statut,
            ])
        g_table = Table(g_data, repeatRows=1, colWidths=[
            2.5 * cm, 6 * cm, 3 * cm, 3 * cm, 3 * cm,
        ])
        g_table.setStyle(TableStyle([
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
        elements.append(g_table)
        elements.append(Spacer(1, 0.5 * cm))

    # Adhésions
    if adhesions:
        elements.append(Paragraph("ADHÉSIONS", style_section))
        a_data = [["N° Adhésion", "Adhérent", "Date début", "Date fin", "Statut"]]
        for a in adhesions:
            a_data.append([
                a.numero_adhesion,
                f"{a.id_adherent.id_personne.nom} {a.id_adherent.id_personne.prenom}",
                a.date_debut.strftime("%d/%m/%Y") if a.date_debut else "-",
                a.date_fin.strftime("%d/%m/%Y") if a.date_fin else "-",
                a.statut,
            ])
        a_table = Table(a_data, repeatRows=1, colWidths=[
            3.5 * cm, 6 * cm, 2.5 * cm, 2.5 * cm, 3 * cm,
        ])
        a_table.setStyle(TableStyle([
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
        elements.append(a_table)
        elements.append(Spacer(1, 0.5 * cm))

    # Signatures
    elements.append(Spacer(1, 1 * cm))
    sig_data = [[
        "Signature du souscripteur", "Cachet de l'organisme"
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

