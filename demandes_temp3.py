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
  
