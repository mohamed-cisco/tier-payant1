# remboursement/views/validation.py
"""Vues de workflow des bulletins."""
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404

from core.models import RolePermission
from core.views.dashboard import enregistrer_audit
from core.views.decorators import session_utilisateur_required

from remboursement.models import BulletinSoins
from remboursement.services.workflow import (
    valider_bulletin, controler_bulletin, transmettre_bulletin,
    rejeter_bulletin, reactiver_bulletin, WorkflowError,
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


@session_utilisateur_required
def valider(request, id_bulletin):
    """RECU → EN_VERIFICATION avec calcul."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VALIDATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    bulletin = get_object_or_404(BulletinSoins, id=id_bulletin)
    
    try:
        valider_bulletin(bulletin, utilisateur)
        
        enregistrer_audit(
            request=request,
            type_action="VALIDATION",
            module="REMBOURSEMENT",
            table_cible="bulletin_soins",
            id_enregistrement=bulletin.id,
            nouvelle_valeur="EN_VERIFICATION",
            description=f"Élaboration bulletin {bulletin.numero}",
        )
        messages.success(request, f"Bulletin élaboré. Remboursement : {bulletin.montant_total_rembourse} DA")
    except WorkflowError as e:
        messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)


@session_utilisateur_required
def recalculer(request, id_bulletin):
    """Recalcule un bulletin."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VALIDATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    bulletin = get_object_or_404(BulletinSoins, id=id_bulletin)
    
    try:
        calculer_bulletin(bulletin)
        messages.success(request, f"Recalcul effectué : {bulletin.montant_total_rembourse} DA")
    except Exception as e:
        messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)


@session_utilisateur_required
def controler(request, id_bulletin):
    """EN_VERIFICATION → VALIDE."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VALIDATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    bulletin = get_object_or_404(BulletinSoins, id=id_bulletin)
    
    try:
        controler_bulletin(bulletin, utilisateur)
        enregistrer_audit(
            request=request,
            type_action="VALIDATION",
            module="REMBOURSEMENT",
            table_cible="bulletin_soins",
            id_enregistrement=bulletin.id,
            nouvelle_valeur="VALIDE",
            description=f"Contrôle bulletin {bulletin.numero}",
        )
        messages.success(request, "Bulletin contrôlé et validé.")
    except WorkflowError as e:
        messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)


@session_utilisateur_required
def rejeter(request, id_bulletin):
    """Rejette un bulletin."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_REJECT" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    bulletin = get_object_or_404(BulletinSoins, id=id_bulletin)
    
    if request.method == "POST":
        motif = request.POST.get("motif", "").strip()
        try:
            rejeter_bulletin(bulletin, motif, utilisateur)
            messages.warning(request, f"Bulletin rejeté.")
        except WorkflowError as e:
            messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)


@session_utilisateur_required
def reactiver(request, id_bulletin):
    """REJETE → RECU."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VALIDATE" not in permissions:
        messages.error(request, "Accès refusé.")
        return redirect("remb_bulletins")
    
    bulletin = get_object_or_404(BulletinSoins, id=id_bulletin)
    
    try:
        reactiver_bulletin(bulletin, utilisateur)
        messages.success(request, "Bulletin réactivé.")
    except WorkflowError as e:
        messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_bulletin_detail", id_bulletin=bulletin.id)