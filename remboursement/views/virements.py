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