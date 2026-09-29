"""Vues de gestion des souscripteurs."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.auth_utils import session_utilisateur_required
from core.forms import SouscripteurForm
from core.models import (
    RolePermission,
    Souscripteur,
)


def souscripteurs(request):
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
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
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
        from django.db.models import Q

        souscripteurs = souscripteurs.filter(
            Q(code_souscripteur__icontains=recherche)
            | Q(raison_sociale__icontains=recherche)
            | Q(nif__icontains=recherche)
            | Q(telephone__icontains=recherche)
            | Q(email__icontains=recherche)
        )

    if statut:
        souscripteurs = souscripteurs.filter(
            statut=statut
        )

    return render(
        request,
        "core/souscripteurs.html",
        {
            "souscripteurs": souscripteurs,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )
def _generer_code_souscripteur():
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
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
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
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
    )

    if "SOUSCRIPTEUR_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er un souscripteur."
        )
        return redirect("souscripteurs")

    if request.method == "POST":
        form = SouscripteurForm(request.POST)

        if form.is_valid():
            try:
                Souscripteur.objects.create(
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

                messages.success(
                    request,
                    "Souscripteur crÃ©Ã© avec succÃ¨s."
                )

                return redirect("souscripteurs")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = SouscripteurForm()

    return render(
        request,
        "core/souscripteur_form.html",
        {
            "form": form,
            "titre": "Nouveau souscripteur",
        }
    )
def souscripteur_modifier(request, id_souscripteur):
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
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
    )

    if "SOUSCRIPTEUR_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un souscripteur."
        )
        return redirect("souscripteurs")

    try:
        souscripteur = Souscripteur.objects.get(
            id_souscripteur=id_souscripteur
        )
    except Souscripteur.DoesNotExist:
        messages.error(
            request,
            "Souscripteur introuvable."
        )
        return redirect("souscripteurs")

    if request.method == "POST":
        form = SouscripteurForm(request.POST)

        if form.is_valid():
            try:
                
                souscripteur.raison_sociale = (
                    form.cleaned_data["raison_sociale"]
                )
                souscripteur.type_souscripteur = (
                    form.cleaned_data["type_souscripteur"]
                )
                souscripteur.nif = (
                    form.cleaned_data["nif"] or None
                )
                souscripteur.registre_commerce = (
                    form.cleaned_data["registre_commerce"] or None
                )
                souscripteur.adresse = (
                    form.cleaned_data["adresse"] or None
                )
                souscripteur.telephone = (
                    form.cleaned_data["telephone"] or None
                )
                souscripteur.email = (
                    form.cleaned_data["email"] or None
                )
                souscripteur.statut = (
                    form.cleaned_data["statut"]
                )

                souscripteur.save()

                messages.success(
                    request,
                    "Souscripteur modifiÃ© avec succÃ¨s."
                )

                return redirect("souscripteurs")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

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

    return render(
        request,
        "core/souscripteur_form.html",
        {
            "form": form,
            "titre": "Modifier le souscripteur",
        }
    )


def souscripteur_radier(request, id_souscripteur):
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
        .values_list(
            "id_permission__code_permission",
            flat=True
        )
    )

    if "SOUSCRIPTEUR_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un souscripteur."
        )
        return redirect("souscripteurs")

    try:
        souscripteur = Souscripteur.objects.get(
            id_souscripteur=id_souscripteur
        )
    except Souscripteur.DoesNotExist:
        messages.error(
            request,
            "Souscripteur introuvable."
        )
        return redirect("souscripteurs")

    if request.method == "POST":
        souscripteur.statut = "RADIE"
        souscripteur.save()

        messages.success(
            request,
            "Souscripteur radiÃ© avec succÃ¨s."
        )

    return redirect("souscripteurs")
