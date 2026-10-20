# core/views/plafonds.py
"""
Vues de gestion des plafonds.

Fonctions :
- plafonds : liste des plafonds
- plafond_create : créer un plafond
- plafond_modifier : modifier un plafond
- plafond_desactiver : désactiver un plafond
"""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from core.forms import PlafondForm
from core.models import (
    GarantieActe,
    Plafond,
    RolePermission,
)
from core.views.dashboard import enregistrer_audit


def plafond_create(request):
    """Créer un nouveau plafond."""
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

    if "PLAFOND_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un plafond."
        )
        return redirect("plafonds")

    garantie_actes = (
        GarantieActe.objects
        .select_related("id_garantie", "id_acte")
        .filter(statut="ACTIF")
        .order_by("id_garantie__libelle", "id_acte__libelle")
    )

    if request.method == "POST":
        form = PlafondForm(request.POST)

        form.fields["id_garantie_acte"].choices = [
            (
                str(ga.id_garantie_acte),
                f"{ga.id_garantie.code_garantie} - "
                f"{ga.id_garantie.libelle} / "
                f"{ga.id_acte.code_acte} - "
                f"{ga.id_acte.libelle}"
            )
            for ga in garantie_actes
        ]

        if form.is_valid():
            try:
                garantie_acte = GarantieActe.objects.get(
                    id_garantie_acte=form.cleaned_data["id_garantie_acte"],
                    statut="ACTIF",
                )

                plafond = Plafond.objects.create(
                    id_garantie_acte=garantie_acte,
                    type_plafond=form.cleaned_data["type_plafond"],
                    niveau_application=form.cleaned_data["niveau_application"],
                    periode=form.cleaned_data["periode"],
                    montant_max=form.cleaned_data["montant_max"],
                    quantite_max=form.cleaned_data["quantite_max"],
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                )

                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="PLAFOND",
                    table_cible="plafond",
                    id_enregistrement=plafond.id_plafond,
                    nouvelle_valeur=(
                        f"Garantie : {garantie_acte.id_garantie.libelle}, "
                        f"Acte : {garantie_acte.id_acte.libelle}, "
                        f"Type : {plafond.type_plafond}, "
                        f"Période : {plafond.periode}"
                    ),
                    description=f"Création du plafond {plafond.id_plafond}",
                )

                messages.success(request, "Plafond créé avec succès.")
                return redirect("plafonds")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création du plafond : {e}"
                )
    else:
        form = PlafondForm()

        form.fields["id_garantie_acte"].choices = [
            (
                str(ga.id_garantie_acte),
                f"{ga.id_garantie.code_garantie} - "
                f"{ga.id_garantie.libelle} / "
                f"{ga.id_acte.code_acte} - "
                f"{ga.id_acte.libelle}"
            )
            for ga in garantie_actes
        ]

    return render(
        request,
        "core/plafond_form.html",
        {
            "form": form,
            "titre": "Nouveau plafond",
            "page": "plafonds",
        }
    )

def plafond_modifier(request, id_plafond):
    """Modifier un plafond existant."""
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

    if "PLAFOND_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de modifier un plafond.")
        return redirect("plafonds")

    try:
        plafond = (
            Plafond.objects
            .select_related(
                "id_garantie_acte",
                "id_garantie_acte__id_garantie",
                "id_garantie_acte__id_acte",
            )
            .get(id_plafond=id_plafond)
        )
    except Plafond.DoesNotExist:
        messages.error(request, "Plafond introuvable.")
        return redirect("plafonds")

    garantie_actes = (
        GarantieActe.objects
        .select_related("id_garantie", "id_acte")
        .filter(statut="ACTIF")
        .order_by("id_garantie__libelle", "id_acte__libelle")
    )

    if request.method == "POST":
        form = PlafondForm(request.POST)

        form.fields["id_garantie_acte"].choices = [
            (
                str(ga.id_garantie_acte),
                f"{ga.id_garantie.code_garantie} - "
                f"{ga.id_garantie.libelle} / "
                f"{ga.id_acte.code_acte} - "
                f"{ga.id_acte.libelle}"
            )
            for ga in garantie_actes
        ]

        if form.is_valid():
            try:
                ancienne_valeur = (
                    f"Garantie : {plafond.id_garantie_acte.id_garantie.libelle}, "
                    f"Acte : {plafond.id_garantie_acte.id_acte.libelle}, "
                    f"Type : {plafond.type_plafond}, "
                    f"Période : {plafond.periode}, "
                    f"Montant : {plafond.montant_max}, "
                    f"Quantité : {plafond.quantite_max}, "
                    f"Statut : {plafond.statut}"
                )

                garantie_acte = GarantieActe.objects.get(
                    id_garantie_acte=form.cleaned_data["id_garantie_acte"],
                    statut="ACTIF",
                )

                plafond.id_garantie_acte = garantie_acte
                plafond.type_plafond = form.cleaned_data["type_plafond"]
                plafond.niveau_application = form.cleaned_data["niveau_application"]
                plafond.periode = form.cleaned_data["periode"]
                plafond.montant_max = form.cleaned_data["montant_max"]
                plafond.quantite_max = form.cleaned_data["quantite_max"]
                plafond.date_debut = form.cleaned_data["date_debut"]
                plafond.date_fin = form.cleaned_data["date_fin"]
                plafond.statut = form.cleaned_data["statut"]

                plafond.save()

                nouvelle_valeur = (
                    f"Garantie : {plafond.id_garantie_acte.id_garantie.libelle}, "
                    f"Acte : {plafond.id_garantie_acte.id_acte.libelle}, "
                    f"Type : {plafond.type_plafond}, "
                    f"Période : {plafond.periode}, "
                    f"Montant : {plafond.montant_max}, "
                    f"Quantité : {plafond.quantite_max}, "
                    f"Statut : {plafond.statut}"
                )

                enregistrer_audit(
                    request=request,
                    type_action="MODIFICATION",
                    module="PLAFOND",
                    table_cible="plafond",
                    id_enregistrement=plafond.id_plafond,
                    ancienne_valeur=ancienne_valeur,
                    nouvelle_valeur=nouvelle_valeur,
                    description=f"Modification du plafond {plafond.id_plafond}",
                )

                messages.success(request, "Plafond modifié avec succès.")
                return redirect("plafonds")

            except Exception as e:
                messages.error(request, f"Erreur lors de la modification : {e}")
    else:
        form = PlafondForm(
            initial={
                "id_garantie_acte": str(plafond.id_garantie_acte_id),
                "type_plafond": plafond.type_plafond,
                "niveau_application": plafond.niveau_application,
                "periode": plafond.periode,
                "montant_max": plafond.montant_max,
                "quantite_max": plafond.quantite_max,
                "date_debut": plafond.date_debut,
                "date_fin": plafond.date_fin,
                "statut": plafond.statut,
            }
        )

        form.fields["id_garantie_acte"].choices = [
            (
                str(ga.id_garantie_acte),
                f"{ga.id_garantie.code_garantie} - "
                f"{ga.id_garantie.libelle} / "
                f"{ga.id_acte.code_acte} - "
                f"{ga.id_acte.libelle}"
            )
            for ga in garantie_actes
        ]

    return render(
        request,
        "core/plafond_form.html",
        {
            "form": form,
            "titre": "Modifier le plafond",
        }
    )


def plafond_desactiver(request, id_plafond):
    """Désactiver un plafond."""
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

    if "PLAFOND_DELETE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de désactiver un plafond.")
        return redirect("plafonds")

    try:
        plafond = (
            Plafond.objects
            .select_related(
                "id_garantie_acte",
                "id_garantie_acte__id_garantie",
                "id_garantie_acte__id_acte",
            )
            .get(id_plafond=id_plafond)
        )
    except Plafond.DoesNotExist:
        messages.error(request, "Plafond introuvable.")
        return redirect("plafonds")

    if request.method == "POST":
        try:
            ancienne_valeur = (
                f"Garantie : {plafond.id_garantie_acte.id_garantie.libelle}, "
                f"Acte : {plafond.id_garantie_acte.id_acte.libelle}, "
                f"Statut : {plafond.statut}"
            )

            plafond.statut = "INACTIF"
            plafond.save()

            enregistrer_audit(
                request=request,
                type_action="DESACTIVATION",
                module="PLAFOND",
                table_cible="plafond",
                id_enregistrement=plafond.id_plafond,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur="Statut : INACTIF",
                description=f"Désactivation du plafond {plafond.id_plafond}",
            )

            messages.success(request, "Plafond désactivé avec succès.")

        except Exception as e:
            messages.error(request, f"Erreur lors de la désactivation : {e}")

        return redirect("plafonds")

    return render(
        request,
        "core/plafond_desactiver.html",
        {
            "plafond": plafond,
            "page": "plafonds",
        }
    )


def plafonds(request):
    """Liste des plafonds."""
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

    if "PLAFOND_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation de consulter les plafonds.")
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    type_plafond = request.GET.get("type_plafond", "").strip()
    periode = request.GET.get("periode", "").strip()
    statut = request.GET.get("statut", "").strip()

    plafonds = (
        Plafond.objects
        .select_related(
            "id_garantie_acte",
            "id_garantie_acte__id_garantie",
            "id_garantie_acte__id_acte",
        )
        .all()
        .order_by(
            "id_garantie_acte__id_garantie__libelle",
            "id_garantie_acte__id_acte__libelle",
            "-date_debut",
        )
    )

    if recherche:
        plafonds = plafonds.filter(
            Q(id_garantie_acte__id_garantie__code_garantie__icontains=recherche)
            | Q(id_garantie_acte__id_garantie__libelle__icontains=recherche)
            | Q(id_garantie_acte__id_acte__code_acte__icontains=recherche)
            | Q(id_garantie_acte__id_acte__libelle__icontains=recherche)
        )

    if type_plafond:
        plafonds = plafonds.filter(type_plafond=type_plafond)

    if periode:
        plafonds = plafonds.filter(periode=periode)

    if statut:
        plafonds = plafonds.filter(statut=statut)

    return render(
        request,
        "core/plafonds.html",
        {
            "plafonds": plafonds,
            "permissions": permissions,
            "recherche": recherche,
            "type_plafond": type_plafond,
            "periode": periode,
            "statut": statut,
            "page": "plafonds",
        }
    )
