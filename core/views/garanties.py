"""Vues de gestion des garanties et garanties-actes."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.auth_utils import session_utilisateur_required
from core.forms import GarantieForm, GarantieActeForm
from core.models import (
    Acte,
    Garantie,
    GarantieActe,
    RolePermission,
)


def garanties(request):
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

    if "GARANTIE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les garanties."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    garanties = (
        Garantie.objects
        .all()
        .order_by("-id_garantie")
    )

    if recherche:
        from django.db.models import Q

        garanties = garanties.filter(
            Q(code_garantie__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        garanties = garanties.filter(
            statut=statut
        )

    return render(
        request,
        "core/garanties.html",
        {
            "garanties": garanties,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
        }
    )

def garantie_detail(request, id_garantie):
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

    if "GARANTIE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter cette garantie."
        )
        return redirect("garanties")

    try:
        garantie = Garantie.objects.get(
            id_garantie=id_garantie
        )
    except Garantie.DoesNotExist:
        messages.error(
            request,
            "Garantie introuvable."
        )
        return redirect("garanties")

    actes = (
        GarantieActe.objects
        .select_related("id_acte")
        .filter(id_garantie=garantie)
        .order_by("id_garantie_acte")
    )

    return render(
        request,
        "core/garantie_detail.html",
        {
            "garantie": garantie,
            "actes": actes,
            "permissions": permissions,
        }
    )
def _generer_code_garantie():
    annee = timezone.now().year
    prefixe = f"GAR-{annee}-"

    codes = (
        Garantie.objects
        .filter(code_garantie__startswith=prefixe)
        .values_list("code_garantie", flat=True)
    )

    valeurs = []

    for code in codes:
        try:
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code_garantie = f"{prefixe}{prochain:04d}"

    while Garantie.objects.filter(
        code_garantie=code_garantie
    ).exists():
        prochain += 1
        code_garantie = f"{prefixe}{prochain:04d}"

    return code_garantie

def garantie_create(request):
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

    if "GARANTIE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de crÃ©er une garantie."
        )
        return redirect("garanties")

    if request.method == "POST":
        form = GarantieForm(request.POST)

        if form.is_valid():
            try:
                Garantie.objects.create(
                    code_garantie=_generer_code_garantie(),
                    libelle=form.cleaned_data["libelle"],
                    description=form.cleaned_data["description"] or None,
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Garantie crÃ©Ã©e avec succÃ¨s."
                )

                return redirect("garanties")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = GarantieForm()

    return render(
        request,
        "core/garantie_form.html",
        {
            "form": form,
            "titre": "Nouvelle garantie",
        }
    )
def garantie_modifier(request, id_garantie):
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    try:
        garantie = Garantie.objects.get(
            id_garantie=id_garantie
        )
    except Garantie.DoesNotExist:
        messages.error(
            request,
            "Garantie introuvable."
        )
        return redirect("garanties")

    if request.method == "POST":
        form = GarantieForm(request.POST)

        if form.is_valid():
            try:
                
                garantie.libelle = (
                    form.cleaned_data["libelle"]
                )
                garantie.description = (
                    form.cleaned_data["description"] or None
                )
                garantie.statut = (
                    form.cleaned_data["statut"]
                )

                garantie.save()

                messages.success(
                    request,
                    "Garantie modifiÃ©e avec succÃ¨s."
                )

                return redirect("garanties")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = GarantieForm(
            initial={
                "code_garantie": garantie.code_garantie,
                "libelle": garantie.libelle,
                "description": garantie.description,
                "statut": garantie.statut,
            }
        )

    return render(
        request,
        "core/garantie_form.html",
        {
            "form": form,
            "titre": "Modifier la garantie",
        }
    )

def garantie_radier(request, id_garantie):
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

    if "GARANTIE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une garantie."
        )
        return redirect("garanties")

    try:
        garantie = Garantie.objects.get(
            id_garantie=id_garantie
        )
    except Garantie.DoesNotExist:
        messages.error(
            request,
            "Garantie introuvable."
        )
        return redirect("garanties")

    if request.method == "POST":
        garantie.statut = "RADIE"
        garantie.save()

        messages.success(
            request,
            "Garantie radiÃ©e avec succÃ¨s."
        )

    return redirect("garanties")



def garantie_actes(request):
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

    if "GARANTIE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les associations garantie-acte."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    id_garantie = request.GET.get("id_garantie", "").strip()

    garantie_actes = (
        GarantieActe.objects
        .select_related("id_garantie", "id_acte", "id_acte__id_type_prestation")
        .all()
        .order_by("-id_garantie_acte")
    )

    if recherche:
        from django.db.models import Q

        garantie_actes = garantie_actes.filter(
            Q(id_garantie__code_garantie__icontains=recherche)
            | Q(id_garantie__libelle__icontains=recherche)
            | Q(id_acte__code_acte__icontains=recherche)
            | Q(id_acte__libelle__icontains=recherche)
        )

    if id_garantie:
        garantie_actes = garantie_actes.filter(
            id_garantie=id_garantie
        )

    garanties = (
        Garantie.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    return render(
        request,
        "core/garantie_actes.html",
        {
            "garantie_actes": garantie_actes,
            "garanties": garanties,
            "recherche": recherche,
            "id_garantie": id_garantie,
            "permissions": permissions,
        }
    )
def garantie_acte_create(request):
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

    if "GARANTIE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'associer un acte Ã  une garantie."
        )
        return redirect("garantie_actes")

    garanties = (
        Garantie.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )
    id_acte_preselectionne = request.GET.get("id_acte", "").strip()
    id_garantie_preselectionne = request.GET.get(
        "id_garantie",
        ""
    ).strip()

    garantie_preselectionnee = None

    if id_garantie_preselectionne:
        garantie_preselectionnee = (
            Garantie.objects
            .filter(
                id_garantie=id_garantie_preselectionne,
                statut="ACTIF"
            )
            .first()
        )

    if request.method == "POST":
        form = GarantieActeForm(request.POST)

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (
                str(a.id_acte),
                f"{a.code_acte} - {a.libelle}"
            )
            for a in actes
        ]

        if form.is_valid():
            try:
                garantie = Garantie.objects.get(
                    id_garantie=form.cleaned_data["id_garantie"],
                    statut="ACTIF"
                )

                acte = Acte.objects.get(
                    id_acte=form.cleaned_data["id_acte"],
                    statut="ACTIF"
                )

                GarantieActe.objects.create(
                    id_garantie=garantie,
                    id_acte=acte,
                    taux_prise_en_charge=form.cleaned_data[
                        "taux_prise_en_charge"
                    ],
                    franchise=form.cleaned_data["franchise"],
                    date_debut=form.cleaned_data["date_debut"],
                    date_fin=form.cleaned_data["date_fin"],
                    statut=form.cleaned_data["statut"],
                )

                messages.success(
                    request,
                    "Association garantie-acte crÃ©Ã©e avec succÃ¨s."
                )

                return redirect("garantie_actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la crÃ©ation : {e}"
                )

    else:
        form = GarantieActeForm()

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (
                str(a.id_acte),
                f"{a.code_acte} - {a.libelle}"
            )
            for a in actes
        ]
        if garantie_preselectionnee:
            form.initial["id_garantie"] = (
                str(garantie_preselectionnee.id_garantie)
            )

    return render(
        request,
        "core/garantie_acte_form.html",
        {
            "form": form,
            "titre": "Associer un acte Ã  une garantie",
            "garantie_preselectionnee": garantie_preselectionnee,
        }
    )

def garantie_acte_modifier(request, id_garantie_acte):
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

    if "GARANTIE_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier une association garantie-acte."
        )
        return redirect("garantie_actes")

    try:
        garantie_acte = GarantieActe.objects.get(
            id_garantie_acte=id_garantie_acte
        )
    except GarantieActe.DoesNotExist:
        messages.error(
            request,
            "Association garantie-acte introuvable."
        )
        return redirect("garantie_actes")

    garanties = (
        Garantie.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )
    id_acte_preselectionne = request.GET.get("id_acte", "").strip()

    if request.method == "POST":
        form = GarantieActeForm(request.POST)

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (
                str(a.id_acte),
                f"{a.code_acte} - {a.libelle}"
            )
            for a in actes
        ]

        if form.is_valid():
            try:
                garantie_acte.id_garantie_id = (
                    form.cleaned_data["id_garantie"]
                )
                garantie_acte.id_acte_id = (
                    form.cleaned_data["id_acte"]
                )
                garantie_acte.taux_prise_en_charge = (
                    form.cleaned_data["taux_prise_en_charge"]
                )
                garantie_acte.franchise = (
                    form.cleaned_data["franchise"]
                )
                garantie_acte.date_debut = (
                    form.cleaned_data["date_debut"]
                )
                garantie_acte.date_fin = (
                    form.cleaned_data["date_fin"]
                )
                garantie_acte.statut = (
                    form.cleaned_data["statut"]
                )

                garantie_acte.save()

                messages.success(
                    request,
                    "Association garantie-acte modifiée avec succès."
                )
                return redirect("garantie_actes")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = GarantieActeForm(
            initial={
                "id_garantie": str(
                    garantie_acte.id_garantie_id
                ),
                "id_acte": str(
                    garantie_acte.id_acte_id
                ),
                "taux_prise_en_charge":
                    garantie_acte.taux_prise_en_charge,
                "franchise":
                    garantie_acte.franchise,
                "date_debut":
                    garantie_acte.date_debut,
                "date_fin":
                    garantie_acte.date_fin,
                "statut":
                    garantie_acte.statut,
            }
        )

        form.fields["id_garantie"].choices = [
            (
                str(g.id_garantie),
                f"{g.code_garantie} - {g.libelle}"
            )
            for g in garanties
        ]

        form.fields["id_acte"].choices = [
            (
                str(a.id_acte),
                f"{a.code_acte} - {a.libelle}"
            )
            for a in actes
        ]

    return render(
        request,
        "core/garantie_acte_form.html",
        {
            "form": form,
            "titre": "Modifier l'association garantie-acte",
        }
    )
def garantie_acte_radier(request, id_garantie_acte):
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

    if "GARANTIE_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de radier une association garantie-acte."
        )
        return redirect("garantie_actes")

    try:
        garantie_acte = GarantieActe.objects.get(
            id_garantie_acte=id_garantie_acte
        )
    except GarantieActe.DoesNotExist:
        messages.error(
            request,
            "Association garantie-acte introuvable."
        )
        return redirect("garantie_actes")

    if request.method == "POST":
        garantie_acte.statut = "RADIE"
        garantie_acte.save()

        messages.success(
            request,
            "Association garantie-acte radiÃ©e avec succÃ¨s."
        )

    return redirect("garantie_actes")
