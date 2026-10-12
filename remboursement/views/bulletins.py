# remboursement/views/bulletins.py
"""Vues de gestion des bulletins de soins."""
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from datetime import date

from core.models import (
    Adherent, Personne, Prestataire, Acte, SousActe,
    Contrat, Souscripteur, Adhesion, RolePermission,
)
from core.views.dashboard import enregistrer_audit
from core.views.decorators import session_utilisateur_required

from remboursement.models import (
    BulletinSoins, LigneBulletin, PieceJointe
)
from remboursement.services.moteur import calculer_bulletin


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


def _generer_numero_bulletin():
    annee = timezone.now().year
    prefixe = f"BS-{annee}-"
    numeros = BulletinSoins.objects.filter(
        numero__startswith=prefixe
    ).values_list("numero", flat=True)
    
    valeurs = []
    for num in numeros:
        try:
            valeurs.append(int(num.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    
    prochain = max(valeurs, default=0) + 1
    numero = f"{prefixe}{prochain:04d}"
    while BulletinSoins.objects.filter(numero=numero).exists():
        prochain += 1
        numero = f"{prefixe}{prochain:04d}"
    return numero


# ============================================================
# LISTE
# ============================================================

@session_utilisateur_required
def bulletins(request):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("accueil")
    
    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()
    souscripteur_id = request.GET.get("souscripteur", "").strip()
    
    qs = BulletinSoins.objects.select_related(
        "patient", "contrat", "souscripteur", "adhesion"
    ).order_by("-date_depot")
    
    if recherche:
        qs = qs.filter(
            Q(numero__icontains=recherche)
            | Q(patient__nom__icontains=recherche)
            | Q(patient__prenom__icontains=recherche)
            | Q(adhesion__id_adherent__numero_adherent__icontains=recherche)
        )
    if statut:
        qs = qs.filter(statut=statut)
    if souscripteur_id:
        qs = qs.filter(souscripteur_id=souscripteur_id)
    
    stats = {
        'total': qs.count(),
        'montant_total': qs.aggregate(t=Sum('montant_total_rembourse'))['t'] or 0,
    }
    
    souscripteurs = Souscripteur.objects.filter(statut='ACTIF').order_by('raison_sociale')
    
    return render(request, "remboursement/bulletins_soins.html", {
        "bulletins": qs,
        "souscripteurs": souscripteurs,
        "recherche": recherche,
        "statut": statut,
        "souscripteur_id": souscripteur_id,
        "stats": stats,
        "permissions": permissions,
        "page": "remb_bulletins",
    })


# ============================================================
# DÉTAIL
# ============================================================

@session_utilisateur_required
def bulletin_detail(request, id_bulletin):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    bulletin = get_object_or_404(BulletinSoins, id=id_bulletin)
    lignes = bulletin.lignes.select_related("acte", "prestataire", "garantie_acte_utilisee").all()
    pieces = bulletin.pieces_jointes.all()
    
    return render(request, "remboursement/bulletin_soin_detail.html", {
        "bulletin": bulletin,
        "lignes": lignes,
        "pieces": pieces,
        "permissions": permissions,
        "page": "remb_bulletins",
    })


# ============================================================
# CRÉATION
# ============================================================

@session_utilisateur_required
def bulletin_create(request):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_CREATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    if request.method == "POST":
        try:
            with transaction.atomic():
                adhesion = get_object_or_404(
                    Adhesion, id_adhesion=request.POST.get("id_adhesion")
                )
                patient = get_object_or_404(
                    Personne, id_personne=request.POST.get("id_patient")
                )
                contrat = adhesion.id_contrat
                
                bulletin = BulletinSoins.objects.create(
                    numero=_generer_numero_bulletin(),
                    adhesion=adhesion,
                    patient=patient,
                    lien_patient=request.POST.get("lien_patient", "ASSURE"),
                    contrat=contrat,
                    souscripteur=contrat.id_souscripteur,
                    date_soins=request.POST.get("date_soins"),
                    deposant_type=request.POST.get("deposant_type", "ADHERENT"),
                    deposant_user=utilisateur,
                    saisi_par=utilisateur,
                    date_saisie=timezone.now(),
                    statut="RECU",
                )
                
                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="REMBOURSEMENT",
                    table_cible="bulletin_soins",
                    id_enregistrement=bulletin.id,
                    nouvelle_valeur=f"Bulletin {bulletin.numero}",
                    description=f"Création du bulletin {bulletin.numero}",
                )
                
                messages.success(request, f"Bulletin {bulletin.numero} créé.")
                return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)
        
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    # ========== DONNÉES POUR LE FORMULAIRE ==========
    from core.models import AyantDroit
    
    adhesions = Adhesion.objects.filter(
        statut='ACTIF'
    ).select_related(
        'id_adherent', 'id_adherent__id_personne', 'id_contrat'
    ).order_by('id_adherent__numero_adherent')
    
    patients_par_adhesion = {}
    for a in adhesions:
        patients = [(
    a.id_adherent.id_personne_id,
    f"{a.id_adherent.id_personne.nom} {a.id_adherent.id_personne.prenom}",
    'ASSURE'
)]
        
        for ad in AyantDroit.objects.filter(
            id_adherent=a.id_adherent, statut='ACTIF'
        ).select_related('id_personne'):
            lien = 'CONJOINT' if ad.type_lien == 'CONJOINT' else (
                    'ENFANT' if ad.type_lien == 'ENFANT' else 'ASCENDANT')
            
        
        patients_par_adhesion[a.id_adhesion] = patients
    
    return render(request, "remboursement/bulletin_soin_form.html", {
        "adhesions": adhesions,
        "patients_par_adhesion": patients_par_adhesion,
        "titre": "Nouveau bulletin",
        "permissions": permissions,
        "page": "remb_bulletins",
    })
    
    


# ============================================================
# AJOUT LIGNE
# ============================================================

@session_utilisateur_required
def ligne_create(request, id_bulletin):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_CREATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    bulletin = get_object_or_404(BulletinSoins, id=id_bulletin)
    
    if bulletin.statut not in ["RECU", "EN_VERIFICATION", "VALIDE"]:
        messages.error(request, "Bulletin non modifiable.")
        return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)
    
    if request.method == "POST":
        try:
            with transaction.atomic():
                acte = get_object_or_404(Acte, id_acte=request.POST.get("id_acte"))
                prestataire = get_object_or_404(
                    Prestataire, id_prestataire=request.POST.get("id_prestataire")
                )
                
                sous_acte_id = request.POST.get("id_sous_acte")
                sous_acte = None
                if sous_acte_id:
                    sous_acte = SousActe.objects.filter(id_sous_acte=sous_acte_id).first()
                
                quantite = int(request.POST.get("quantite", 1))
                montant_unitaire = request.POST.get("montant_unitaire")
                montant_total = float(montant_unitaire) * quantite
                
                ligne = LigneBulletin.objects.create(
                    bulletin=bulletin,
                    section=request.POST.get("section", "A"),
                    date_acte=request.POST.get("date_acte"),
                    acte=acte,
                    sous_acte=sous_acte,
                    prestataire=prestataire,
                    quantite=quantite,
                    montant_unitaire=montant_unitaire,
                    montant_total=montant_total,
                    type_vignette=request.POST.get("type_vignette", "AUCUNE"),
                )
                
                # Recalculer tout le bulletin
                calculer_bulletin(bulletin)
                
                messages.success(request, "Ligne ajoutée.")
                return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)
        
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    actes = Acte.objects.filter(statut='ACTIF').order_by('code_acte')
    prestataires = Prestataire.objects.filter(statut='ACTIF').order_by('raison_sociale')
    
    return render(request, "remboursement/ligne_bulletin_form.html", {
        "bulletin": bulletin,
        "actes": actes,
        "prestataires": prestataires,
        "permissions": permissions,
        "page": "remb_bulletins",
    })


# ============================================================
# SUPPRESSION LIGNE
# ============================================================

@session_utilisateur_required
def ligne_delete(request, id_ligne):
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_UPDATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    ligne = get_object_or_404(LigneBulletin, id=id_ligne)
    bulletin = ligne.bulletin
    
    if bulletin.statut not in ["RECU", "EN_VERIFICATION"]:
        messages.error(request, "Bulletin non modifiable.")
        return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)
    
    ligne.delete()
    calculer_bulletin(bulletin)
    
    messages.success(request, "Ligne supprimée.")
    return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)