# core/views/adherents.py
"""
Vues de gestion des adhérents.

Fonctions :
- adherents : liste des adhérents
- adherent_detail : fiche d'un adhérent
- _generer_numero_adherent : helper
- _generer_numero_personne : helper
- adherent_create : créer un adhérent
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import AdherentForm
from core.models import (
    Adherent,
    AyantDroit,
    Personne,
    RolePermission,
)
from core.views.champs import (
    get_champs_pour_entite,
    get_valeurs_champs_entite,
    sauvegarder_valeurs_champs,
)
from core.views.dashboard import enregistrer_audit
from core.views.decorators import session_utilisateur_required


@session_utilisateur_required
def adherents(request):
    """Liste des adhérents."""
    utilisateur = request.utilisateur
    id_utilisateur = utilisateur.id_utilisateur

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les adhérents."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    adherents = (
        Adherent.objects
        .select_related("id_personne")
        .all()
        .order_by("-id_adherent")
    )

    if recherche:
        adherents = adherents.filter(
            Q(numero_adherent__icontains=recherche)
            | Q(id_personne__numero_personne__icontains=recherche)
            | Q(id_personne__nom__icontains=recherche)
            | Q(id_personne__prenom__icontains=recherche)
            | Q(id_personne__telephone__icontains=recherche)
        )

    if statut:
        adherents = adherents.filter(statut=statut)

    return render(
        request,
        "core/adherents.html",
        {
            "adherents": adherents,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "adherents",
        }
    )


def adherent_detail(request, id_adherent):
    """Fiche détaillée d'un adhérent."""
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

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter cet adhérent."
        )
        return redirect("adherents")

    try:
        adherent = (
            Adherent.objects
            .select_related("id_personne")
            .get(id_adherent=id_adherent)
        )
    except Adherent.DoesNotExist:
        messages.error(request, "Adhérent introuvable.")
        return redirect("adherents")

    ayants_droit = (
        AyantDroit.objects
        .select_related("id_personne")
        .filter(id_adherent=adherent)
        .order_by("id_ayant_droit")
    )

    # Charger les champs personnalisés pour chaque ayant droit
    for ad in ayants_droit:
        ad.champs_personnalises = get_valeurs_champs_entite(
            "AYANT_DROIT", ad.id_ayant_droit
        )

    champs_perso_adherent = get_valeurs_champs_entite(
        "ADHERENT", adherent.id_adherent
    )
    champs_perso_adherent = [
        c for c in champs_perso_adherent
        if c["valeur"] and str(c["valeur"]).strip()
    ]

    return render(
        request,
        "core/adherent_detail.html",
        {
            "adherent": adherent,
            "ayants_droit": ayants_droit,
            "permissions": permissions,
            "page": "adherents",
            "champs_personnalises": champs_perso_adherent,
        }
    )


def _generer_numero_adherent():
    """Génère un numéro unique d'adhérent."""
    annee = timezone.now().year
    prefixe = f"ADH-{annee}-"

    numeros = (
        Adherent.objects
        .filter(numero_adherent__startswith=prefixe)
        .values_list("numero_adherent", flat=True)
    )

    valeurs = []
    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_adherent = f"{prefixe}{prochain:04d}"

    while Adherent.objects.filter(
        numero_adherent=numero_adherent
    ).exists():
        prochain += 1
        numero_adherent = f"{prefixe}{prochain:04d}"

    return numero_adherent


def _generer_numero_personne():
    """Génère un numéro unique de personne."""
    annee = timezone.now().year
    prefixe = f"PERS-{annee}-"

    numeros = (
        Personne.objects
        .filter(numero_personne__startswith=prefixe)
        .values_list("numero_personne", flat=True)
    )

    valeurs = []
    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_personne = f"{prefixe}{prochain:04d}"

    while Personne.objects.filter(
        numero_personne=numero_personne
    ).exists():
        prochain += 1
        numero_personne = f"{prefixe}{prochain:04d}"

    return numero_personne


def adherent_create(request):
    """Créer un nouvel adhérent."""
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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un adhérent."
        )
        return redirect("adherents")

    if request.method == "POST":
        form = AdherentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    doublon = (
                        Adherent.objects
                        .filter(
                            statut="ACTIF",
                            id_personne__nom__iexact=form.cleaned_data["nom"].strip(),
                            id_personne__prenom__iexact=form.cleaned_data["prenom"].strip(),
                            id_personne__date_naissance=form.cleaned_data["date_naissance"],
                        )
                        .first()
                    )

                    if doublon:
                        messages.error(
                            request,
                            f"Cet adhérent existe déjà "
                            f"({doublon.numero_adherent})."
                        )
                        return render(
                            request,
                            "core/adherent_form.html",
                            {
                                "form": form,
                                "titre": "Nouvel adhérent",
                                "page": "adherents",
                            }
                        )

                    personne = Personne.objects.create(
                        numero_personne=_generer_numero_personne(),
                        nom=form.cleaned_data["nom"].strip(),
                        prenom=form.cleaned_data["prenom"].strip(),
                        date_naissance=form.cleaned_data["date_naissance"],
                        sexe=form.cleaned_data["sexe"] or None,
                        adresse=form.cleaned_data["adresse"] or None,
                        telephone=form.cleaned_data["telephone"] or None,
                        email=form.cleaned_data["email"] or None,
                        statut=form.cleaned_data["statut"],
                        date_creation=timezone.now(),
                    )

                    adherent = Adherent.objects.create(
                        id_personne=personne,
                        numero_adherent=_generer_numero_adherent(),
                        statut=form.cleaned_data["statut"],
                        date_adhesion=form.cleaned_data["date_adhesion"],
                        date_creation=timezone.now(),
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="CREATION",
                        module="ADHERENTS",
                        table_cible="adherent",
                        id_enregistrement=adherent.id_adherent,
                        nouvelle_valeur=(
                            f"Numéro adhérent : "
                            f"{adherent.numero_adherent}, "
                            f"Statut : {adherent.statut}"
                        ),
                        description=(
                            f"Création de l'adhérent "
                            f"{adherent.numero_adherent}"
                        ),
                    )

                    # Sauvegarder les champs personnalisés
                    sauvegarder_valeurs_champs(
                        request, "ADHERENT", adherent.id_adherent
                    )

                messages.success(request, "Adhérent créé avec succès.")
                return redirect("adherents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )
    else:
        form = AdherentForm()

    # Charger les champs personnalisés (dans tous les cas)
    champs = get_champs_pour_entite("ADHERENT")
    for c in champs:
        c.valeur_actuelle = None
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/adherent_form.html",
        {
            "form": form,
            "titre": "Nouvel adhérent",
            "page": "adherents",
            "champs_disponibles": champs,
        }
    )


def adherent_modifier(request, id_adherent):
    """Modifier un adhérent existant."""
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

    if "ADHERENT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un adhérent."
        )
        return redirect("adherents")

    try:
        adherent = (
            Adherent.objects
            .select_related("id_personne")
            .get(id_adherent=id_adherent)
        )
    except Adherent.DoesNotExist:
        messages.error(request, "Adhérent introuvable.")
        return redirect("adherents")

    personne = adherent.id_personne

    if request.method == "POST":
        form = AdherentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    doublon = (
                        Adherent.objects
                        .filter(
                            statut="ACTIF",
                            id_personne__nom__iexact=form.cleaned_data["nom"].strip(),
                            id_personne__prenom__iexact=form.cleaned_data["prenom"].strip(),
                            id_personne__date_naissance=form.cleaned_data["date_naissance"],
                        )
                        .exclude(id_adherent=adherent.id_adherent)
                        .first()
                    )

                    if doublon:
                        messages.error(
                            request,
                            f"Un autre adhérent existe déjà avec ces informations "
                            f"({doublon.numero_adherent})."
                        )
                    else:
                        personne.nom = form.cleaned_data["nom"].strip()
                        personne.prenom = form.cleaned_data["prenom"].strip()
                        personne.date_naissance = form.cleaned_data["date_naissance"]
                        personne.sexe = form.cleaned_data["sexe"] or None
                        personne.adresse = form.cleaned_data["adresse"] or None
                        personne.telephone = form.cleaned_data["telephone"] or None
                        personne.email = form.cleaned_data["email"] or None
                        personne.statut = form.cleaned_data["statut"]
                        personne.date_modification = timezone.now()
                        personne.save()

                        adherent.statut = form.cleaned_data["statut"]
                        adherent.date_adhesion = form.cleaned_data["date_adhesion"]
                        adherent.save()

                        # Mettre à jour les champs personnalisés
                        sauvegarder_valeurs_champs(
                            request, "ADHERENT", adherent.id_adherent
                        )

                        messages.success(
                            request,
                            "Adhérent modifié avec succès."
                        )
                        return redirect("adherents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )
    else:
        form = AdherentForm(
            initial={
                "numero_adherent": adherent.numero_adherent,
                "numero_personne": personne.numero_personne,
                "nom": personne.nom,
                "prenom": personne.prenom,
                "date_naissance": personne.date_naissance,
                "sexe": personne.sexe,
                "adresse": personne.adresse,
                "telephone": personne.telephone,
                "email": personne.email,
                "date_adhesion": adherent.date_adhesion,
                "statut": adherent.statut,
            }
        )

    # Charger les champs personnalisés avec valeurs actuelles
    champs = get_champs_pour_entite("ADHERENT")
    for c in champs:
        c.valeur_actuelle = get_valeur_champ(c, adherent.id_adherent)
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/adherent_form.html",
        {
            "form": form,
            "titre": "Modifier l'adhérent",
            "page": "adherents",
            "champs_disponibles": champs,
        }
    )


def adherent_radier(request, id_adherent):
    """Radier un adhérent."""
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

    if "ADHERENT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un adhérent."
        )
        return redirect("adherents")

    try:
        adherent = Adherent.objects.get(id_adherent=id_adherent)
    except Adherent.DoesNotExist:
        messages.error(request, "Adhérent introuvable.")
        return redirect("adherents")

    if request.method == "POST":
        try:
            adherent.statut = "RADIE"
            adherent.date_radiation = timezone.now().date()
            adherent.save()

            enregistrer_audit(
                request=request,
                type_action="RADIATION",
                module="ADHERENTS",
                table_cible="adherent",
                id_enregistrement=adherent.id_adherent,
                ancienne_valeur="Statut : ACTIF",
                nouvelle_valeur="Statut : RADIE",
                description=f"Radiation de l'adhérent {adherent.numero_adherent}",
            )

            messages.success(request, "Adhérent radié avec succès.")

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de la radiation : {e}"
            )

        return redirect("adherents")

    return render(
        request,
        "core/adherent_radier.html",
        {
            "adherent": adherent,
        }
    )