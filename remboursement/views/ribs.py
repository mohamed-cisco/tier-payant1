# remboursement/views/ribs.py
"""Vue de gestion des coordonnées bancaires des adhérents."""
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404

from core.models import (
    Adherent, CoordonneesBancaires, RolePermission
)
from core.views.dashboard import enregistrer_audit
from core.views.decorators import session_utilisateur_required


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
def ribs_manquants(request):
    """Liste des adhérents sans coordonnées bancaires."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions and "ADHERENT_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")
    
    # Adhérents SANS RIB
    ribs_existants = CoordonneesBancaires.objects.values_list('adherent_id', flat=True)
    
    sans_rib = Adherent.objects.filter(
        statut='ACTIF'
    ).exclude(
        id_adherent__in=ribs_existants
    ).select_related('id_personne').order_by('numero_adherent')
    
    # Adhérents AVEC RIB
    avec_rib = CoordonneesBancaires.objects.select_related(
        'adherent', 'adherent__id_personne'
    ).order_by('adherent__numero_adherent')
    
    return render(request, "remboursement/ribs.html", {
        "sans_rib": sans_rib,
        "avec_rib": avec_rib,
        "nb_sans_rib": sans_rib.count(),
        "nb_avec_rib": avec_rib.count(),
        "permissions": permissions,
        "page": "remb_ribs",
    })


@session_utilisateur_required
def rib_ajouter(request, id_adherent):
    """Ajoute un RIB pour un adhérent."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions and "ADHERENT_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("remb_ribs_manquants")
    
    adherent = get_object_or_404(Adherent, id_adherent=id_adherent)
    
    if request.method == "POST":
        try:
            type_compte = request.POST.get("type_compte", "CCP")
            banque = request.POST.get("banque", "").strip()
            rib = request.POST.get("rib", "").strip()
            titulaire = request.POST.get("titulaire", "").strip()
            
            if not rib or len(rib) < 10:
                messages.error(request, "Le RIB est obligatoire (au moins 10 caractères).")
                return redirect("remb_rib_ajouter", id_adherent=adherent.id_adherent)
            
            # Vérifier si existe déjà
            cb, created = CoordonneesBancaires.objects.update_or_create(
                adherent=adherent,
                defaults={
                    'type_compte': type_compte,
                    'banque': banque,
                    'rib': rib,
                    'titulaire': titulaire,
                    'valide': True,
                }
            )
            
            enregistrer_audit(
                request=request,
                type_action="MODIFICATION",
                module="REMBOURSEMENT",
                table_cible="coordonnees_bancaires",
                id_enregistrement=cb.id,
                nouvelle_valeur=f"RIB ajouté pour {adherent.numero_adherent}",
                description=f"Ajout RIB adhérent {adherent.numero_adherent}",
            )
            
            messages.success(request, f"✅ RIB ajouté pour {adherent.numero_adherent}.")
            return redirect("remb_ribs_manquants")
        
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    return render(request, "remboursement/rib_form.html", {
        "adherent": adherent,
        "permissions": permissions,
        "page": "remb_ribs",
    })


@session_utilisateur_required
def rib_modifier(request, id_rib):
    """Modifie un RIB existant."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions and "ADHERENT_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("remb_ribs_manquants")
    
    cb = get_object_or_404(CoordonneesBancaires, id=id_rib)
    adherent = cb.adherent
    
    if request.method == "POST":
        try:
            cb.type_compte = request.POST.get("type_compte", "CCP")
            cb.banque = request.POST.get("banque", "").strip()
            cb.rib = request.POST.get("rib", "").strip()
            cb.titulaire = request.POST.get("titulaire", "").strip()
            cb.valide = True
            cb.save()
            
            messages.success(request, f"✅ RIB modifié pour {adherent.numero_adherent}.")
            return redirect("remb_ribs_manquants")
        
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    return render(request, "remboursement/rib_form.html", {
        "adherent": adherent,
        "coordonnees": cb,
        "permissions": permissions,
        "page": "remb_ribs",
    })


@session_utilisateur_required
def rib_supprimer(request, id_rib):
    """Supprime un RIB."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    if "REMBOURSEMENT_VIEW" not in permissions and "ADHERENT_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("remb_ribs_manquants")
    
    cb = get_object_or_404(CoordonneesBancaires, id=id_rib)
    num = cb.adherent.numero_adherent
    cb.delete()
    
    messages.success(request, f"RIB supprimé pour {num}.")
    return redirect("remb_ribs_manquants")