# core/views/champs.py
"""
Vues de gestion des champs personnalisés.

Fonctions :
- champs_personnalises : liste des champs
- champ_personnalise_create : créer un champ
- champ_personnalise_modifier : modifier un champ
- champ_personnalise_supprimer : désactiver un champ
- get_champs_pour_entite : helper
- get_valeur_champ : helper
- sauvegarder_valeurs_champs : helper
- get_valeurs_champs_entite : helper
"""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from core.forms import ChampPersonnaliseForm
from core.models import (
    ChampPersonnalise,
    RolePermission,
    ValeurChampPersonnalise,
)


def champs_personnalises(request):
    """Liste des champs personnalisés."""
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

    if "USER_VIEW" not in permissions and "ROLE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les champs personnalisés."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    entite_filtre = request.GET.get("entite", "").strip()

    champs = ChampPersonnalise.objects.all().order_by(
        "entite", "ordre_affichage", "id"
    )

    if recherche:
        champs = champs.filter(
            Q(libelle__icontains=recherche)
            | Q(nom_technique__icontains=recherche)
        )

    if entite_filtre:
        champs = champs.filter(entite=entite_filtre)

    return render(
        request,
        "core/champs_personnalises.html",
        {
            "champs": champs,
            "recherche": recherche,
            "entite_filtre": entite_filtre,
            "entites": ChampPersonnalise.ENTITES,
            "permissions": permissions,
            "page": "champs_personnalises",
        }
    )


def champ_personnalise_create(request):
    """Créer un nouveau champ personnalisé."""
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

    if "USER_CREATE" not in permissions and "ROLE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un champ personnalisé."
        )
        return redirect("champs_personnalises")

    if request.method == "POST":
        form = ChampPersonnaliseForm(request.POST)

        if form.is_valid():
            try:
                champ = form.save()

                from core.views_old import enregistrer_audit
                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="CHAMP PERSONNALISE",
                    table_cible="champ_personnalise",
                    id_enregistrement=champ.pk,
                    nouvelle_valeur=(
                        f"{champ.get_entite_display()} → "
                        f"{champ.libelle} ({champ.nom_technique})"
                    ),
                    description=(
                        f"Création du champ personnalisé "
                        f"{champ.libelle}"
                    ),
                )

                messages.success(
                    request,
                    f"Champ personnalisé « {champ.libelle} » créé avec succès."
                )
                return redirect("champs_personnalises")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )
    else:
        form = ChampPersonnaliseForm()

    return render(
        request,
        "core/champ_personnalise_form.html",
        {
            "form": form,
            "titre": "Nouveau champ personnalisé",
            "permissions": permissions,
            "page": "champs_personnalises",
        }
    )


def champ_personnalise_modifier(request, id_champ):
    """Modifier un champ personnalisé existant."""
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

    if "USER_UPDATE" not in permissions and "ROLE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un champ personnalisé."
        )
        return redirect("champs_personnalises")

    try:
        champ = ChampPersonnalise.objects.get(pk=id_champ)
    except ChampPersonnalise.DoesNotExist:
        messages.error(request, "Champ personnalisé introuvable.")
        return redirect("champs_personnalises")

    if request.method == "POST":
        form = ChampPersonnaliseForm(request.POST, instance=champ)

        if form.is_valid():
            try:
                ancienne_valeur = (
                    f"{champ.get_entite_display()} → "
                    f"{champ.libelle} ({champ.nom_technique})"
                )

                champ = form.save()

                nouvelle_valeur = (
                    f"{champ.get_entite_display()} → "
                    f"{champ.libelle} ({champ.nom_technique})"
                )

                from core.views_old import enregistrer_audit
                enregistrer_audit(
                    request=request,
                    type_action="MODIFICATION",
                    module="CHAMP PERSONNALISE",
                    table_cible="champ_personnalise",
                    id_enregistrement=champ.pk,
                    ancienne_valeur=ancienne_valeur,
                    nouvelle_valeur=nouvelle_valeur,
                    description=(
                        f"Modification du champ personnalisé "
                        f"{champ.libelle}"
                    ),
                )

                messages.success(
                    request,
                    f"Champ personnalisé « {champ.libelle} » modifié avec succès."
                )
                return redirect("champs_personnalises")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )
    else:
        form = ChampPersonnaliseForm(instance=champ)

    return render(
        request,
        "core/champ_personnalise_form.html",
        {
            "form": form,
            "titre": f"Modifier « {champ.libelle} »",
            "champ": champ,
            "permissions": permissions,
            "page": "champs_personnalises",
        }
    )


def champ_personnalise_supprimer(request, id_champ):
    """Désactiver un champ personnalisé (radiation logique)."""
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

    if "USER_UPDATE" not in permissions and "ROLE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de désactiver un champ personnalisé."
        )
        return redirect("champs_personnalises")

    try:
        champ = ChampPersonnalise.objects.get(pk=id_champ)
    except ChampPersonnalise.DoesNotExist:
        messages.error(request, "Champ personnalisé introuvable.")
        return redirect("champs_personnalises")

    if request.method == "POST":
        try:
            ancienne_valeur = f"Statut : {champ.statut}"

            champ.statut = "INACTIF"
            champ.save()

            from core.views_old import enregistrer_audit
            enregistrer_audit(
                request=request,
                type_action="DESACTIVATION",
                module="CHAMP PERSONNALISE",
                table_cible="champ_personnalise",
                id_enregistrement=champ.pk,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur="Statut : INACTIF",
                description=(
                    f"Désactivation du champ personnalisé "
                    f"{champ.libelle}"
                ),
            )

            messages.success(
                request,
                f"Champ personnalisé « {champ.libelle} » désactivé."
            )
        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la désactivation : {e}"
            )

    return redirect("champs_personnalises")


# ============================================================
# FONCTIONS UTILITAIRES POUR LES CHAMPS PERSONNALISÉS
# ============================================================

def get_champs_pour_entite(entite):
    """Récupère la liste des champs actifs pour une entité."""
    return ChampPersonnalise.objects.filter(
        entite=entite,
        statut="ACTIF",
    ).order_by("ordre_affichage", "id")


def get_valeur_champ(champ, id_enregistrement):
    """Récupère la valeur d'un champ pour un enregistrement."""
    try:
        return ValeurChampPersonnalise.objects.get(
            champ=champ,
            id_enregistrement=id_enregistrement,
        ).valeur
    except ValeurChampPersonnalise.DoesNotExist:
        return None


def sauvegarder_valeurs_champs(request, entite, id_enregistrement):
    """Sauvegarde toutes les valeurs des champs personnalisés d'une entité."""
    champs = get_champs_pour_entite(entite)

    for champ in champs:
        valeur = request.POST.get(f"champ_{champ.pk}", "").strip()

        if champ.obligatoire and not valeur:
            continue

        if valeur:
            ValeurChampPersonnalise.objects.update_or_create(
                champ=champ,
                id_enregistrement=id_enregistrement,
                defaults={"valeur": valeur},
            )
        else:
            ValeurChampPersonnalise.objects.filter(
                champ=champ,
                id_enregistrement=id_enregistrement,
            ).delete()


def get_valeurs_champs_entite(entite, id_enregistrement):
    """Récupère toutes les valeurs des champs pour un enregistrement."""
    champs = get_champs_pour_entite(entite)
    resultat = []

    for champ in champs:
        valeur = get_valeur_champ(champ, id_enregistrement)
        resultat.append({
            "champ": champ,
            "valeur": valeur if valeur is not None else (champ.valeur_defaut or ""),
        })

    return resultat