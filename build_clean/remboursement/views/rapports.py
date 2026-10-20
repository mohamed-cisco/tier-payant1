# remboursement/views/rapports.py
"""
Rapports de suivi du module Remboursement.
5 rapports : par mois, par souscripteur, en attente, échecs, écarts.
"""
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q

from core.models import RolePermission, Souscripteur
from core.views.decorators import session_utilisateur_required

from remboursement.models import (
    BulletinSoins, RecapSouscripteur, VirementAdherent
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


# ============================================================
# RAPPORT 1 — REMBOURSEMENTS PAR MOIS
# ============================================================

@session_utilisateur_required
def remb_par_mois(request):
    """Rapport des remboursements par mois."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")
    
    # Année sélectionnée
    aujourd_hui = timezone.now().date()
    try:
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        annee = aujourd_hui.year
    
    # Pour chaque mois de l'année
    lignes = []
    total_annee_bulletins = 0
    total_annee_rembourse = 0
    total_annee_remboursements = 0
    
    for mois in range(1, 13):
        date_debut = date(annee, mois, 1)
        dernier_jour = monthrange(annee, mois)[1]
        date_fin = date(annee, mois, dernier_jour)
        
        bulletins = BulletinSoins.objects.filter(
            date_soins__gte=date_debut,
            date_soins__lte=date_fin,
            statut__in=['REMBOURSE', 'REVERSE'],
        )
        
        remboursements = RecapSouscripteur.objects.filter(
            periode_debut__gte=date_debut,
            periode_debut__lte=date_fin,
        )
        
        nb_bulletins = bulletins.count()
        montant_rembourse = bulletins.aggregate(
            t=Sum('montant_total_rembourse')
        )['t'] or Decimal('0')
        
        nb_remboursements = remboursements.filter(statut='PAYE').count()
        montant_recu = remboursements.aggregate(
            t=Sum('montant_recu')
        )['t'] or Decimal('0')
        
        lignes.append({
            'mois': mois,
            'nom_mois': [
                'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
            ][mois - 1],
            'nb_bulletins': nb_bulletins,
            'montant_rembourse': montant_rembourse,
            'nb_remboursements': nb_remboursements,
            'montant_recu': montant_recu,
        })
        
        total_annee_bulletins += nb_bulletins
        total_annee_rembourse += montant_rembourse
        total_annee_remboursements += nb_remboursements
    
    return render(request, "remboursement/rapport_par_mois.html", {
        "annee": annee,
        "lignes": lignes,
        "total_annee_bulletins": total_annee_bulletins,
        "total_annee_rembourse": total_annee_rembourse,
        "total_annee_remboursements": total_annee_remboursements,
        "permissions": permissions,
        "page": "rapports",
    })


# ============================================================
# RAPPORT 2 — REMBOURSEMENTS PAR SOUSCRIPTEUR
# ============================================================

@session_utilisateur_required
def remb_par_souscripteur(request):
    """Rapport des remboursements par souscripteur."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")
    
    # Période
    aujourd_hui = timezone.now().date()
    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year
    
    date_debut = date(annee, mois, 1)
    date_fin = date(annee, mois, monthrange(annee, mois)[1])
    
    # Pour chaque souscripteur
    lignes = []
    for s in Souscripteur.objects.filter(statut='ACTIF').order_by('raison_sociale'):
        bulletins = BulletinSoins.objects.filter(
            souscripteur=s,
            date_soins__gte=date_debut,
            date_soins__lte=date_fin,
        )
        
        recaps = RecapSouscripteur.objects.filter(
            souscripteur=s,
            periode_debut__gte=date_debut,
            periode_debut__lte=date_fin,
        )
        
        nb_bulletins = bulletins.count()
        montant_rembourse = bulletins.filter(
            statut__in=['REMBOURSE', 'REVERSE']
        ).aggregate(t=Sum('montant_total_rembourse'))['t'] or Decimal('0')
        
        nb_recaps = recaps.count()
        montant_recu = recaps.aggregate(t=Sum('montant_recu'))['t'] or Decimal('0')
        
        if nb_bulletins > 0 or nb_recaps > 0:
            lignes.append({
                'souscripteur': s,
                'nb_bulletins': nb_bulletins,
                'montant_rembourse': montant_rembourse,
                'nb_recaps': nb_recaps,
                'montant_recu': montant_recu,
            })
    
    return render(request, "remboursement/rapport_par_souscripteur.html", {
        "mois": mois,
        "annee": annee,
        "nom_mois": [
            'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ][mois - 1],
        "lignes": lignes,
        "permissions": permissions,
        "page": "rapports",
    })


# ============================================================
# RAPPORT 3 — BULLETINS EN ATTENTE
# ============================================================

@session_utilisateur_required
def remb_en_attente(request):
    """Rapport des bulletins en attente de traitement."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")
    
    # Nombre de jours
    try:
        jours = int(request.GET.get("jours", 30))
    except (ValueError, TypeError):
        jours = 30
    
    date_limite = timezone.now().date() - timedelta(days=jours)
    
    # Bulletins en attente
    bulletins = BulletinSoins.objects.filter(
        statut__in=['RECU', 'EN_VERIFICATION', 'VALIDE'],
        date_depot__date__lte=date_limite,
    ).select_related(
        'adherent', 'adherent__id_personne', 'souscripteur', 'patient'
    ).order_by('date_depot')
    
    # Statistiques
    stats = {
        'total': bulletins.count(),
        'montant_total': bulletins.aggregate(
            t=Sum('montant_total_rembourse')
        )['t'] or Decimal('0'),
    }
    
    return render(request, "remboursement/rapport_en_attente.html", {
        "jours": jours,
        "date_limite": date_limite,
        "bulletins": bulletins,
        "stats": stats,
        "permissions": permissions,
        "page": "rapports",
    })


# ============================================================
# RAPPORT 4 — VIREMENTS EN ÉCHEC
# ============================================================

@session_utilisateur_required
def remb_echecs(request):
    """Rapport des virements en échec."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")
    
    # Virements en échec
    virements = VirementAdherent.objects.filter(
        statut='ECHEC'
    ).select_related(
        'adherent', 'adherent__id_personne', 'recap'
    ).order_by('-date_creation')
    
    # Statistiques
    stats = {
        'total': virements.count(),
        'montant_total': virements.aggregate(
            t=Sum('montant')
        )['t'] or Decimal('0'),
    }
    
    return render(request, "remboursement/rapport_echecs.html", {
        "virements": virements,
        "stats": stats,
        "permissions": permissions,
        "page": "rapports",
    })


# ============================================================
# RAPPORT 5 — ÉCARTS RÉCAPS
# ============================================================

@session_utilisateur_required
def remb_ecarts(request):
    """Rapport des écarts entre montants demandés et reçus."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")
    
    # Tous les récaps payés
    recaps = RecapSouscripteur.objects.filter(
        statut='PAYE'
    ).select_related('souscripteur').order_by('-periode_debut')
    
    # Calculer les écarts
    lignes = []
    total_demande = Decimal('0')
    total_recu = Decimal('0')
    total_ecart = Decimal('0')
    
    for r in recaps:
        ecart = (r.montant_total or 0) - (r.montant_recu or 0)
        
        lignes.append({
            'recap': r,
            'ecart': ecart,
            'a_ecart': ecart != 0,
        })
        
        total_demande += r.montant_total or 0
        total_recu += r.montant_recu or 0
        total_ecart += ecart
    
    # Filtrer : ne montrer que les écarts non-nuls ?
    filtre = request.GET.get("filtre", "tous")
    if filtre == "ecarts":
        lignes = [l for l in lignes if l['a_ecart']]
    
    stats = {
        'total_recaps': recaps.count(),
        'total_demande': total_demande,
        'total_recu': total_recu,
        'total_ecart': total_ecart,
        'nb_avec_ecart': sum(1 for l in lignes if l['a_ecart']),
    }
    
    return render(request, "remboursement/rapport_ecarts.html", {
        "lignes": lignes,
        "stats": stats,
        "filtre": filtre,
        "permissions": permissions,
        "page": "rapports",
    })


# ============================================================
# EXPORTS PDF
# ============================================================

def _pdf_header(elements, titre_pdf, sous_titre):
    """Génère l'en-tête PDF standard."""
    import os
    from django.conf import settings
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image
    
    styles = getSampleStyleSheet()
    
    style_titre = ParagraphStyle(
        "Titre", parent=styles["Title"], fontSize=14,
        textColor=colors.HexColor("#123b65"), alignment=2, leading=18,
    )
    
    logo_path = os.path.join(
        settings.BASE_DIR, "core", "static", "core", "img", "logo-sagps.png"
    )
    
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=4.5 * cm, height=2 * cm)
    else:
        logo = ""
    
    titre_header = Paragraph(
        f"<b>{titre_pdf}</b><br/><font size=9>{sous_titre}</font>",
        style_titre,
    )
    
    header_table = Table([[logo, titre_header]], colWidths=[6.5 * cm, 11 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#123b65")),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.4 * cm))


def _pdf_table(data, colWidths):
    """Crée un tableau PDF standard."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    
    table = Table(data, colWidths=colWidths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    return table


@session_utilisateur_required
def remb_par_mois_pdf(request):
    """Export PDF du rapport par mois."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        return redirect("accueil")
    
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph
    
    aujourd_hui = timezone.now().date()
    try:
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        annee = aujourd_hui.year
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Rapport-remb-{annee}.pdf"'
    
    document = SimpleDocTemplate(
        response, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1 * cm, bottomMargin=1.5 * cm,
    )
    
    elements = []
    _pdf_header(elements, "RAPPORT REMBOURSEMENTS PAR MOIS", f"Année {annee}")
    elements.append(Spacer(1, 0.5 * cm))
    
    # Données
    data = [["Mois", "Bulletins", "Remboursé (DA)", "Récaps", "Montant reçu (DA)"]]
    
    for mois in range(1, 13):
        date_debut = date(annee, mois, 1)
        date_fin = date(annee, mois, monthrange(annee, mois)[1])
        
        bulletins = BulletinSoins.objects.filter(
            date_soins__gte=date_debut, date_soins__lte=date_fin,
            statut__in=['REMBOURSE', 'REVERSE'],
        )
        recaps = RecapSouscripteur.objects.filter(
            periode_debut__gte=date_debut, periode_debut__lte=date_fin,
        )
        
        nom_mois = [
            'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ][mois - 1]
        
        data.append([
            nom_mois,
            str(bulletins.count()),
            f"{float(bulletins.aggregate(t=Sum('montant_total_rembourse'))['t'] or 0):,.2f}".replace(",", " "),
            str(recaps.filter(statut='PAYE').count()),
            f"{float(recaps.aggregate(t=Sum('montant_recu'))['t'] or 0):,.2f}".replace(",", " "),
        ])
    
    elements.append(_pdf_table(data, [3 * cm, 2.5 * cm, 4 * cm, 2.5 * cm, 5 * cm]))
    elements.append(Spacer(1, 0.5 * cm))
    
    document.build(elements)
    return response


@session_utilisateur_required
def remb_par_souscripteur_pdf(request):
    """Export PDF du rapport par souscripteur."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        return redirect("accueil")
    
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Spacer
    
    aujourd_hui = timezone.now().date()
    try:
        mois = int(request.GET.get("mois", aujourd_hui.month))
        annee = int(request.GET.get("annee", aujourd_hui.year))
    except (ValueError, TypeError):
        mois = aujourd_hui.month
        annee = aujourd_hui.year
    
    date_debut = date(annee, mois, 1)
    date_fin = date(annee, mois, monthrange(annee, mois)[1])
    
    nom_mois = [
        'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
    ][mois - 1]
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Rapport-souscripteurs-{mois}-{annee}.pdf"'
    
    document = SimpleDocTemplate(
        response, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1 * cm, bottomMargin=1.5 * cm,
    )
    
    elements = []
    _pdf_header(
        elements, "RAPPORT REMBOURSEMENTS PAR SOUSCRIPTEUR",
        f"{nom_mois} {annee}"
    )
    elements.append(Spacer(1, 0.5 * cm))
    
    data = [["Souscripteur", "Bulletins", "Remboursé (DA)", "Récaps", "Montant reçu (DA)"]]
    
    for s in Souscripteur.objects.filter(statut='ACTIF').order_by('raison_sociale'):
        bulletins = BulletinSoins.objects.filter(
            souscripteur=s, date_soins__gte=date_debut, date_soins__lte=date_fin,
        )
        recaps = RecapSouscripteur.objects.filter(
            souscripteur=s, periode_debut__gte=date_debut, periode_debut__lte=date_fin,
        )
        
        nb = bulletins.count()
        if nb == 0 and recaps.count() == 0:
            continue
        
        montant_remb = bulletins.filter(
            statut__in=['REMBOURSE', 'REVERSE']
        ).aggregate(t=Sum('montant_total_rembourse'))['t'] or 0
        
        data.append([
            s.raison_sociale,
            str(nb),
            f"{float(montant_remb):,.2f}".replace(",", " "),
            str(recaps.count()),
            f"{float(recaps.aggregate(t=Sum('montant_recu'))['t'] or 0):,.2f}".replace(",", " "),
        ])
    
    elements.append(_pdf_table(data, [5 * cm, 2.5 * cm, 3.5 * cm, 2 * cm, 4 * cm]))
    document.build(elements)
    return response


@session_utilisateur_required
def remb_en_attente_pdf(request):
    """Export PDF du rapport des bulletins en attente."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        return redirect("accueil")
    
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Spacer
    
    try:
        jours = int(request.GET.get("jours", 30))
    except (ValueError, TypeError):
        jours = 30
    
    date_limite = timezone.now().date() - timedelta(days=jours)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Rapport-attente-{jours}j.pdf"'
    
    document = SimpleDocTemplate(
        response, pagesize=landscape(A4),
        rightMargin=1 * cm, leftMargin=1 * cm,
        topMargin=1 * cm, bottomMargin=1 * cm,
    )
    
    elements = []
    _pdf_header(
        elements, "BULLETINS EN ATTENTE",
        f"Depuis plus de {jours} jours (limite : {date_limite.strftime('%d/%m/%Y')})"
    )
    elements.append(Spacer(1, 0.5 * cm))
    
    bulletins = BulletinSoins.objects.filter(
        statut__in=['RECU', 'EN_VERIFICATION', 'VALIDE'],
        date_depot__date__lte=date_limite,
    ).select_related('adherent', 'souscripteur', 'patient').order_by('date_depot')
    
    data = [["N° Bulletin", "Adhérent", "Bénéficiaire", "Souscripteur", "Date dépôt", "Statut", "Montant (DA)"]]
    
    for b in bulletins:
        data.append([
            b.numero,
            b.adherent.numero_adherent,
            f"{b.patient.nom} {b.patient.prenom}"[:25],
            b.souscripteur.raison_sociale[:25],
            b.date_depot.strftime('%d/%m/%Y'),
            b.get_statut_display(),
            f"{float(b.montant_total_rembourse or 0):,.2f}".replace(",", " "),
        ])
    
    elements.append(_pdf_table(data, [2.8 * cm, 2.5 * cm, 4 * cm, 4 * cm, 2.2 * cm, 2.5 * cm, 2.5 * cm]))
    document.build(elements)
    return response


@session_utilisateur_required
def remb_echecs_pdf(request):
    """Export PDF du rapport des virements en échec."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        return redirect("accueil")
    
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Spacer
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Virements-echecs.pdf"'
    
    document = SimpleDocTemplate(
        response, pagesize=landscape(A4),
        rightMargin=1 * cm, leftMargin=1 * cm,
        topMargin=1 * cm, bottomMargin=1 * cm,
    )
    
    elements = []
    _pdf_header(elements, "VIREMENTS EN ÉCHEC", timezone.now().strftime('%d/%m/%Y'))
    elements.append(Spacer(1, 0.5 * cm))
    
    virements = VirementAdherent.objects.filter(
        statut='ECHEC'
    ).select_related('adherent').order_by('-date_creation')
    
    data = [["N° Virement", "Adhérent", "Banque", "RIB", "Montant (DA)", "Date"]]
    
    for v in virements:
        data.append([
            v.numero,
            f"{v.adherent.numero_adherent} - {v.adherent.id_personne.nom}"[:30],
            (v.banque or "—")[:20],
            (v.rib or "—")[:25],
            f"{float(v.montant):,.2f}".replace(",", " "),
            v.date_creation.strftime('%d/%m/%Y'),
        ])
    
    elements.append(_pdf_table(data, [3 * cm, 6 * cm, 3.5 * cm, 5 * cm, 3 * cm, 2.5 * cm]))
    document.build(elements)
    return response


@session_utilisateur_required
def remb_ecarts_pdf(request):
    """Export PDF du rapport des écarts récaps."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        return redirect("accueil")
    
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Spacer
    
    filtre = request.GET.get("filtre", "tous")
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Rapport-ecarts.pdf"'
    
    document = SimpleDocTemplate(
        response, pagesize=landscape(A4),
        rightMargin=1 * cm, leftMargin=1 * cm,
        topMargin=1 * cm, bottomMargin=1 * cm,
    )
    
    elements = []
    _pdf_header(elements, "ÉCARTS RÉCAPS", f"Filtre : {filtre}")
    elements.append(Spacer(1, 0.5 * cm))
    
    recaps = RecapSouscripteur.objects.filter(statut='PAYE').order_by('-periode_debut')
    
    data = [["N° Récap", "Souscripteur", "Période", "Demandé (DA)", "Reçu (DA)", "Écart (DA)"]]
    
    for r in recaps:
        ecart = float((r.montant_total or 0) - (r.montant_recu or 0))
        
        if filtre == 'ecarts' and ecart == 0:
            continue
        
        data.append([
            r.numero,
            r.souscripteur.raison_sociale[:25],
            f"{r.periode_debut.strftime('%d/%m/%Y')} → {r.periode_fin.strftime('%d/%m/%Y')}",
            f"{float(r.montant_total or 0):,.2f}".replace(",", " "),
            f"{float(r.montant_recu or 0):,.2f}".replace(",", " "),
            f"{ecart:,.2f}".replace(",", " "),
        ])
    
    elements.append(_pdf_table(data, [4 * cm, 5 * cm, 5 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm]))
    document.build(elements)
    return response