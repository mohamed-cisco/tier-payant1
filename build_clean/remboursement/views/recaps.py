# remboursement/views/recaps.py
"""Vues de gestion des récaps souscripteur."""
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.db.models import Sum

from core.models import RolePermission, Souscripteur
from core.views.dashboard import enregistrer_audit
from core.views.decorators import session_utilisateur_required

from remboursement.models import RecapSouscripteur, VirementAdherent
from remboursement.services.recap import (
    creer_recap_mensuel, recalculer_totaux_recap,
    envoyer_recap, valider_recap, enregistrer_paiement_recap,
    rejeter_recap, get_bulletins_recap,
)
from remboursement.services.virements import generer_virements_recap


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
def recaps(request):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("accueil")
    
    statut = request.GET.get("statut", "").strip()
    souscripteur_id = request.GET.get("souscripteur", "").strip()
    
    qs = RecapSouscripteur.objects.select_related("souscripteur").order_by("-periode_debut")
    
    if statut:
        qs = qs.filter(statut=statut)
    if souscripteur_id:
        qs = qs.filter(souscripteur_id=souscripteur_id)
    
    stats = {
        'total': qs.count(),
        'montant_total': qs.aggregate(t=Sum('montant_total'))['t'] or 0,
    }
    
    souscripteurs = Souscripteur.objects.filter(statut='ACTIF').order_by('raison_sociale')
    
    return render(request, "remboursement/recaps.html", {
        "recaps": qs,
        "souscripteurs": souscripteurs,
        "statut": statut,
        "souscripteur_id": souscripteur_id,
        "stats": stats,
        "permissions": permissions,
        "page": "remb_recaps",
    })

@session_utilisateur_required
def recap_detail(request, id_recap):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    recap = get_object_or_404(RecapSouscripteur, id=id_recap)
    bulletins = get_bulletins_recap(recap)
    virements = recap.virements.all().select_related(
        'adherent', 'adherent__id_personne'
    ).order_by('adherent__numero_adherent')
    
    # ============ STATS PAR STATUT DE BULLETIN ============
    stats_bulletins = {
        'total': bulletins.count(),
        'valide': bulletins.filter(statut='VALIDE').count(),
        'transmis': bulletins.filter(statut='TRANSMIS').count(),
        'rembourse': bulletins.filter(statut='REMBOURSE').count(),
        'reverse': bulletins.filter(statut='REVERSE').count(),
        'rejete': bulletins.filter(statut='REJETE').count(),
    }
    
    # ============ STATS VIREMENTS ============
    stats_virements = {
        'total': virements.count(),
        'a_payer': virements.filter(statut='A_PAYER').count(),
        'paye': virements.filter(statut='PAYE').count(),
        'echec': virements.filter(statut='ECHEC').count(),
        'montant_paye': sum((v.montant for v in virements.filter(statut='PAYE')), 0),
        'montant_a_payer': sum((v.montant for v in virements.filter(statut='A_PAYER')), 0),
    }
    
    # ============ ÉCART ============
    ecart = recap.montant_total - recap.montant_recu
    
    return render(request, "remboursement/recap_detail.html", {
        "recap": recap,
        "bulletins": bulletins,
        "virements": virements,
        "stats_bulletins": stats_bulletins,
        "stats_virements": stats_virements,
        "ecart": ecart,
        "permissions": permissions,
        "page": "remb_recaps",
    })


@session_utilisateur_required
def recap_create(request):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VALIDATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    if request.method == "POST":
        try:
            souscripteur = get_object_or_404(
                Souscripteur, id_souscripteur=request.POST.get("souscripteur")
            )
            annee = int(request.POST.get("annee"))
            mois = int(request.POST.get("mois"))
            
            recap = creer_recap_mensuel(souscripteur, annee=annee, mois=mois)
            
            messages.success(
                request,
                f"Récap {recap.numero} créé ({recap.nb_bulletins} bulletins, {recap.montant_total} DA)"
            )
            return redirect("remb_recap_detail", id_recap=recap.id)
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    souscripteurs = Souscripteur.objects.filter(statut='ACTIF').order_by('raison_sociale')
    today = timezone.now().date()
    
    return render(request, "remboursement/recap_form.html", {
        "souscripteurs": souscripteurs,
        "annee_courante": today.year,
        "mois_courant": today.month,
        "permissions": permissions,
        "page": "remb_recaps",
    })


@session_utilisateur_required
def recap_envoyer(request, id_recap):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_TRANSMIT" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    recap = get_object_or_404(RecapSouscripteur, id=id_recap)
    
    try:
        envoyer_recap(recap, utilisateur)
        messages.success(request, f"Récap {recap.numero} envoyé.")
    except Exception as e:
        messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_recap_detail", id_recap=recap.id)


@session_utilisateur_required
def recap_valider(request, id_recap):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VALIDATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    recap = get_object_or_404(RecapSouscripteur, id=id_recap)
    
    if request.method == "POST":
        reference = request.POST.get("reference", "").strip()
        try:
            valider_recap(recap, utilisateur, reference=reference)
            messages.success(request, f"Récap validé.")
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_recap_detail", id_recap=recap.id)


@session_utilisateur_required
def recap_payer(request, id_recap):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_PAY" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    recap = get_object_or_404(RecapSouscripteur, id=id_recap)
    
    if request.method == "POST":
        try:
            montant = request.POST.get("montant")
            reference = request.POST.get("reference", "").strip()
            date_paiement = request.POST.get("date_paiement") or None
            
            enregistrer_paiement_recap(
                recap, montant, utilisateur,
                reference=reference, date_paiement=date_paiement
            )
            
            # Générer les virements adhérents
            virements = generer_virements_recap(recap, utilisateur)
            
            messages.success(
                request,
                f"Paiement enregistré. {len(virements)} virement(s) généré(s)."
            )
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_recap_detail", id_recap=recap.id)


@session_utilisateur_required
def recap_rejeter(request, id_recap):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_REJECT" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    recap = get_object_or_404(RecapSouscripteur, id=id_recap)
    
    if request.method == "POST":
        motif = request.POST.get("motif", "").strip()
        try:
            rejeter_recap(recap, motif, utilisateur)
            messages.warning(request, "Récap rejeté.")
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_recap_detail", id_recap=recap.id)


@session_utilisateur_required
def recap_recalculer(request, id_recap):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VALIDATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    recap = get_object_or_404(RecapSouscripteur, id=id_recap)
    
    try:
        recalculer_totaux_recap(recap)
        messages.success(request, f"Totaux recalculés.")
    except Exception as e:
        messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_recap_detail", id_recap=recap.id)


# ============================================================
# RÉCAP DE RATTRAPAGE (période personnalisée)
# ============================================================

@session_utilisateur_required
def recap_rattrapage(request):
    """
    Crée un récap de rattrapage sur une période personnalisée.
    Inclut tous les bulletins VALIDÉS de la période.
    Utile pour rattraper un bulletin validé après l'envoi du récap mensuel.
    """
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VALIDATE" not in permissions and "REMBOURSEMENT_TRANSMIT" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("remb_recaps")
    
    from datetime import date
    from django.db.models import Q
    from core.models import Souscripteur
    from remboursement.models import BulletinSoins
    from remboursement.services.recap import recalculer_totaux_recap
    
    if request.method == "POST":
        try:
            souscripteur_id = request.POST.get("souscripteur")
            date_debut = request.POST.get("date_debut")
            date_fin = request.POST.get("date_fin")
            motif = request.POST.get("motif", "").strip()
            
            if not souscripteur_id or not date_debut or not date_fin:
                messages.error(request, "Tous les champs obligatoires doivent être remplis.")
                return redirect("remb_recap_rattrapage")
            
            souscripteur = Souscripteur.objects.get(id_souscripteur=int(souscripteur_id))
            
            # Vérifier qu'il y a des bulletins VALIDÉS dans la période
                        # Récupérer les bulletins DÉJÀ payés (avec virement PAYE)
            bulletins_deja_payes = VirementAdherent.objects.filter(
                statut='PAYE'
            ).values_list('bulletins__id', flat=True)
            
            # Récupérer les bulletins DÉJÀ dans un récap
            bulletins_deja_recap = BulletinSoins.objects.filter(
                recap__isnull=False
            ).values_list('id', flat=True)
            
            # Bulletins VALIDÉS éligibles
            bulletins = BulletinSoins.objects.filter(
                souscripteur=souscripteur,
                statut='VALIDE',
                date_soins__gte=date_debut,
                date_soins__lte=date_fin,
            ).exclude(
                id__in=bulletins_deja_payes
            ).exclude(
                id__in=bulletins_deja_recap
            )
            
            if not bulletins.exists():
                messages.warning(request, "Aucun bulletin VALIDÉ trouvé dans cette période.")
                return redirect("remb_recap_rattrapage")
            
            # Générer le numéro
            annee = date.today().year
            prefixe = f"REC-SOUS-RATT-{annee}-"
            numeros = RecapSouscripteur.objects.filter(
                numero__startswith=prefixe
            ).values_list('numero', flat=True)
            
            valeurs = []
            for num in numeros:
                try:
                    valeurs.append(int(num.rsplit('-', 1)[1]))
                except (ValueError, IndexError):
                    continue
            
            prochain = max(valeurs, default=0) + 1
            numero = f"{prefixe}{prochain:04d}"
            
            # Créer le récap
            recap = RecapSouscripteur.objects.create(
                numero=numero,
                souscripteur=souscripteur,
                periode_debut=date_debut,
                periode_fin=date_fin,
                statut='BROUILLON',
                observations=f"[RATTRAPAGE] {motif}" if motif else "[RATTRAPAGE]",
                cree_par=utilisateur,
            )
            
            # Rattacher les bulletins
            bulletins.update(recap=recap)
            
            # Recalculer les totaux
            recalculer_totaux_recap(recap)
            
            enregistrer_audit(
                request=request,
                type_action="CREATION",
                module="REMBOURSEMENT",
                table_cible="recap_souscripteur",
                id_enregistrement=recap.id,
                nouvelle_valeur=f"Récap rattrapage {recap.numero}",
                description=f"Récap de rattrapage {recap.numero} ({recap.nb_bulletins} bulletins)",
            )
            
            messages.success(
                request,
                f"✅ Récap de rattrapage {recap.numero} créé "
                f"({recap.nb_bulletins} bulletins, {recap.montant_total} DA)"
            )
            return redirect("remb_recap_detail", id_recap=recap.id)
        
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    # GET : afficher le formulaire
    souscripteurs = Souscripteur.objects.filter(statut='ACTIF').order_by('raison_sociale')
    
    # Bulletins VALIDÉS en attente de récap
    bulletins_en_attente = BulletinSoins.objects.filter(
        statut='VALIDE',
        recap__isnull=True,
    ).select_related('souscripteur', 'patient').order_by('souscripteur__raison_sociale', 'date_soins')
    
    return render(request, "remboursement/recap_rattrapage.html", {
        "souscripteurs": souscripteurs,
        "bulletins_en_attente": bulletins_en_attente,
        "permissions": permissions,
        "page": "remb_recaps",
    })


# ============================================================
# EXPORT PDF DU RÉCAP
# ============================================================

@session_utilisateur_required
def recap_pdf(request, id_recap):
    """Génère le PDF du récap pour envoi au souscripteur."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    recap = get_object_or_404(RecapSouscripteur, id=id_recap)
    bulletins = get_bulletins_recap(recap)
    
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
    
    # ============ RÉPONSE HTTP ============
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Recap-{recap.numero}.pdf"'
    
    # ============ DOCUMENT ============
    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1 * cm,
        bottomMargin=1.5 * cm,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # ============ STYLES ============
    style_titre = ParagraphStyle(
        "Titre",
        parent=styles["Title"],
        fontSize=16,
        textColor=colors.HexColor("#123b65"),
        alignment=2,
        leading=20,
    )
    
    style_section = ParagraphStyle(
        "Section",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#123b65"),
        fontName="Helvetica-Bold",
        spaceAfter=6,
        spaceBefore=10,
    )
    
    # ============ EN-TÊTE AVEC LOGO ============
    logo_path = os.path.join(
        settings.BASE_DIR, "core", "static", "core", "img", "logo-sagps.png"
    )
    
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=5 * cm, height=2.2 * cm)
    else:
        logo = ""
    
    titre_header = Paragraph(
        "<b>RÉCAP SOUSCRIPTEUR</b><br/>"
        "<font size=10>Djazair Med - Tiers Payant</font>",
        style_titre,
    )
    
    header_table = Table([[logo, titre_header]], colWidths=[7 * cm, 10 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#123b65")),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.4 * cm))
    
    # ============ INFOS DU RÉCAP ============
    infos_data = [
        ["N° Récap", recap.numero],
        ["Souscripteur", recap.souscripteur.raison_sociale],
        ["Période", f"{recap.periode_debut.strftime('%d/%m/%Y')} → {recap.periode_fin.strftime('%d/%m/%Y')}"],
        ["Date d'émission", recap.date_creation.strftime("%d/%m/%Y")],
        ["Statut", recap.get_statut_display()],
        ["Nb bulletins", str(recap.nb_bulletins)],
        ["Nb adhérents", str(recap.nb_adherents)],
    ]
    
    infos_table = Table(infos_data, colWidths=[4 * cm, 13 * cm])
    infos_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (0, -1), 9),
        ("FONTSIZE", (1, 0), (1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#123b65")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(infos_table)
    elements.append(Spacer(1, 0.5 * cm))
    
    # ============ DÉTAIL DES BULLETINS ============
    elements.append(Paragraph("DÉTAIL DES BULLETINS", style_section))
    
    bulletins_data = [
        ["N° Bulletin", "Adhérent", "Bénéficiaire", "Date soins", "Remboursé (DA)"]
    ]
    
    total = 0
    for b in bulletins:
        montant = b.montant_total_rembourse or 0
        total += montant
        
        bulletins_data.append([
            b.numero,
            b.adhesion.id_adherent.numero_adherent,
            f"{b.patient.nom} {b.patient.prenom}",
            b.date_soins.strftime("%d/%m/%Y"),
            f"{montant:,.2f}".replace(",", " "),
        ])
    
    # Ligne TOTAL
    bulletins_data.append([
        "", "", "", "TOTAL",
        f"{total:,.2f}".replace(",", " ")
    ])
    
    bulletins_table = Table(
        bulletins_data,
        colWidths=[3.2 * cm, 3 * cm, 4 * cm, 2.8 * cm, 4 * cm],
        repeatRows=1,
    )
    bulletins_table.setStyle(TableStyle([
        # En-tête
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123b65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        
        # Corps
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        
        # Dernière ligne (TOTAL)
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eaf2fb")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#123b65")),
        ("FONTSIZE", (0, -1), (-1, -1), 10),
        
        # Bordures
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(bulletins_table)
    elements.append(Spacer(1, 0.5 * cm))
    
    # ============ RÉCAPITULATIF FINANCIER ============
    elements.append(Paragraph("RÉCAPITULATIF FINANCIER", style_section))
    
    recap_fin_data = [
        ["Montant total demandé", f"{recap.montant_total:,.2f} DA".replace(",", " ")],
        ["Montant reçu du souscripteur", f"{recap.montant_recu:,.2f} DA".replace(",", " ")],
        ["Écart", f"{(recap.montant_total - recap.montant_recu):,.2f} DA".replace(",", " ")],
    ]
    
    recap_fin_table = Table(recap_fin_data, colWidths=[10 * cm, 7 * cm])
    recap_fin_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#123b65")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
    ]))
    elements.append(recap_fin_table)
    elements.append(Spacer(1, 1 * cm))
    
    # ============ PIED : SIGNATURES ============
    pied_data = [[
        Paragraph("<b>Signature SAGPS</b>", styles["Normal"]),
        Paragraph(
            f"<b>Cachet et visa du souscripteur</b>",
            ParagraphStyle("right", parent=styles["Normal"], alignment=2),
        ),
    ]]
    pied_table = Table(pied_data, colWidths=[8.5 * cm, 8.5 * cm])
    pied_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
    ]))
    elements.append(pied_table)
    
    # ============ CONSTRUCTION ============
    document.build(elements)
    return response


# ============================================================
# EXPORT EXCEL DU RÉCAP
# ============================================================

@session_utilisateur_required
def recap_excel(request, id_recap):
    """Génère l'Excel du récap pour analyse."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_recaps")
    
    recap = get_object_or_404(RecapSouscripteur, id=id_recap)
    bulletins = get_bulletins_recap(recap)
    
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from django.http import HttpResponse
    
    # ============ WORKBOOK ============
    workbook = openpyxl.Workbook()
    feuille = workbook.active
    feuille.title = f"Recap-{recap.numero}"
    
    # ============ STYLES ============
    bleu_fonce = "123B65"
    bleu_clair = "EAF2FB"
    
    style_titre = Font(bold=True, size=14, color=bleu_fonce)
    style_entete = Font(bold=True, size=10, color="FFFFFF")
    style_total = Font(bold=True, size=10, color=bleu_fonce)
    
    fill_entete = PatternFill("solid", fgColor=bleu_fonce)
    fill_total = PatternFill("solid", fgColor=bleu_clair)
    
    align_centre = Alignment(horizontal="center", vertical="center")
    align_droite = Alignment(horizontal="right", vertical="center")
    
    border_thin = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )
    
    # ============ TITRE ============
    feuille.merge_cells("A1:F1")
    titre_cell = feuille["A1"]
    titre_cell.value = f"RÉCAP SOUSCRIPTEUR - {recap.numero}"
    titre_cell.font = style_titre
    titre_cell.alignment = align_centre
    
    # ============ INFOS ============
    feuille["A3"] = "Souscripteur"
    feuille["B3"] = recap.souscripteur.raison_sociale
    feuille["A4"] = "Période"
    feuille["B4"] = f"{recap.periode_debut.strftime('%d/%m/%Y')} → {recap.periode_fin.strftime('%d/%m/%Y')}"
    feuille["A5"] = "Statut"
    feuille["B5"] = recap.get_statut_display()
    feuille["A6"] = "Nb bulletins"
    feuille["B6"] = recap.nb_bulletins
    feuille["A7"] = "Nb adhérents"
    feuille["B7"] = recap.nb_adherents
    
    for cell in ["A3", "A4", "A5", "A6", "A7"]:
        feuille[cell].font = Font(bold=True)
    
    # ============ TABLEAU BULLETINS ============
    ligne_depart = 9
    
    entetes = [
        "N° Bulletin",
        "Adhérent",
        "Bénéficiaire",
        "Date soins",
        "Facturé (DA)",
        "Remboursé (DA)",
    ]
    
    for col_num, entete in enumerate(entetes, 1):
        cell = feuille.cell(row=ligne_depart, column=col_num)
        cell.value = entete
        cell.font = style_entete
        cell.fill = fill_entete
        cell.alignment = align_centre
        cell.border = border_thin
    
    # ============ DONNÉES ============
    total_facture = 0
    total_rembourse = 0
    
    for idx, b in enumerate(bulletins, start=1):
        ligne = ligne_depart + idx
        
        facture = float(b.montant_total_facture or 0)
        rembourse = float(b.montant_total_rembourse or 0)
        total_facture += facture
        total_rembourse += rembourse
        
        feuille.cell(row=ligne, column=1, value=b.numero).border = border_thin
        feuille.cell(row=ligne, column=2, value=b.adhesion.id_adherent.numero_adherent).border = border_thin
        feuille.cell(row=ligne, column=3, value=f"{b.patient.nom} {b.patient.prenom}").border = border_thin
        feuille.cell(row=ligne, column=4, value=b.date_soins.strftime("%d/%m/%Y")).border = border_thin
        feuille.cell(row=ligne, column=5, value=facture).border = border_thin
        feuille.cell(row=ligne, column=6, value=rembourse).border = border_thin
        
        feuille.cell(row=ligne, column=5).number_format = '#,##0.00'
        feuille.cell(row=ligne, column=6).number_format = '#,##0.00'
    
    # ============ TOTAL ============
    ligne_total = ligne_depart + len(bulletins) + 1
    
    feuille.cell(row=ligne_total, column=1, value="")
    feuille.cell(row=ligne_total, column=4, value="TOTAL")
    feuille.cell(row=ligne_total, column=5, value=total_facture)
    feuille.cell(row=ligne_total, column=6, value=total_rembourse)
    
    for col in range(1, 7):
        cell = feuille.cell(row=ligne_total, column=col)
        cell.font = style_total
        cell.fill = fill_total
        cell.border = border_thin
    
    feuille.cell(row=ligne_total, column=5).number_format = '#,##0.00'
    feuille.cell(row=ligne_total, column=6).number_format = '#,##0.00'
    
    # ============ LARGEURS ============
    largeurs = [16, 14, 25, 12, 14, 16]
    for i, largeur in enumerate(largeurs, 1):
        feuille.column_dimensions[chr(64 + i)].width = largeur
    
    # ============ RÉPONSE ============
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Recap-{recap.numero}.xlsx"'
    
    workbook.save(response)
    return response