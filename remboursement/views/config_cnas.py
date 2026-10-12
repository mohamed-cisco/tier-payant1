# remboursement/views/config_cnas.py
"""Vue de configuration CNAS paramétrable."""
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect, render

from core.models import ConfigCNAS, TypePrestation, RolePermission
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
def config_cnas(request):
    """Configuration des forfaits et taux CNAS."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    # ✅ CORRECTION : seul CONFIG_CNAS_VIEW donne accès
    if "CONFIG_CNAS_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à la configuration CNAS.")
        return redirect("remb_dashboard")
    
    if request.method == "POST":
        # ✅ CORRECTION : seul CONFIG_CNAS_UPDATE permet de modifier
        if "CONFIG_CNAS_UPDATE" not in permissions:
            messages.error(request, "Vous n'avez pas l'autorisation de modifier la configuration CNAS.")
            return redirect("remb_config_cnas")
        
        try:
            configs = ConfigCNAS.objects.all()
            modifications = 0
            
            for config in configs:
                forfait_key = f"forfait_{config.pk}"
                taux_key = f"taux_{config.pk}"
                actif_key = f"actif_{config.pk}"
                
                if forfait_key in request.POST:
                    nouveau_forfait = request.POST.get(forfait_key, "0").strip() or "0"
                    nouveau_taux = request.POST.get(taux_key, "0").strip() or "0"
                    est_actif = actif_key in request.POST
                    
                    try:
                        nouveau_forfait = Decimal(nouveau_forfait)
                    except Exception:
                        nouveau_forfait = Decimal("0")
                    try:
                        nouveau_taux = Decimal(nouveau_taux)
                    except Exception:
                        nouveau_taux = Decimal("0")
                    
                    if (config.forfait != nouveau_forfait 
                        or config.taux_pourcentage != nouveau_taux
                        or config.actif != est_actif):
                        
                        config.forfait = nouveau_forfait
                        config.taux_pourcentage = nouveau_taux
                        config.actif = est_actif
                        config.save()
                        modifications += 1
            
            if "ajouter_config" in request.POST:
                type_prestation_id = request.POST.get("nouveau_type_prestation")
                if type_prestation_id:
                    try:
                        tp = TypePrestation.objects.get(id_type_prestation=int(type_prestation_id))
                        if not ConfigCNAS.objects.filter(type_prestation=tp).exists():
                            ConfigCNAS.objects.create(
                                type_prestation=tp,
                                forfait=Decimal(request.POST.get("nouveau_forfait", "0") or "0"),
                                taux_pourcentage=Decimal(request.POST.get("nouveau_taux", "0") or "0"),
                                actif=True,
                            )
                            modifications += 1
                    except Exception as e:
                        messages.error(request, f"Erreur ajout : {e}")
            
            if modifications > 0:
                enregistrer_audit(
                    request=request,
                    type_action="MODIFICATION",
                    module="REMBOURSEMENT",
                    table_cible="config_cnas",
                    id_enregistrement=0,
                    nouvelle_valeur=f"{modifications} configurations modifiées",
                    description=f"Mise à jour config CNAS ({modifications})",
                )
                messages.success(request, f"{modifications} configuration(s) mise(s) à jour.")
            else:
                messages.info(request, "Aucune modification détectée.")
            
            return redirect("remb_config_cnas")
        
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
    
    configs = ConfigCNAS.objects.all().select_related('type_prestation').order_by('type_prestation__libelle')
    
    types_sans_config = TypePrestation.objects.filter(
        statut='ACTIF',
        config_cnas__isnull=True
    ).order_by('libelle')
    
    return render(request, "remboursement/config_cnas.html", {
        "configs": configs,
        "types_sans_config": types_sans_config,
        "permissions": permissions,
        "page": "remb_config_cnas",
    })


@session_utilisateur_required
def config_cnas_supprimer(request, id_config):
    """Supprime une configuration CNAS."""
    utilisateur = request.utilisateur
    permissions = _get_permissions(utilisateur.id_utilisateur)
    
    # ✅ CORRECTION : seul CONFIG_CNAS_UPDATE permet de supprimer
    if "CONFIG_CNAS_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de supprimer une configuration CNAS.")
        return redirect("remb_config_cnas")
    
    try:
        config = ConfigCNAS.objects.get(pk=id_config)
        libelle = config.type_prestation.libelle
        config.delete()
        messages.success(request, f"Configuration '{libelle}' supprimée.")
    except ConfigCNAS.DoesNotExist:
        messages.error(request, "Configuration introuvable.")
    except Exception as e:
        messages.error(request, f"Erreur : {e}")
    
    return redirect("remb_config_cnas")