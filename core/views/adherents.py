# core/views/adherents.py
"""
Vues de gestion des adhérents.

Fonctions :
- adherents : liste des adhérents
- adherent_detail : fiche d'un adhérent
- _generer_numero_adherent : helper
- _generer_numero_personne : helper
- adherent_create : créer un adhérent
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
import openpyxl
from openpyxl.styles import Font
from django.http import HttpResponse

from core.forms import AdherentForm
from core.models import (
    Adherent,
    AyantDroit,
    Personne,
    RolePermission,
)
from core.views.champs import (
    get_champs_pour_entite,
    get_valeurs_champs_entite,
    sauvegarder_valeurs_champs,
)
from core.views.dashboard import enregistrer_audit
from core.views.decorators import session_utilisateur_required


# ============================================================
# IMPORTS POUR LES PDF
# ============================================================
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
# Imports pour les PDF
from django.http import HttpResponse
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)


@session_utilisateur_required
def adherents(request):
    """Liste des adhérents."""
    utilisateur = request.utilisateur
    id_utilisateur = utilisateur.id_utilisateur

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les adhérents."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    adherents = (
        Adherent.objects
        .select_related("id_personne")
        .all()
        .order_by("-id_adherent")
    )

    if recherche:
        adherents = adherents.filter(
            Q(numero_adherent__icontains=recherche)
            | Q(id_personne__numero_personne__icontains=recherche)
            | Q(id_personne__nom__icontains=recherche)
            | Q(id_personne__prenom__icontains=recherche)
            | Q(id_personne__telephone__icontains=recherche)
        )

    if statut:
        adherents = adherents.filter(statut=statut)

    return render(
        request,
        "core/adherents.html",
        {
            "adherents": adherents,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "adherents",
        }
    )


def adherent_detail(request, id_adherent):
    """Fiche détaillée d'un adhérent."""
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

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter cet adhérent."
        )
        return redirect("adherents")

    try:
        adherent = (
            Adherent.objects
            .select_related("id_personne")
            .get(id_adherent=id_adherent)
        )
    except Adherent.DoesNotExist:
        messages.error(request, "Adhérent introuvable.")
        return redirect("adherents")

    ayants_droit = (
        AyantDroit.objects
        .select_related("id_personne")
        .filter(id_adherent=adherent)
        .order_by("id_ayant_droit")
    )

    # Charger les champs personnalisés pour chaque ayant droit
    for ad in ayants_droit:
        ad.champs_personnalises = get_valeurs_champs_entite(
            "AYANT_DROIT", ad.id_ayant_droit
        )

    champs_perso_adherent = get_valeurs_champs_entite(
        "ADHERENT", adherent.id_adherent
    )
    champs_perso_adherent = [
        c for c in champs_perso_adherent
        if c["valeur"] and str(c["valeur"]).strip()
    ]

    return render(
        request,
        "core/adherent_detail.html",
        {
            "adherent": adherent,
            "ayants_droit": ayants_droit,
            "permissions": permissions,
            "page": "adherents",
            "champs_personnalises": champs_perso_adherent,
        }
    )


def _generer_numero_adherent():
    """Génère un numéro unique d'adhérent."""
    annee = timezone.now().year
    prefixe = f"ADH-{annee}-"

    numeros = (
        Adherent.objects
        .filter(numero_adherent__startswith=prefixe)
        .values_list("numero_adherent", flat=True)
    )

    valeurs = []
    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_adherent = f"{prefixe}{prochain:04d}"

    while Adherent.objects.filter(
        numero_adherent=numero_adherent
    ).exists():
        prochain += 1
        numero_adherent = f"{prefixe}{prochain:04d}"

    return numero_adherent


def _generer_numero_personne():
    """Génère un numéro unique de personne."""
    annee = timezone.now().year
    prefixe = f"PERS-{annee}-"

    numeros = (
        Personne.objects
        .filter(numero_personne__startswith=prefixe)
        .values_list("numero_personne", flat=True)
    )

    valeurs = []
    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_personne = f"{prefixe}{prochain:04d}"

    while Personne.objects.filter(
        numero_personne=numero_personne
    ).exists():
        prochain += 1
        numero_personne = f"{prefixe}{prochain:04d}"

    return numero_personne


def adherent_create(request):
    """Créer un nouvel adhérent."""
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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un adhérent."
        )
        return redirect("adherents")

    if request.method == "POST":
        form = AdherentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    doublon = (
                        Adherent.objects
                        .filter(
                            statut="ACTIF",
                            id_personne__nom__iexact=form.cleaned_data["nom"].strip(),
                            id_personne__prenom__iexact=form.cleaned_data["prenom"].strip(),
                            id_personne__date_naissance=form.cleaned_data["date_naissance"],
                        )
                        .first()
                    )

                    if doublon:
                        messages.error(
                            request,
                            f"Cet adhérent existe déjà "
                            f"({doublon.numero_adherent})."
                        )
                        return render(
                            request,
                            "core/adherent_form.html",
                            {
                                "form": form,
                                "titre": "Nouvel adhérent",
                                "page": "adherents",
                            }
                        )

                    personne = Personne.objects.create(
                        numero_personne=_generer_numero_personne(),
                        nom=form.cleaned_data["nom"].strip(),
                        prenom=form.cleaned_data["prenom"].strip(),
                        date_naissance=form.cleaned_data["date_naissance"],
                        sexe=form.cleaned_data["sexe"] or None,
                        adresse=form.cleaned_data["adresse"] or None,
                        telephone=form.cleaned_data["telephone"] or None,
                        email=form.cleaned_data["email"] or None,
                        statut=form.cleaned_data["statut"],
                        date_creation=timezone.now(),
                    )

                    adherent = Adherent.objects.create(
                        id_personne=personne,
                        numero_adherent=_generer_numero_adherent(),
                        statut=form.cleaned_data["statut"],
                        date_adhesion=form.cleaned_data["date_adhesion"],
                        date_creation=timezone.now(),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="CREATION",
                        module="ADHERENTS",
                        table_cible="adherent",
                        id_enregistrement=adherent.id_adherent,
                        nouvelle_valeur=(
                            f"Numéro adhérent : "
                            f"{adherent.numero_adherent}, "
                            f"Statut : {adherent.statut}"
                        ),
                        description=(
                            f"Création de l'adhérent "
                            f"{adherent.numero_adherent}"
                        ),
                    )

                    # Sauvegarder les champs personnalisés
                    sauvegarder_valeurs_champs(
                        request, "ADHERENT", adherent.id_adherent
                    )

                messages.success(request, "Adhérent créé avec succès.")
                return redirect("adherents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )
    else:
        form = AdherentForm()

    # Charger les champs personnalisés (dans tous les cas)
    champs = get_champs_pour_entite("ADHERENT")
    for c in champs:
        c.valeur_actuelle = None
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/adherent_form.html",
        {
            "form": form,
            "titre": "Nouvel adhérent",
            "page": "adherents",
            "champs_disponibles": champs,
        }
    )


def adherent_modifier(request, id_adherent):
    """Modifier un adhérent existant."""
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

    if "ADHERENT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un adhérent."
        )
        return redirect("adherents")

    try:
        adherent = (
            Adherent.objects
            .select_related("id_personne")
            .get(id_adherent=id_adherent)
        )
    except Adherent.DoesNotExist:
        messages.error(request, "Adhérent introuvable.")
        return redirect("adherents")

    personne = adherent.id_personne

    if request.method == "POST":
        form = AdherentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    doublon = (
                        Adherent.objects
                        .filter(
                            statut="ACTIF",
                            id_personne__nom__iexact=form.cleaned_data["nom"].strip(),
                            id_personne__prenom__iexact=form.cleaned_data["prenom"].strip(),
                            id_personne__date_naissance=form.cleaned_data["date_naissance"],
                        )
                        .exclude(id_adherent=adherent.id_adherent)
                        .first()
                    )

                    if doublon:
                        messages.error(
                            request,
                            f"Un autre adhérent existe déjà avec ces informations "
                            f"({doublon.numero_adherent})."
                        )
                    else:
                        personne.nom = form.cleaned_data["nom"].strip()
                        personne.prenom = form.cleaned_data["prenom"].strip()
                        personne.date_naissance = form.cleaned_data["date_naissance"]
                        personne.sexe = form.cleaned_data["sexe"] or None
                        personne.adresse = form.cleaned_data["adresse"] or None
                        personne.telephone = form.cleaned_data["telephone"] or None
                        personne.email = form.cleaned_data["email"] or None
                        personne.statut = form.cleaned_data["statut"]
                        personne.date_modification = timezone.now()
                        personne.save()

                        adherent.statut = form.cleaned_data["statut"]
                        adherent.date_adhesion = form.cleaned_data["date_adhesion"]
                        adherent.save()

                        # Mettre à jour les champs personnalisés
                        sauvegarder_valeurs_champs(
                            request, "ADHERENT", adherent.id_adherent
                        )

                        messages.success(
                            request,
                            "Adhérent modifié avec succès."
                        )
                        return redirect("adherents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )
    else:
        form = AdherentForm(
            initial={
                "numero_adherent": adherent.numero_adherent,
                "numero_personne": personne.numero_personne,
                "nom": personne.nom,
                "prenom": personne.prenom,
                "date_naissance": personne.date_naissance,
                "sexe": personne.sexe,
                "adresse": personne.adresse,
                "telephone": personne.telephone,
                "email": personne.email,
                "date_adhesion": adherent.date_adhesion,
                "statut": adherent.statut,
            }
        )

    # Charger les champs personnalisés avec valeurs actuelles
    champs = get_champs_pour_entite("ADHERENT")
    for c in champs:
        c.valeur_actuelle = get_valeur_champ(c, adherent.id_adherent)
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/adherent_form.html",
        {
            "form": form,
            "titre": "Modifier l'adhérent",
            "page": "adherents",
            "champs_disponibles": champs,
        }
    )


def adherent_radier(request, id_adherent):
    """Radier un adhérent."""
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

    if "ADHERENT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un adhérent."
        )
        return redirect("adherents")

    try:
        adherent = Adherent.objects.get(id_adherent=id_adherent)
    except Adherent.DoesNotExist:
        messages.error(request, "Adhérent introuvable.")
        return redirect("adherents")

    if request.method == "POST":
        try:
            adherent.statut = "RADIE"
            adherent.date_radiation = timezone.now().date()
            adherent.save()

            enregistrer_audit(
                request=request,
                type_action="RADIATION",
                module="ADHERENTS",
                table_cible="adherent",
                id_enregistrement=adherent.id_adherent,
                ancienne_valeur="Statut : ACTIF",
                nouvelle_valeur="Statut : RADIE",
                description=f"Radiation de l'adhérent {adherent.numero_adherent}",
            )

            messages.success(request, "Adhérent radié avec succès.")

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la radiation : {e}"
            )

        return redirect("adherents")

    return render(
        request,
        "core/adherent_radier.html",
        {
            "adherent": adherent,
        }
    )


def adherent_carte_pdf(request, id_adherent):
    """Génère la carte d'adhérent en PDF (avec ayants droit)."""
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

    if "ADHERENT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("adherents")

    try:
        adherent = (
            Adherent.objects
            .select_related("id_personne")
            .get(id_adherent=id_adherent)
        )
    except Adherent.DoesNotExist:
        messages.error(request, "Adhérent introuvable.")
        return redirect("adherents")

    adhesion = (
        Adhesion.objects
        .filter(id_adherent=adherent, statut="ACTIF")
        .select_related("id_contrat", "id_contrat__id_souscripteur")
        .order_by("-date_debut")
        .first()
    )

    # ⬇️ Récupérer les ayants droit ACTIFS
    ayants_droit = (
        AyantDroit.objects
        .select_related("id_personne")
        .filter(id_adherent=adherent, statut="ACTIF")
        .order_by("id_ayant_droit")
    )
        # Récupérer les champs personnalisés
    champs_perso = get_valeurs_champs_entite(
        "ADHERENT", adherent.id_adherent
    )
    # Filtrer pour ne garder que ceux qui ont une valeur
    champs_perso = [
        item for item in champs_perso
        if item["valeur"] and str(item["valeur"]).strip()
    ]

    personne = adherent.id_personne

    import os
    from django.conf import settings
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A5, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Carte-{adherent.numero_adherent}.pdf"'
    )

    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A5),
        rightMargin=0.8 * cm,
        leftMargin=0.8 * cm,
        topMargin=0.6 * cm,
        bottomMargin=0.6 * cm,
    )

    elements = []
    styles = getSampleStyleSheet()

    style_titre = ParagraphStyle(
        "Titre", parent=styles["Title"], fontSize=16,
        textColor=colors.HexColor("#123b65"), alignment=2, leading=20,
    )

    # =========================
    # EN-TÊTE AVEC LOGO
    # =========================
    logo_path = os.path.join(
        settings.BASE_DIR, "core", "static", "core", "img", "logo-sagps.png"
    )

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=5 * cm, height=2.2 * cm)
    else:
        logo = ""

    titre_header = Paragraph(
        "<b>CARTE D'ADHÉRENT</b><br/>"
        f"<font size=10>Djazair Med - Tiers Payant</font>",
        style_titre,
    )

    header_table = Table([[logo, titre_header]], colWidths=[7 * cm, 11.5 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#123b65")),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.4 * cm))

    # =========================
    # INFOS DU TITULAIRE
    # =========================
    infos_data = [
        ["Nom", personne.nom or "-"],
        ["Prénom", personne.prenom or "-"],
        ["Date de naissance",
         personne.date_naissance.strftime("%d/%m/%Y") if personne.date_naissance else "-"],
        ["N° Adhérent", adherent.numero_adherent],
        ["Contrat", adhesion.id_contrat.numero_contrat if adhesion else "-"],
        ["Organisme",
         adhesion.id_contrat.id_souscripteur.raison_sociale if adhesion else "-"],
        ["Valide du",
         adhesion.date_debut.strftime("%d/%m/%Y") if adhesion and adhesion.date_debut else "-"],
        ["Au",
         adhesion.date_fin.strftime("%d/%m/%Y") if adhesion and adhesion.date_fin else "Illimité"],
    ]

    # Ajouter les champs personnalisés
    for item in champs_perso:
        infos_data.append([
            item["champ"].libelle,
            str(item["valeur"]),
        ])

    infos_table = Table(infos_data, colWidths=[4 * cm, 14.5 * cm])
    infos_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (0, -1), 8),
        ("FONTSIZE", (1, 0), (1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#123b65")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(infos_table)

    # =========================
    # AYANTS DROIT (si présents)
    # =========================
    if ayants_droit:
        elements.append(Spacer(1, 0.3 * cm))

        # Titre de section
        style_section_ayant = ParagraphStyle(
            "SectionAyant",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#123b65"),
            fontName="Helvetica-Bold",
            spaceAfter=5,
        )
        elements.append(Paragraph("AYANTS DROIT", style_section_ayant))

        # Tableau des ayants droit
        ad_data = [["Nom & Prénom", "N° Personne", "Lien", "Date de naissance"]]

        for ad in ayants_droit:
            p = ad.id_personne
            lien_label = ad.type_lien
            if ad.type_lien == "ENFANT":
                lien_label = "Enfant"
            elif ad.type_lien == "CONJOINT":
                lien_label = "Conjoint(e)"
            elif ad.type_lien == "PARENT":
                lien_label = "Parent"

            ad_data.append([
                f"{p.nom} {p.prenom}",
                p.numero_personne or "-",
                lien_label,
                p.date_naissance.strftime("%d/%m/%Y") if p.date_naissance else "-",
            ])

        ad_table = Table(
            ad_data,
            colWidths=[6 * cm, 4 * cm, 4 * cm, 4.5 * cm],
            repeatRows=1,
        )
        ad_table.setStyle(TableStyle([
            # En-tête
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Corps
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            # Bordures
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(ad_table)

    # =========================
    # PIED : SIGNATURE
    # =========================
    
    elements.append(Spacer(1, 0.3 * cm))

    pied_data = [[
        Paragraph("<b>Signature et cachet</b>", styles["Normal"]),
        Paragraph(
            f"<b>N° : {adherent.numero_adherent}</b>",
            ParagraphStyle("right", parent=styles["Normal"], alignment=2),
        ),
    ]]
    pied_table = Table(pied_data, colWidths=[9 * cm, 9.5 * cm])
    pied_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(pied_table)

    document.build(elements)

    return response




def adherent_import_excel(request):

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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'importer des adhérents."
        )
        return redirect("adherents")

    if request.method == "POST":

        form = ImportAdherentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            try:

                import openpyxl

                fichier = form.cleaned_data["fichier"]

                if not fichier.name.lower().endswith(".xlsx"):
                    messages.error(
                        request,
                        "Veuillez sélectionner un fichier Excel au format .xlsx."
                    )
                    return redirect("adherent_import_excel")

                workbook = openpyxl.load_workbook(
                    fichier,
                    data_only=True
                )

                feuille = workbook.active

                nombre_importes = 0
                erreurs = []

                with transaction.atomic():

                    for numero_ligne, ligne in enumerate(
                        feuille.iter_rows(
                            min_row=2,
                            values_only=True
                        ),
                        start=2
                    ):

                        if not any(ligne):
                            continue

                        nom = ligne[0]
                        prenom = ligne[1]
                        date_naissance = ligne[2]
                        sexe = ligne[3]
                        adresse = ligne[4]
                        telephone = ligne[5]
                        email = ligne[6]
                        date_adhesion = ligne[7]

                        if not nom or not prenom:

                            erreurs.append(
                                f"Ligne {numero_ligne} : "
                                "Nom ou prénom manquant."
                            )

                            continue

                        # Vérification doublon
                        doublon = (
                            Adherent.objects
                            .filter(
                                statut="ACTIF",
                                id_personne__nom__iexact=str(nom).strip(),
                                id_personne__prenom__iexact=str(prenom).strip(),
                                id_personne__date_naissance=date_naissance,
                            )
                            .first()
                        )

                        if doublon:

                            erreurs.append(
                                f"Ligne {numero_ligne} : "
                                f"Cet adhérent existe déjà "
                                f"({doublon.numero_adherent})."
                            )

                            continue

                        # Création de la personne
                        personne = Personne.objects.create(

                            numero_personne=_generer_numero_personne(),

                            nom=str(nom).strip(),

                            prenom=str(prenom).strip(),

                            date_naissance=date_naissance,

                            sexe=(
                                str(sexe).strip()
                                if sexe
                                else None
                            ),

                            adresse=(
                                str(adresse).strip()
                                if adresse
                                else None
                            ),

                            telephone=(
                                str(telephone).strip()
                                if telephone
                                else None
                            ),

                            email=(
                                str(email).strip()
                                if email
                                else None
                            ),

                            statut="ACTIF",

                            date_creation=timezone.now(),

                            date_modification=None,
                        )

                        # Création de l'adhérent
                        adherent = Adherent.objects.create(

                            id_personne=personne,

                            numero_adherent=_generer_numero_adherent(),

                            date_creation=timezone.now(),

                            statut="ACTIF",

                            date_adhesion=date_adhesion,

                            date_radiation=None,
                        )

                        # Audit
                        enregistrer_audit(
                            request=request,
                            type_action="IMPORTATION",
                            module="ADHERENTS",
                            table_cible="adherent",
                            id_enregistrement=adherent.id_adherent,
                            nouvelle_valeur=(
                                f"Import Excel - "
                                f"Adhérent : {adherent.numero_adherent}"
                            ),
                            description=(
                                f"Importation de l'adhérent "
                                f"{adherent.numero_adherent}"
                            ),
                        )

                        nombre_importes += 1


                if nombre_importes > 0:

                    messages.success(
                        request,
                        f"{nombre_importes} adhérent(s) importé(s) "
                        "avec succès."
                    )

                if erreurs:

                    for erreur in erreurs[:10]:

                        messages.warning(
                            request,
                            erreur
                        )

                    if len(erreurs) > 10:

                        messages.warning(
                            request,
                            f"{len(erreurs) - 10} autre(s) erreur(s)."
                        )

                return redirect("adherents")

            except Exception as e:

                messages.error(
                    request,
                    f"Erreur lors de l'importation : {str(e)}"
                )

    else:

        form = ImportAdherentForm()

    return render(
        request,
        "core/adherent_import_excel.html",
        {
            "form": form,
        }
    )



def adherent_export_excel(request):

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

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les adhérents."
        )
        return redirect("adherents")

    import openpyxl

    from openpyxl.styles import Font
    from django.http import HttpResponse


    adherents_list = (
        Adherent.objects
        .select_related("id_personne")
        .order_by("numero_adherent")
    )


    workbook = openpyxl.Workbook()

    feuille = workbook.active

    feuille.title = "Adherents"


    entetes = [

        "Numéro adhérent",

        "Numéro personne",

        "Nom",

        "Prénom",

        "Date de naissance",

        "Sexe",

        "Adresse",

        "Téléphone",

        "Email",

        "Date adhésion",

        "Statut",

    ]


    feuille.append(entetes)


    for cellule in feuille[1]:

        cellule.font = Font(bold=True)


    for adherent in adherents_list:

        personne = adherent.id_personne

        feuille.append([

            adherent.numero_adherent,

            personne.numero_personne,

            personne.nom,

            personne.prenom,

            personne.date_naissance,

            personne.sexe,

            personne.adresse,

            personne.telephone,

            personne.email,

            adherent.date_adhesion,

            adherent.statut,

        ])


    for colonne in feuille.columns:

        longueur_max = 0

        lettre_colonne = colonne[0].column_letter


        for cellule in colonne:

            try:

                longueur = len(
                    str(cellule.value)
                )

                if longueur > longueur_max:

                    longueur_max = longueur

            except Exception:

                pass


        feuille.column_dimensions[
            lettre_colonne
        ].width = longueur_max + 2


    response = HttpResponse(

        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    )


    response[
        "Content-Disposition"
    ] = (

        'attachment; filename="adherents.xlsx"'

    )


    workbook.save(response)


    return response
