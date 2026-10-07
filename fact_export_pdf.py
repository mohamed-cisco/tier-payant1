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

