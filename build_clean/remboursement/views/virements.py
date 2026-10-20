# remboursement/views/virements.py
"""Vues de gestion des virements adhérents."""
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Sum, Q

from core.models import RolePermission, Souscripteur
from core.views.dashboard import enregistrer_audit
from core.views.decorators import session_utilisateur_required

from remboursement.models import VirementAdherent
from remboursement.services.virements import (
    marquer_virement_paye, annuler_virement, marquer_echec_virement,
    corriger_rib_virement, get_virements_a_payer, get_totaux_virements,
    verifier_coordonnees_bancaires,
)


def _get_permissions(id_utilisateur):
    return set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )


@session_utilisateur_required
def virements(request):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("accueil")
    
    statut = request.GET.get("statut", "").strip()
    recherche = request.GET.get("recherche", "").strip()
    
    qs = VirementAdherent.objects.select_related(
        "adherent", "adherent__id_personne", "recap", "recap__souscripteur"
    ).order_by("-date_creation")
    
    if statut:
        qs = qs.filter(statut=statut)
    if recherche:
        qs = qs.filter(
            Q(numero__icontains=recherche)
            | Q(adherent__numero_adherent__icontains=recherche)
            | Q(adherent__id_personne__nom__icontains=recherche)
        )
    
    totaux = {
        'total': qs.count(),
        'montant_total': qs.aggregate(t=Sum('montant'))['t'] or 0,
        'a_payer': qs.filter(statut='A_PAYER').count(),
        'payes': qs.filter(statut='PAYE').count(),
    }
    
    return render(request, "remboursement/virements.html", {
        "virements": qs,
        "statut": statut,
        "recherche": recherche,
        "totaux": totaux,
        "permissions": permissions,
        "page": "remb_virements",
    })


@session_utilisateur_required
def virement_detail(request, id_virement):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_virements")
    
    virement = get_object_or_404(VirementAdherent, id=id_virement)
    bulletins = virement.bulletins.all()
    
    return render(request, "remboursement/virement_detail.html", {
        "virement": virement,
        "bulletins": bulletins,
        "permissions": permissions,
        "page": "remb_virements",
    })


@session_utilisateur_required
def virement_payer(request, id_virement):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_PAY" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_virements")
    
    virement = get_object_or_404(VirementAdherent, id=id_virement)
    
    if request.method == "POST":
        try:
            reference = request.POST.get("reference", "").strip()
            date_paiement = request.POST.get("date_paiement") or None
            
            marquer_virement_paye(
                virement, utilisateur,
                reference=reference, date_paiement=date_paiement
            )
            messages.success(request, f"Virement {virement.numero} payé.")
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_virement_detail", id_virement=virement.id)


@session_utilisateur_required
def virement_echec(request, id_virement):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_PAY" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_virements")
    
    virement = get_object_or_404(VirementAdherent, id=id_virement)
    
    if request.method == "POST":
        motif = request.POST.get("motif", "").strip()
        try:
            marquer_echec_virement(virement, motif, utilisateur)
            messages.warning(request, "Virement marqué en échec.")
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_virement_detail", id_virement=virement.id)


@session_utilisateur_required
def virement_corriger_rib(request, id_virement):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_PAY" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_virements")
    
    virement = get_object_or_404(VirementAdherent, id=id_virement)
    
    if request.method == "POST":
        rib = request.POST.get("rib", "").strip()
        banque = request.POST.get("banque", "").strip()
        try:
            corriger_rib_virement(virement, rib, banque, utilisateur)
            messages.success(request, "RIB corrigé.")
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_virement_detail", id_virement=virement.id)


@session_utilisateur_required
def virement_annuler(request, id_virement):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_PAY" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_virements")
    
    virement = get_object_or_404(VirementAdherent, id=id_virement)
    
    if request.method == "POST":
        motif = request.POST.get("motif", "").strip()
        try:
            annuler_virement(virement, motif, utilisateur)
            messages.warning(request, "Virement annulé.")
        except Exception as e:
            messages

            

# ============================================================
# DÉTAIL D'UN VIREMENT
# ============================================================

@session_utilisateur_required
def virement_detail(request, id_virement):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_virements")
    
    virement = get_object_or_404(VirementAdherent, id=id_virement)
    bulletins = virement.bulletins.all()
    
    return render(request, "remboursement/virement_detail.html", {
        "virement": virement,
        "bulletins": bulletins,
        "permissions": permissions,
        "page": "remb_virements",
    })


# ============================================================
# LISTE DES VIREMENTS À PAYER
# ============================================================

@session_utilisateur_required
def virements_a_payer(request):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_PAY" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_virements")
    
    souscripteur_id = request.GET.get("souscripteur", "").strip()
    souscripteur = None
    if souscripteur_id:
        souscripteur = Souscripteur.objects.filter(id_souscripteur=souscripteur_id).first()
    
    virements_qs = get_virements_a_payer(souscripteur=souscripteur)
    totaux = get_totaux_virements(souscripteur=souscripteur)
    souscripteurs = Souscripteur.objects.filter(statut='ACTIF').order_by('raison_sociale')
    
    return render(request, "remboursement/virements_a_payer.html", {
        "virements": virements_qs,
        "totaux": totaux,
        "souscripteurs": souscripteurs,
        "souscripteur_id": souscripteur_id,
        "permissions": permissions,
        "page": "remb_virements",
    })
# ============================================================
# BORDEREAU BANCAIRE
# ============================================================

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from remboursement.services.bordereau import (
    get_bordereau_virements,
    construire_lignes_bordereau,
    calculer_totaux,
)


def _permissions(request):
    """Helper : retourne l'ensemble des permissions de l'utilisateur."""
    from core.models import RolePermission
    id_utilisateur = request.session.get("id_utilisateur")
    if not id_utilisateur:
        return set()
    return set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF",
        )
        .values_list("id_permission__code_permission", flat=True)
    )


def bordereau_bancaire(request):
    """Aperçu écran du bordereau bancaire avec filtres."""
    if not request.session.get("id_utilisateur"):
        from django.shortcuts import redirect
        return redirect("connexion")

    permissions = _permissions(request)
    if "REMBOURSEMENT_VIEW" not in permissions:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "Accès non autorisé.")
        return redirect("accueil")

    # Filtres
    date_debut = request.GET.get("date_debut") or None
    date_fin = request.GET.get("date_fin") or None
    banque = request.GET.get("banque") or None
    mode_paiement = request.GET.get("mode_paiement") or None

    # Récupérer les virements
    virements = get_bordereau_virements(
        date_debut=date_debut,
        date_fin=date_fin,
        banque=banque,
        mode_paiement=mode_paiement,
    )

    lignes = construire_lignes_bordereau(virements)
    totaux = calculer_totaux(lignes)

    # Liste des banques distinctes pour filtre
    from remboursement.models import VirementAdherent
    banques = (
        VirementAdherent.objects
        .exclude(banque="")
        .values_list("banque", flat=True)
        .distinct()
        .order_by("banque")
    )

    context = {
        "lignes": lignes,
        "totaux": totaux,
        "banques": banques,
        "date_debut": date_debut or "",
        "date_fin": date_fin or "",
        "banque_filtre": banque or "",
        "mode_paiement_filtre": mode_paiement or "",
        "page": "remb_virements",
        "permissions": permissions,
        "utilisateur": None,  # injecté par context_processor
    }
    return render(request, "remboursement/bordereau_bancaire.html", context)


def bordereau_bancaire_pdf(request):
    """Génère le PDF du bordereau bancaire."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )

    if not request.session.get("id_utilisateur"):
        from django.shortcuts import redirect
        return redirect("connexion")

    permissions = _permissions(request)
    if "REMBOURSEMENT_VIEW" not in permissions:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "Accès non autorisé.")
        return redirect("accueil")

    # Filtres (identiques à la vue écran)
    date_debut = request.GET.get("date_debut") or None
    date_fin = request.GET.get("date_fin") or None
    banque = request.GET.get("banque") or None
    mode_paiement = request.GET.get("mode_paiement") or None

    virements = get_bordereau_virements(
        date_debut=date_debut,
        date_fin=date_fin,
        banque=banque,
        mode_paiement=mode_paiement,
    )
    lignes = construire_lignes_bordereau(virements)
    totaux = calculer_totaux(lignes)

    # ============ Construction PDF ============
    response = HttpResponse(content_type="application/pdf")
    filename = f"bordereau_bancaire_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Bordereau bancaire - SAGPS",
    )

    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle(
        "Titre",
        parent=styles["Title"],
        textColor=colors.HexColor("#123b65"),
        fontSize=16,
        spaceAfter=6,
    )
    style_sous_titre = ParagraphStyle(
        "SousTitre",
        parent=styles["Normal"],
        textColor=colors.HexColor("#64748b"),
        fontSize=10,
        spaceAfter=14,
    )
    style_cell = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=10,
    )

    elements = []

    # En-tête
    elements.append(Paragraph("SAGPS — Bordereau bancaire", style_titre))
    elements.append(Paragraph(
        f"Édité le {timezone.now().strftime('%d/%m/%Y à %H:%M')} "
        f"| {totaux['nb_virements']} virement(s) | "
        f"Total : <b>{totaux['total']:.2f} DA</b>",
        style_sous_titre,
    ))

    # Période
    if date_debut or date_fin:
        info = "Période : "
        info += f"du {date_debut or '—'} au {date_fin or '—'}"
        elements.append(Paragraph(info, style_cell))
        elements.append(Spacer(1, 6))

    # Tableau
    headers = [
        "N° Virement",
        "Bénéficiaire",
        "N° Adhérent",
        "Banque",
        "RIB",
        "Mode",
        "Nb B.",
        "Montant (DA)",
    ]

    data = [headers]
    for l in lignes:
        data.append([
            Paragraph(l["numero"], style_cell),
            Paragraph(l["adherent_nom"], style_cell),
            Paragraph(l["adherent_numero"], style_cell),
            Paragraph(l["banque"], style_cell),
            Paragraph(l["rib"], style_cell),
            Paragraph(l["mode_paiement"], style_cell),
            Paragraph(str(l["nb_bulletins"]), style_cell),
            Paragraph(f"{l['montant']:.2f}", style_cell),
        ])

    # Ligne total
    data.append([
        "", "", "", "", "", "", "TOTAL",
        Paragraph(f"<b>{totaux['total']:.2f}</b>", style_cell),
    ])

    col_widths = [
        2.6 * cm, 4.2 * cm, 2.6 * cm, 2.4 * cm,
        4.2 * cm, 2.2 * cm, 1.2 * cm, 2.4 * cm,
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1)

    style_table = [
        # En-tête
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Corps
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (6, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        # Total
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        # Zebra
    ]
    for i in range(1, len(data) - 1):
        if i % 2 == 0:
            style_table.append(
                ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8fafc"))
            )

    table.setStyle(TableStyle(style_table))
    elements.append(table)

    # Bloc signature
    elements.append(Spacer(1, 20))
    sign_data = [
        ["Préparé par (SAGPS)", "Vérifié par", "Reçu par la banque"],
        ["", "", ""],
        ["", "", ""],
        ["\nNom et signature", "\nNom et signature", "\nCachet et date"],
    ]
    sign_table = Table(sign_data, colWidths=[7 * cm, 7 * cm, 7 * cm])
    sign_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
    ]))
    elements.append(sign_table)

    # Pied de page
    elements.append(Spacer(1, 14))
    elements.append(Paragraph(
        "SAGPS — Plateforme Tiers Payant — Document interne",
        style_sous_titre,
    ))

    doc.build(elements)
    return response