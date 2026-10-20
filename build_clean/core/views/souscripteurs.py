# core/views/souscripteurs.py
"""
Vues de gestion des souscripteurs.

Fonctions :
- souscripteurs : liste des souscripteurs
- _generer_code_souscripteur : helper
- souscripteur_create : créer un souscripteur
- souscripteur_modifier : modifier un souscripteur
- souscripteur_radier : radier un souscripteur
"""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import SouscripteurForm
from core.models import (
    RolePermission,
    Souscripteur,
)
from core.views.champs import (
    get_champs_pour_entite,
    get_valeur_champ,
    sauvegarder_valeurs_champs,
)


def souscripteurs(request):
    """Liste des souscripteurs."""
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

    if "SOUSCRIPTEUR_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les souscripteurs."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    souscripteurs = (
        Souscripteur.objects
        .all()
        .order_by("raison_sociale")
    )

    if recherche:
        souscripteurs = souscripteurs.filter(
            Q(code_souscripteur__icontains=recherche)
            | Q(raison_sociale__icontains=recherche)
            | Q(nif__icontains=recherche)
            | Q(telephone__icontains=recherche)
            | Q(email__icontains=recherche)
        )

    if statut:
        souscripteurs = souscripteurs.filter(statut=statut)

    return render(
        request,
        "core/souscripteurs.html",
        {
            "souscripteurs": souscripteurs,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "souscripteurs",
        }
    )


def _generer_code_souscripteur():
    """Génère un code unique de souscripteur."""
    annee = timezone.now().year
    prefixe = f"SOUS-{annee}-"

    numeros = (
        Souscripteur.objects
        .filter(code_souscripteur__startswith=prefixe)
        .values_list("code_souscripteur", flat=True)
    )

    valeurs = []

    for code in numeros:
        try:
            valeurs.append(int(code.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    code_souscripteur = f"{prefixe}{prochain:04d}"

    while Souscripteur.objects.filter(
        code_souscripteur=code_souscripteur
    ).exists():
        prochain += 1
        code_souscripteur = f"{prefixe}{prochain:04d}"

    return code_souscripteur


def souscripteur_create(request):
    """Créer un nouveau souscripteur."""
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

    if "SOUSCRIPTEUR_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("souscripteurs")

    if request.method == "POST":
        form = SouscripteurForm(request.POST)

        if form.is_valid():
            try:
                souscripteur = Souscripteur.objects.create(
                    code_souscripteur=_generer_code_souscripteur(),
                    raison_sociale=form.cleaned_data["raison_sociale"],
                    type_souscripteur=form.cleaned_data["type_souscripteur"],
                    nif=form.cleaned_data["nif"] or None,
                    registre_commerce=form.cleaned_data["registre_commerce"] or None,
                    adresse=form.cleaned_data["adresse"] or None,
                    telephone=form.cleaned_data["telephone"] or None,
                    email=form.cleaned_data["email"] or None,
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                # Sauvegarder les champs personnalisés
                sauvegarder_valeurs_champs(
                    request, "SOUSCRIPTEUR", souscripteur.id_souscripteur
                )

                messages.success(request, "Souscripteur créé avec succès.")
                return redirect("souscripteurs")

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = SouscripteurForm()

    champs = get_champs_pour_entite("SOUSCRIPTEUR")
    for c in champs:
        c.valeur_actuelle = None
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/souscripteur_form.html",
        {
            "form": form,
            "titre": "Nouveau souscripteur",
            "page": "souscripteurs",
            "champs_disponibles": champs,
        }
    )


def souscripteur_modifier(request, id_souscripteur):
    """Modifier un souscripteur existant."""
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

    if "SOUSCRIPTEUR_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("souscripteurs")

    try:
        souscripteur = Souscripteur.objects.get(id_souscripteur=id_souscripteur)
    except Souscripteur.DoesNotExist:
        messages.error(request, "Souscripteur introuvable.")
        return redirect("souscripteurs")

    if request.method == "POST":
        form = SouscripteurForm(request.POST)

        if form.is_valid():
            try:
                souscripteur.raison_sociale = form.cleaned_data["raison_sociale"]
                souscripteur.type_souscripteur = form.cleaned_data["type_souscripteur"]
                souscripteur.nif = form.cleaned_data["nif"] or None
                souscripteur.registre_commerce = form.cleaned_data["registre_commerce"] or None
                souscripteur.adresse = form.cleaned_data["adresse"] or None
                souscripteur.telephone = form.cleaned_data["telephone"] or None
                souscripteur.email = form.cleaned_data["email"] or None
                souscripteur.statut = form.cleaned_data["statut"]
                souscripteur.save()

                # Mettre à jour les champs personnalisés
                sauvegarder_valeurs_champs(
                    request, "SOUSCRIPTEUR", souscripteur.id_souscripteur
                )

                messages.success(request, "Souscripteur modifié avec succès.")
                return redirect("souscripteurs")

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = SouscripteurForm(
            initial={
                "code_souscripteur": souscripteur.code_souscripteur,
                "raison_sociale": souscripteur.raison_sociale,
                "type_souscripteur": souscripteur.type_souscripteur,
                "nif": souscripteur.nif,
                "registre_commerce": souscripteur.registre_commerce,
                "adresse": souscripteur.adresse,
                "telephone": souscripteur.telephone,
                "email": souscripteur.email,
                "statut": souscripteur.statut,
            }
        )

    champs = get_champs_pour_entite("SOUSCRIPTEUR")
    for c in champs:
        c.valeur_actuelle = get_valeur_champ(c, souscripteur.id_souscripteur)
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/souscripteur_form.html",
        {
            "form": form,
            "titre": "Modifier le souscripteur",
            "page": "souscripteurs",
            "champs_disponibles": champs,
        }
    )


def souscripteur_radier(request, id_souscripteur):
    """Radier un souscripteur."""
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

    if "SOUSCRIPTEUR_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un souscripteur."
        )
        return redirect("souscripteurs")

    try:
        souscripteur = Souscripteur.objects.get(id_souscripteur=id_souscripteur)
    except Souscripteur.DoesNotExist:
        messages.error(request, "Souscripteur introuvable.")
        return redirect("souscripteurs")

    if request.method == "POST":
        souscripteur.statut = "RADIE"
        souscripteur.save()

        messages.success(request, "Souscripteur radié avec succès.")

    return redirect("souscripteurs")