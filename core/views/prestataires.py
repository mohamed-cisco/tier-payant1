# core/views/prestataires.py
"""
Vues de gestion des prestataires.

Fonctions :
- prestataires : liste
- _generer_code_prestataire : helper
- prestataire_create : créer
- prestataire_modifier : modifier
- prestataire_radier : radier
"""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import PrestataireForm
from core.models import (
    Prestataire,
    RolePermission,
)
from core.views.champs import (
    get_champs_pour_entite,
    get_valeur_champ,
    sauvegarder_valeurs_champs,
)
from core.views.dashboard import enregistrer_audit


def prestataires(request):
    """Liste des prestataires."""
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

    if "PRESTATAIRE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les prestataires."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    type_prestataire = request.GET.get("type_prestataire", "").strip()
    statut = request.GET.get("statut", "").strip()

    prestataires_liste = (
        Prestataire.objects
        .all()
        .order_by("raison_sociale")
    )

    if recherche:
        prestataires_liste = prestataires_liste.filter(
            Q(code_prestataire__icontains=recherche)
            | Q(raison_sociale__icontains=recherche)
            | Q(nif__icontains=recherche)
            | Q(registre_commerce__icontains=recherche)
            | Q(telephone__icontains=recherche)
        )

    if type_prestataire:
        prestataires_liste = prestataires_liste.filter(type_prestataire=type_prestataire)

    if statut:
        prestataires_liste = prestataires_liste.filter(statut=statut)

    types_prestataire = [
        ("PHARMACIE", "Pharmacie"),
        ("MEDECIN", "Médecin"),
        ("CLINIQUE", "Clinique"),
        ("LABORATOIRE", "Laboratoire"),
        ("CENTRE_RADIOLOGIE", "Centre de radiologie"),
        ("DENTAIRE", "Centre dentaire"),
        ("OPTIQUE", "Centre optique"),
        ("AUTRE", "Autre"),
    ]

    return render(
        request,
        "core/prestataires.html",
        {
            "prestataires": prestataires_liste,
            "recherche": recherche,
            "type_prestataire": type_prestataire,
            "statut": statut,
            "types_prestataire": types_prestataire,
            "permissions": permissions,
            "page": "prestataires",
        }
    )


def _generer_code_prestataire():
    """Génère un code unique de prestataire."""
    annee = timezone.now().year
    prefixe = f"PREST-{annee}-"

    codes = (
        Prestataire.objects
        .filter(code_prestataire__startswith=prefixe)
        .values_list("code_prestataire", flat=True)
    )

    valeurs = []
    for code in codes:
        try:
            valeurs.append(int(code.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    code_prestataire = f"{prefixe}{prochain:04d}"

    while Prestataire.objects.filter(code_prestataire=code_prestataire).exists():
        prochain += 1
        code_prestataire = f"{prefixe}{prochain:04d}"

    return code_prestataire


def prestataire_create(request):
    """Créer un nouveau prestataire."""
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

    if "PRESTATAIRE_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("prestataires")

    if request.method == "POST":
        form = PrestataireForm(request.POST)

        if form.is_valid():
            try:
                nif = (form.cleaned_data.get("nif") or "").strip()
                raison_sociale = form.cleaned_data["raison_sociale"].strip()

                # Détection de doublon
                doublon = None
                if nif:
                    doublon = Prestataire.objects.filter(nif__iexact=nif).first()

                if not doublon and raison_sociale:
                    doublon = Prestataire.objects.filter(
                        raison_sociale__iexact=raison_sociale
                    ).first()

                if doublon and not request.POST.get("confirmer_doublon"):
                    messages.warning(
                        request,
                        f"⚠️ Un prestataire similaire existe déjà : "
                        f"{doublon.code_prestataire} — {doublon.raison_sociale} "
                        f"(NIF : {doublon.nif or 'non renseigné'}). "
                        f"Cliquez à nouveau sur Enregistrer pour créer quand même."
                    )
                    return render(
                        request,
                        "core/prestataire_form.html",
                        {
                            "form": form,
                            "titre": "Nouveau prestataire",
                            "page": "prestataires",
                            "doublon_detecte": doublon,
                            "champs_disponibles": get_champs_pour_entite("PRESTATAIRE"),
                        }
                    )

                prestataire = Prestataire.objects.create(
                    code_prestataire=_generer_code_prestataire(),
                    raison_sociale=raison_sociale,
                    type_prestataire=form.cleaned_data["type_prestataire"],
                    nif=nif or None,
                    registre_commerce=form.cleaned_data["registre_commerce"] or None,
                    adresse=form.cleaned_data["adresse"] or None,
                    telephone=form.cleaned_data["telephone"] or None,
                    email=form.cleaned_data["email"] or None,
                    statut=form.cleaned_data["statut"],
                    date_creation=timezone.now(),
                )

                sauvegarder_valeurs_champs(
                    request, "PRESTATAIRE", prestataire.id_prestataire
                )

                enregistrer_audit(
                    request=request,
                    type_action="CREATION",
                    module="PRESTATAIRE",
                    table_cible="prestataire",
                    id_enregistrement=prestataire.id_prestataire,
                    nouvelle_valeur=(
                        f"{prestataire.code_prestataire} - "
                        f"{prestataire.raison_sociale}"
                    ),
                    description=f"Création du prestataire {prestataire.code_prestataire}",
                )

                messages.success(request, "Prestataire créé avec succès.")
                return redirect("prestataires")

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = PrestataireForm()

    champs = get_champs_pour_entite("PRESTATAIRE")
    for c in champs:
        c.valeur_actuelle = None
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/prestataire_form.html",
        {
            "form": form,
            "titre": "Nouveau prestataire",
            "page": "prestataires",
            "champs_disponibles": champs,
        }
    )


def prestataire_modifier(request, id_prestataire):
    """Modifier un prestataire existant."""
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

    if "PRESTATAIRE_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("prestataires")

    try:
        prestataire = Prestataire.objects.get(id_prestataire=id_prestataire)
    except Prestataire.DoesNotExist:
        messages.error(request, "Prestataire introuvable.")
        return redirect("prestataires")

    if request.method == "POST":
        form = PrestataireForm(request.POST)

        if form.is_valid():
            try:
                prestataire.raison_sociale = form.cleaned_data["raison_sociale"]
                prestataire.type_prestataire = form.cleaned_data["type_prestataire"]
                prestataire.nif = form.cleaned_data["nif"] or None
                prestataire.registre_commerce = form.cleaned_data["registre_commerce"] or None
                prestataire.adresse = form.cleaned_data["adresse"] or None
                prestataire.telephone = form.cleaned_data["telephone"] or None
                prestataire.email = form.cleaned_data["email"] or None
                prestataire.statut = form.cleaned_data["statut"]
                prestataire.save()

                sauvegarder_valeurs_champs(
                    request, "PRESTATAIRE", prestataire.id_prestataire
                )

                messages.success(request, "Prestataire modifié avec succès.")
                return redirect("prestataires")

            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = PrestataireForm(initial={
            "code_prestataire": prestataire.code_prestataire,
            "raison_sociale": prestataire.raison_sociale,
            "type_prestataire": prestataire.type_prestataire,
            "nif": prestataire.nif,
            "registre_commerce": prestataire.registre_commerce,
            "adresse": prestataire.adresse,
            "telephone": prestataire.telephone,
            "email": prestataire.email,
            "statut": prestataire.statut,
        })

    champs = get_champs_pour_entite("PRESTATAIRE")
    for c in champs:
        c.valeur_actuelle = get_valeur_champ(c, prestataire.id_prestataire)
        c.choix_possibles_list = [
            x.strip() for x in (c.choix_possibles or "").split("\n") if x.strip()
        ]

    return render(
        request,
        "core/prestataire_form.html",
        {
            "form": form,
            "titre": "Modifier le prestataire",
            "page": "prestataires",
            "champs_disponibles": champs,
        }
    )


def prestataire_radier(request, id_prestataire):
    """Radier un prestataire."""
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

    if "PRESTATAIRE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un prestataire."
        )
        return redirect("prestataires")

    try:
        prestataire = Prestataire.objects.get(id_prestataire=id_prestataire)
    except Prestataire.DoesNotExist:
        messages.error(request, "Prestataire introuvable.")
        return redirect("prestataires")

    if request.method == "POST":
        prestataire.statut = "INACTIF"
        prestataire.save()

        messages.success(request, "Prestataire désactivé avec succès.")

    return redirect("prestataires")