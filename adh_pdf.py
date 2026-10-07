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

