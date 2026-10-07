# core/views/actes.py
"""
Vues de gestion des actes, sous-actes et types de prestation.

Fonctions :
- types_prestation : liste
- type_prestation_create : créer
- type_prestation_modifier : modifier
- type_prestation_radier : radier
"""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.forms import (
    SousActeForm,
    TypePrestationForm
)    
from core.models import (
    Acte,
    RolePermission,
    SousActe,
    TypePrestation,
)


def types_prestation(request):
    """Liste des types de prestation."""
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

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    types_prestation_liste = (
        TypePrestation.objects
        .all()
        .order_by("-id_type_prestation")
    )

    if recherche:
        types_prestation_liste = types_prestation_liste.filter(
            Q(code_type__icontains=recherche)
            | Q(libelle__icontains=recherche)
        )

    if statut:
        types_prestation_liste = types_prestation_liste.filter(statut=statut)

    return render(
        request,
        "core/types_prestation.html",
        {
            "types_prestation": types_prestation_liste,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "types_prestation",
        }
    )


def type_prestation_create(request):
    """Créer un nouveau type de prestation."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    if request.method == "POST":
        form = TypePrestationForm(request.POST)

        if form.is_valid():
            try:
                TypePrestation.objects.create(
                    code_type=form.cleaned_data["code_type"].upper(),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"],
                    statut=form.cleaned_data["statut"],
                )
                messages.success(
                    request,
                    "Type de prestation créé avec succès."
                )
                return redirect("types_prestation")
            except Exception as e:
                messages.error(request, f"Erreur : {e}")
    else:
        form = TypePrestationForm()

    return render(
        request,
        "core/types_prestation_form.html",
        {
            "form": form,
            "titre": "Nouveau type de prestation",
            "page": "types_prestation",
        }
    )


def type_prestation_modifier(request, id_type_prestation):
    """Modifier un type de prestation existant."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    type_prestation = get_object_or_404(
        TypePrestation,
        id_type_prestation=id_type_prestation
    )

    if request.method == "POST":
        form = TypePrestationForm(request.POST)

        if form.is_valid():
            type_prestation.code_type = form.cleaned_data["code_type"].upper()
            type_prestation.libelle = form.cleaned_data["libelle"]
            type_prestation.description = form.cleaned_data["description"]
            type_prestation.statut = form.cleaned_data["statut"]
            type_prestation.save()

            messages.success(
                request,
                "Type de prestation modifié avec succès."
            )
            return redirect("types_prestation")
    else:
        form = TypePrestationForm(initial={
            "code_type": type_prestation.code_type,
            "libelle": type_prestation.libelle,
            "description": type_prestation.description,
            "statut": type_prestation.statut,
        })

    return render(
        request,
        "core/types_prestation_form.html",
        {
            "form": form,
            "titre": "Modifier le type de prestation",
        }
    )


def type_prestation_radier(request, id_type_prestation):
    """Radier un type de prestation."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    type_prestation = get_object_or_404(
        TypePrestation,
        id_type_prestation=id_type_prestation
    )

    if request.method == "POST":
        type_prestation.statut = "INACTIF"
        type_prestation.save()
        messages.success(
            request,
            "Type de prestation désactivé avec succès."
        )

    return redirect("types_prestation")


def actes(request):
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

    if "ACTE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les actes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    actes = (
        Acte.objects
        .select_related("id_type_prestation")
        .all()
        .order_by("-id_acte")
    )

    if recherche:
        from django.db.models import Q

        actes = actes.filter(
            Q(code_acte__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        actes = actes.filter(statut=statut)

    return render(
        request,
        "core/actes.html",
        {
            "actes": actes,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "actes",       # ← AJOUTE
        }
    )

def acte_detail(request, id_acte):
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

    if "ACTE_VIEW" not in permissions:
        return redirect("accueil")

    acte = get_object_or_404(
        Acte.objects.select_related("id_type_prestation"),
        id_acte=id_acte
    )

    sous_actes = (
        SousActe.objects
        .filter(id_acte=acte)
        .order_by("libelle")
    )

    return render(
        request,
        "core/acte_detail.html",
        {
            "acte": acte,
            "sous_actes": sous_actes,
            "permissions": permissions,
        }
    )

def acte_create(request):
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

    if "ACTE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un acte."
        )
        return redirect("actes")

    types_prestation = (
        TypePrestation.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    if request.method == "POST":
        form = ActeForm(request.POST)

        form.fields["id_type_prestation"].choices = [
            (
                str(t.id_type_prestation),
                t.libelle
            )
            for t in types_prestation
        ]

        if form.is_valid():
            try:
                type_prestation = TypePrestation.objects.get(
                    id_type_prestation=form.cleaned_data["id_type_prestation"],
                    statut="ACTIF"
                )

                Acte.objects.create(
                    id_type_prestation=type_prestation,
                    code_acte=generer_code_acte(),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"] or None,
                    unite=form.cleaned_data["unite"] or None,
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Acte créé avec succès."
                )

                return redirect("actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création : {e}"
                )

    else:
        form = ActeForm()

        form.fields["id_type_prestation"].choices = [
            (
                str(t.id_type_prestation),
                t.libelle
            )
            for t in types_prestation
        ]

    return render(
        request,
        "core/acte_form.html",
        {
            "form": form,
            "titre": "Nouvel acte",
        }
    )
def acte_modifier(request, id_acte):
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

    if "ACTE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un acte."
        )
        return redirect("actes")

    try:
        acte = Acte.objects.get(id_acte=id_acte)
    except Acte.DoesNotExist:
        messages.error(
            request,
            "Acte introuvable."
        )
        return redirect("actes")

    if request.method == "POST":
        form = ActeForm(request.POST)

        if form.is_valid():
            try:
                acte.id_type_prestation_id = form.cleaned_data["id_type_prestation"]
                acte.libelle = form.cleaned_data["libelle"]
                acte.description = form.cleaned_data["description"] or None
                acte.unite = form.cleaned_data["unite"] or None
                acte.statut = form.cleaned_data["statut"]

                acte.save()

                messages.success(
                    request,
                    "Acte modifié avec succès."
                )
                return redirect("actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = ActeForm(
            initial={
                "id_type_prestation": acte.id_type_prestation_id,
                "code_acte": acte.code_acte,
                "libelle": acte.libelle,
                "description": acte.description,
                "unite": acte.unite,
                "statut": acte.statut,
            }
       
            )
        types_prestation = (
            TypePrestation.objects
            .filter(statut="ACTIF")
            .order_by("libelle")
        )

        form.fields["id_type_prestation"].choices = [
    (
        str(t.id_type_prestation),
        t.libelle
    )
    for t in types_prestation
]
    return render(
        request,
        "core/acte_form.html",
        {
            "form": form,
            "titre": "Modifier un acte",
        }
    )
def acte_radier(request, id_acte):
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

    if "ACTE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un acte."
        )
        return redirect("actes")

    try:
        acte = Acte.objects.get(id_acte=id_acte)
    except Acte.DoesNotExist:
        messages.error(
            request,
            "Acte introuvable."
        )
        return redirect("actes")

    if request.method == "POST":
        acte.statut = "INACTIF"
        acte.save()

        messages.success(
            request,
            "Acte radié avec succès."
        )

    return redirect("actes")


def sous_actes(request):
    """Liste des sous-actes."""
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

    if "ACTE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les sous-actes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()
    id_acte = request.GET.get("id_acte", "").strip()

    sous_actes_liste = (
        SousActe.objects
        .select_related("id_acte")
        .all()
        .order_by("-id_sous_acte")
    )

    if recherche:
        sous_actes_liste = sous_actes_liste.filter(
            Q(code_sous_acte__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        sous_actes_liste = sous_actes_liste.filter(statut=statut)

    if id_acte:
        sous_actes_liste = sous_actes_liste.filter(id_acte_id=id_acte)

    actes_liste = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    return render(
        request,
        "core/sous_actes.html",
        {
            "sous_actes": sous_actes_liste,
            "actes": actes_liste,
            "recherche": recherche,
            "statut": statut,
            "id_acte": id_acte,
            "permissions": permissions,
            "page": "sous_actes",
        }
    )


def _generer_code_acte():
    """Génère un code unique d'acte."""
    annee = timezone.now().year
    prefixe = f"ACT-{annee}-"

    codes = (
        Acte.objects
        .filter(code_acte__startswith=prefixe)
        .values_list("code_acte", flat=True)
    )

    valeurs = []
    for code in codes:
        try:
            valeurs.append(int(code.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    code_acte = f"{prefixe}{prochain:04d}"

    while Acte.objects.filter(code_acte=code_acte).exists():
        prochain += 1
        code_acte = f"{prefixe}{prochain:04d}"

    return code_acte


def _generer_code_sous_acte():
    """Génère un code unique de sous-acte."""
    annee = timezone.now().year
    prefixe = f"SA-{annee}-"

    codes = (
        SousActe.objects
        .filter(code_sous_acte__startswith=prefixe)
        .values_list("code_sous_acte", flat=True)
    )

    valeurs = []
    for code in codes:
        try:
            valeurs.append(int(code.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    code_sous_acte = f"{prefixe}{prochain:04d}"

    while SousActe.objects.filter(code_sous_acte=code_sous_acte).exists():
        prochain += 1
        code_sous_acte = f"{prefixe}{prochain:04d}"

    return code_sous_acte


def sous_acte_create(request):
    """Créer un nouveau sous-acte."""
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

    if "ACTE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un sous-acte."
        )
        return redirect("sous_actes")

    actes_liste = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    if request.method == "POST":
        form = SousActeForm(request.POST)

        form.fields["id_acte"].choices = [
            (acte.id_acte, f"{acte.code_acte} - {acte.libelle}")
            for acte in actes_liste
        ]

        if form.is_valid():
            id_acte = form.cleaned_data["id_acte"]
            code_sous_acte = _generer_code_sous_acte()

            sous_acte = SousActe.objects.create(
                id_acte_id=id_acte,
                code_sous_acte=code_sous_acte,
                libelle=form.cleaned_data["libelle"],
                description=form.cleaned_data["description"],
                unite=form.cleaned_data["unite"],
                statut="ACTIF",
            )

            messages.success(
                request,
                f"Sous-acte {sous_acte.code_sous_acte} créé avec succès."
            )
            return redirect("sous_actes")
    else:
        id_acte_preselectionne = request.GET.get("id_acte", "").strip()

        form = SousActeForm(
            initial={"id_acte": id_acte_preselectionne}
        )

    form.fields["id_acte"].choices = [
        (acte.id_acte, f"{acte.code_acte} - {acte.libelle}")
        for acte in actes_liste
    ]

    return render(
        request,
        "core/sous_acte_form.html",
        {
            "form": form,
            "titre": "Nouveau sous-acte",
            "permissions": permissions,
            "page": "sous_actes",
        }
    )


def sous_acte_modifier(request, id_sous_acte):
    """Modifier un sous-acte existant."""
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

    if "ACTE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un sous-acte."
        )
        return redirect("sous_actes")

    try:
        sous_acte = SousActe.objects.get(id_sous_acte=id_sous_acte)
    except SousActe.DoesNotExist:
        messages.error(request, "Sous-acte introuvable.")
        return redirect("sous_actes")

    actes_liste = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    if request.method == "POST":
        form = SousActeForm(request.POST)
        form.fields["id_acte"].choices = [
            (acte.id_acte, f"{acte.code_acte} - {acte.libelle}")
            for acte in actes_liste
        ]

        if form.is_valid():
            try:
                sous_acte.id_acte_id = form.cleaned_data["id_acte"]
                sous_acte.libelle = form.cleaned_data["libelle"]
                sous_acte.description = form.cleaned_data["description"]
                sous_acte.unite = form.cleaned_data["unite"]
                sous_acte.statut = form.cleaned_data["statut"]
                sous_acte.save()

                messages.success(
                    request,
                    f"Sous-acte {sous_acte.code_sous_acte} modifié avec succès."
                )
                return redirect("sous_actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )
    else:
        form = SousActeForm(
            initial={
                "id_acte": sous_acte.id_acte_id,
                "code_sous_acte": sous_acte.code_sous_acte,
                "libelle": sous_acte.libelle,
                "description": sous_acte.description,
                "unite": sous_acte.unite,
                "statut": sous_acte.statut,
            }
        )
        form.fields["id_acte"].choices = [
            (acte.id_acte, f"{acte.code_acte} - {acte.libelle}")
            for acte in actes_liste
        ]

    return render(
        request,
        "core/sous_acte_form.html",
        {
            "form": form,
            "titre": "Modifier le sous-acte",
            "permissions": permissions,
            "page": "sous_actes",
        }
    )


def sous_acte_radier(request, id_sous_acte):
    """Radier un sous-acte."""
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

    if "ACTE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier un sous-acte."
        )
        return redirect("sous_actes")

    try:
        sous_acte = SousActe.objects.get(id_sous_acte=id_sous_acte)
    except SousActe.DoesNotExist:
        messages.error(request, "Sous-acte introuvable.")
        return redirect("sous_actes")

    if request.method == "POST":
        sous_acte.statut = "INACTIF"
        sous_acte.save()

        messages.success(request, "Sous-acte radié avec succès.")

    return redirect("sous_actes")
