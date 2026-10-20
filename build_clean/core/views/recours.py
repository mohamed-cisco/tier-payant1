# core/views/recours.py
"""
Vues de gestion des recours.

Fonctions :
- recours : liste
- recours_detail : détail
- recours_create : créer
- recours_document_create : pièce jointe
- recours_traiter : traiter
- recours_pdf : PDF
- _generer_numero_recours : helper
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import (
    RecoursForm,
    DecisionRecoursForm,
)
from core.models import (
    DecisionRecours,
    Document,
    Recours,
    RecoursDocument,
    RolePermission,
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


def _generer_numero_recours():
    annee = timezone.now().year
    prefixe = f"REC-{annee}-"

    numeros = (
        Recours.objects
        .filter(numero_recours__startswith=prefixe)
        .values_list("numero_recours", flat=True)
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
    numero_recours = f"{prefixe}{prochain:04d}"

    while Recours.objects.filter(
        numero_recours=numero_recours
    ).exists():
        prochain += 1
        numero_recours = f"{prefixe}{prochain:04d}"

    return numero_recours




def recours(request):
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

    if "RECOURS_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les recours."
        )
        return redirect("accueil")

    recours_list = (
        Recours.objects
        .select_related("id_personne")
        .all()
        .order_by("-id_recours")
    )

    return render(
        request,
        "core/recours.html",
        {
            "recours": recours_list,
            "permissions": permissions,
            "page": "recours",
        }
    )




def recours_detail(request, id_recours):
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

    if "RECOURS_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les recours."
        )
        return redirect("recours")

    try:
        recours_obj = (
            Recours.objects
            .select_related("id_personne")
            .get(id_recours=id_recours)
        )
    except Recours.DoesNotExist:
        messages.error(
            request,
            "Recours introuvable."
        )
        return redirect("recours")

    documents_lies = (
        RecoursDocument.objects
        .select_related(
            "id_document",
            "id_document__id_utilisateur",
        )
        .filter(id_recours=recours_obj)
        .order_by("-date_ajout")
    )

    return render(
        request,
        "core/recours_detail.html",
        {
            "recours": recours_obj,
            "documents_lies": documents_lies,
            "permissions": permissions,
            "page": "recours",
        }
    )




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




def recours_create(request):
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

    if "RECOURS_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un recours."
        )
        return redirect("recours")

    if request.method == "POST":
        form = RecoursForm(request.POST)

        if form.is_valid():
            recours_obj = form.save(commit=False)

            recours_obj.numero_recours = _generer_numero_recours()

            recours_obj.statut = "EN_ATTENTE"

            recours_obj.utilisateur_creation = (
                request.session.get("nom_utilisateur")
            )

            recours_obj.save()

            messages.success(
                request,
                "Le recours a été créé avec succès."
            )

            return redirect("recours")

    else:
        form = RecoursForm()

    return render(
        request,
        "core/recours_form.html",
        {
            "form": form,
            "permissions": permissions,
            "page": "recours",
        }
    )



def recours_document_create(request, id_recours):
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

    if "DOCUMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter une pièce jointe."
        )
        return redirect(
            "recours_detail",
            id_recours=id_recours
        )

    try:
        recours_obj = Recours.objects.get(
            id_recours=id_recours
        )
    except Recours.DoesNotExist:
        messages.error(
            request,
            "Recours introuvable."
        )
        return redirect("recours")

    if request.method == "POST":

        form = DocumentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            try:
                with transaction.atomic():

                    fichier = form.cleaned_data["fichier"]

                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    type_document = (
                        form.cleaned_data["type_document"]
                        or getattr(
                            fichier,
                            "content_type",
                            None
                        )
                        or "INCONNU"
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=type_document,
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    RecoursDocument.objects.create(
                        id_recours=recours_obj,
                        id_document=document,
                        type_document=type_document,
                        date_ajout=timezone.now(),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="DEPOT_DOCUMENT",
                        module="DOCUMENT",
                        table_cible="document",
                        id_enregistrement=document.id_document,
                        nouvelle_valeur=(
                            f"Fichier : {document.nom_fichier}, "
                            f"Type : {document.type_document}, "
                            f"Recours : {recours_obj.numero_recours}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="RATTACHEMENT_DOCUMENT",
                        module="RECOURS",
                        table_cible="recours_document",
                        id_enregistrement=recours_obj.id_recours,
                        nouvelle_valeur=(
                            f"Document : {document.nom_fichier}, "
                            f"Recours : {recours_obj.numero_recours}"
                        ),
                        description=(
                            f"Rattachement du document "
                            f"{document.nom_fichier} au recours "
                            f"{recours_obj.numero_recours}"
                        ),
                    )

                messages.success(
                    request,
                    "Le document a été ajouté au recours avec succès."
                )

                return redirect(
                    "recours_detail",
                    id_recours=id_recours
                )

            except Exception as e:

                messages.error(
                    request,
                    f"Erreur lors du dépôt du document : {str(e)}"
                )

    else:

        form = DocumentForm()

    return render(
    request,
    "core/recours_document_form.html",
    {
        "form": form,
        "recours": recours_obj,
        "permissions": permissions,
        "page": "recours",
    }
)




def recours_traiter(request, id_recours):
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

    if "RECOURS_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de traiter les recours."
        )
        return redirect("recours")

    try:
        recours_obj = Recours.objects.get(id_recours=id_recours)
    except Recours.DoesNotExist:
        messages.error(request, "Recours introuvable.")
        return redirect("recours")

    if recours_obj.statut != "EN_ATTENTE":
        messages.error(
            request,
            "Ce recours a déjà été traité."
        )
        return redirect("recours")

    if request.method == "POST":
        form = DecisionRecoursForm(request.POST)

        if form.is_valid():
            decision = form.save(commit=False)

            decision.id_recours = recours_obj
            decision.utilisateur_decision = (
                request.session.get("nom_utilisateur")
            )

            decision.save()

            if decision.type_decision == "ACCEPTEE":
             recours_obj.statut = "ACCEPTEE"

            elif decision.type_decision == "REJETEE":
             recours_obj.statut = "REJETEE"

            elif decision.type_decision == "ACCEPTEE_PARTIELLEMENT":
             recours_obj.statut = "ACCEPTEE_PARTIELLEMENT"

            recours_obj.date_cloture = timezone.now().date()
            recours_obj.observation = decision.observation
            recours_obj.save()

            messages.success(
                request,
                "La décision du recours a été enregistrée."
            )

            return redirect("recours")

    else:
        form = DecisionRecoursForm(
            initial={
                "date_decision": timezone.now().date()
            }
        )

    return render(
        request,
        "core/recours_traiter.html",
        {
            "recours": recours_obj,
            "form": form,
            "permissions": permissions,
            "page": "recours",
        }
    )

