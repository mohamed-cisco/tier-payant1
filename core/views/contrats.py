# core/views/contrats.py
"""
Vues de gestion des contrats.

Fonctions :
- contrats : liste des contrats
- contrat_detail : fiche d'un contrat
- contrat_garantie_create : ajouter une garantie à un contrat
- _generer_numero_contrat : helper
- contrat_create : créer un contrat
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import ContratForm, ContratGarantieForm
from core.models import (
    Adhesion,
    Contrat,
    ContratGarantie,
    DemandeTp,
    Garantie,
    RolePermission,
    Souscripteur,
)
from core.views.champs import (
    get_champs_pour_entite,
    sauvegarder_valeurs_champs,
)
from core.views.dashboard import enregistrer_audit


def contrats(request):
    """Liste des contrats."""
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
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les contrats."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    contrats = (
        Contrat.objects
        .select_related("id_souscripteur")
        .all()
        .order_by("-id_contrat")
    )

    if recherche:
        contrats = contrats.filter(
            Q(numero_contrat__icontains=recherche)
            | Q(id_souscripteur__code_souscripteur__icontains=recherche)
            | Q(id_souscripteur__raison_sociale__icontains=recherche)
            | Q(type_contrat__icontains=recherche)
        )

    if statut:
        contrats = contrats.filter(statut=statut)

    return render(
        request,
        "core/contrats.html",
        {
            "contrats": contrats,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "contrats",
        }
    )


def contrat_detail(request, id_contrat):
    """Fiche détaillée d'un contrat."""
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
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter ce contrat."
        )
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
        .order_by("id_contrat_garantie")
    )

    adhesions = (
        Adhesion.objects
        .select_related("id_adherent", "id_adherent__id_personne")
        .filter(id_contrat=contrat)
        .order_by("id_adhesion")
    )

    demandes_tp = (
        DemandeTp.objects
        .select_related(
            "id_personne_beneficiaire",
            "id_prestataire",
        )
        .filter(id_contrat=contrat)
        .order_by("-id_demande")
    )

    return render(
        request,
        "core/contrat_detail.html",
        {
            "contrat": contrat,
            "garanties": garanties,
            "adhesions": adhesions,
            "demandes_tp": demandes_tp,
            "permissions": permissions,
        }
    )


def contrat_garantie_create(request, id_contrat):
    """Ajouter une garantie à un contrat."""
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

    if "CONTRAT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter une garantie à un contrat."
        )
        return redirect("contrats")

    contrat = (
        Contrat.objects
        .filter(id_contrat=id_contrat, statut="ACTIF")
        .select_related("id_souscripteur")
        .first()
    )

    if not contrat:
        messages.error(request, "Contrat invalide ou introuvable.")
        return redirect("contrats")

    garanties = (
        Garantie.objects
        .filter(statut="ACTIF")
        .order_by("code_garantie")
    )

    if request.method == "POST":
        form = ContratGarantieForm(request.POST)

        form.fields["id_garantie"].choices = [
            (str(g.id_garantie), f"{g.code_garantie} - {g.libelle}")
            for g in garanties
        ]

        if form.is_valid():
            try:
                garantie = Garantie.objects.get(
                    id_garantie=form.cleaned_data["id_garantie"],
                    statut="ACTIF"
                )

                ContratGarantie.objects.create(
                    id_contrat=contrat,
                    id_garantie=garantie,
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Garantie ajoutée au contrat avec succès."
                )
                return redirect("contrat_detail", id_contrat=contrat.id_contrat)

            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {e}")

    else:
        form = ContratGarantieForm()
        form.fields["id_garantie"].choices = [
            (str(g.id_garantie), f"{g.code_garantie} - {g.libelle}")
            for g in garanties
        ]

    return render(
        request,
        "core/contrat_garantie_form.html",
        {
            "form": form,
            "contrat": contrat,
            "permissions": permissions,
        }
    )


def _generer_numero_contrat():
    """Génère un numéro unique de contrat."""
    annee = timezone.now().year
    prefixe = f"CTR-{annee}-"

    numeros = (
        Contrat.objects
        .filter(numero_contrat__startswith=prefixe)
        .values_list("numero_contrat", flat=True)
    )

    valeurs = []
    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_contrat = f"{prefixe}{prochain:04d}"

    while Contrat.objects.filter(numero_contrat=numero_contrat).exists():
        prochain += 1
        numero_contrat = f"{prefixe}{prochain:04d}"

    return numero_contrat


def contrat_create(request):
    """Créer un nouveau contrat."""
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

    if "CONTRAT_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("contrats")

    souscripteurs = (
        Souscripteur.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    if request.method == "POST":
        form = ContratForm(request.POST)

        form.fields["id_souscripteur"].choices = [
            (str(s.id_souscripteur), f"{s.code_souscripteur} - {s.raison_sociale}")
            for s in souscripteurs
        ]

        if form.is_valid():
            try:
                souscripteur = Souscripteur.objects.get(
                    id_souscripteur=form.cleaned_data["id_souscripteur"],
                    statut="ACTIF"
                )

                # Détection de doublon
                doublon = Contrat.objects.filter(
                    id_souscripteur=souscripteur,
                    type_contrat=form.cleaned_data["type_contrat"],
                    date_debut=form.cleaned_data["date_debut"],
                    statut="ACTIF",
                ).first()

                if doublon and not request.POST.get("confirmer_doublon"):
                    messages.warning(
                        request,
                        f"⚠️ Un contrat similaire existe déjà : "
                        f"{doublon.numero_contrat} — "
                        f"{doublon.id_souscripteur.raison_sociale} "
                        f"({doublon.type_contrat}, début le "
                        f"{doublon.date_debut.strftime('%d/%m/%Y')}). "
                        f"Cliquez à nouveau sur Enregistrer pour créer quand même."
                    )
                    return render(
                        request,
                        "core/contrat_form.html",
                        {
                            "form": form,
                            "titre": "Nouveau contrat",
                            "page": "contrats",
                            "doublon_detecte": doublon,
                            "champs_disponibles": get_champs_pour_entite("CONTRAT"),
                        }
                    )

                contrat = Contrat.objects.create(
                    id_souscripteur=souscripteur,
                    numero_contrat=_generer_numero_contrat(),
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    type_contrat=form.cleaned_data["type_contrat"],
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                    objet=form.cleaned_data["objet"] or None,
                    date_signature=form.cleaned_data["date_signature"],
                    date_modification=None,
                )

                # Lier automatiquement les garanties actives
                garanties_actives = Garantie.objects.filter(statut="ACTIF")
                for garantie in garanties_actives:
                    ContratGarantie.objects.get_or_create(
                        id_contrat=contrat,
                        id_garantie=garantie,
                        defaults={
                            "date_debut": contrat.date_debut,
                            "date_fin": contrat.date_fin,
                            "statut": "ACTIF",
                        }
                    )

                sauvegarder_valeurs_champs(
                    request, "CONTRAT", contrat.id_contrat
                )

                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="CONTRAT",
                    table_cible="contrat",
                    id_enregistrement=contrat.id_contrat,
                    nouvelle_valeur=f"{contrat.numero_contrat}",
                    description=f"Création du contrat {contrat.numero_contrat}",
                )

                messages.success(
                    request,
                    f"Contrat {contrat.numero_contrat} créé avec succès."
                )
                return redirect("contrats")

            except Exception as e:
                messages.error(request, f"Erreur : {e}")

    else:
        form = ContratForm()
        form.fields["id_souscripteur"].choices = [
            (str(s.id_souscripteur), f"{s.code_souscripteur} - {s.raison_sociale}")
            for s in souscripteurs
        ]

    champs = get_champs_pour_entite("CONTRAT")
    for c in champs:
        c.valeur_actuelle = None
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/contrat_form.html",
        {
            "form": form,
            "titre": "Nouveau contrat",
            "page": "contrats",
            "champs_disponibles": champs,
        }
    )



def contrat_modifier(request, id_contrat):
    """Modifier un contrat existant."""
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

    if "CONTRAT_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("contrats")

    try:
        contrat = Contrat.objects.get(id_contrat=id_contrat)
    except Contrat.DoesNotExist:
        messages.error(request, "Contrat introuvable.")
        return redirect("contrats")

    souscripteurs = (
        Souscripteur.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    if request.method == "POST":
        form = ContratForm(request.POST)

        form.fields["id_souscripteur"].choices = [
            (str(s.id_souscripteur), f"{s.code_souscripteur} - {s.raison_sociale}")
            for s in souscripteurs
        ]

        if form.is_valid():
            try:
                souscripteur = Souscripteur.objects.get(
                    id_souscripteur=form.cleaned_data["id_souscripteur"],
                    statut="ACTIF"
                )

                contrat.id_souscripteur = souscripteur
                contrat.date_debut = form.cleaned_data["date_debut"]
                contrat.date_fin = form.cleaned_data["date_fin"]
                contrat.type_contrat = form.cleaned_data["type_contrat"]
                contrat.statut = form.cleaned_data["statut"]
                contrat.objet = form.cleaned_data["objet"] or None
                contrat.date_signature = form.cleaned_data["date_signature"]
                contrat.date_modification = timezone.now()
                contrat.save()

                sauvegarder_valeurs_champs(
                    request, "CONTRAT", contrat.id_contrat
                )

                messages.success(request, "Contrat modifié avec succès.")
                return redirect("contrats")

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = ContratForm(initial={
            "numero_contrat": contrat.numero_contrat,
            "id_souscripteur": str(contrat.id_souscripteur_id),
            "date_debut": contrat.date_debut,
            "date_fin": contrat.date_fin,
            "type_contrat": contrat.type_contrat,
            "statut": contrat.statut,
            "objet": contrat.objet,
            "date_signature": contrat.date_signature,
        })
        form.fields["id_souscripteur"].choices = [
            (str(s.id_souscripteur), f"{s.code_souscripteur} - {s.raison_sociale}")
            for s in souscripteurs
        ]

    from core.views.champs import get_valeur_champ
    champs = get_champs_pour_entite("CONTRAT")
    for c in champs:
        c.valeur_actuelle = get_valeur_champ(c, contrat.id_contrat)
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/contrat_form.html",
        {
            "form": form,
            "titre": "Modifier le contrat",
            "page": "contrats",
            "champs_disponibles": champs,
        }
    )




def contrat_radier(request, id_contrat):
    """Radier un contrat existant."""
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

    if "CONTRAT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un contrat."
        )
        return redirect("contrats")

    try:
        contrat = Contrat.objects.get(id_contrat=id_contrat)
    except Contrat.DoesNotExist:
        messages.error(request, "Contrat introuvable.")
        return redirect("contrats")

    if request.method == "POST":
        contrat.statut = "RADIE"
        contrat.date_modification = timezone.now()
        contrat.save()

        messages.success(request, "Contrat radié avec succès.")

    return redirect("contrats")



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

