"""Vues de gestion des actes, sous-actes et tarifs."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.auth_utils import session_utilisateur_required
from core.forms import ActeForm, SousActeForm, TarifSousActeForm
from core.models import (
    # ... (à compléter selon résultat étape 1)
)


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

def sous_actes(request):
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
            "Vous n'avez pas l'autorisation de consulter les sous-actes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()
    id_acte = request.GET.get("id_acte", "").strip()

    sous_actes = (
        SousActe.objects
        .select_related("id_acte")
        .all()
        .order_by("-id_sous_acte")
    )

    if recherche:
        sous_actes = sous_actes.filter(
            Q(code_sous_acte__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        sous_actes = sous_actes.filter(statut=statut)

    if id_acte:
        sous_actes = sous_actes.filter(id_acte_id=id_acte)

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    return render(
        request,
        "core/sous_actes.html",
        {
            "sous_actes": sous_actes,
            "actes": actes,
            "recherche": recherche,
            "statut": statut,
            "id_acte": id_acte,
            "permissions": permissions,
        }
    )

def _generer_code_acte():
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
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code_acte = f"{prefixe}{prochain:04d}"

    while Acte.objects.filter(
        code_acte=code_acte
    ).exists():
        prochain += 1
        code_acte = f"{prefixe}{prochain:04d}"

    return code_acte

def _generer_code_sous_acte():
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
            valeurs.append(
                int(code.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    code_sous_acte = f"{prefixe}{prochain:04d}"

    while SousActe.objects.filter(
        code_sous_acte=code_sous_acte
    ).exists():
        prochain += 1
        code_sous_acte = f"{prefixe}{prochain:04d}"

    return code_sous_acte

def sous_acte_create(request):
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
            "Vous n'avez pas l'autorisation de créer un sous-acte."
        )
        return redirect("sous_actes")

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )

    if request.method == "POST":
        form = SousActeForm(request.POST)

        form.fields["id_acte"].choices = [
            (
                acte.id_acte,
                f"{acte.code_acte} - {acte.libelle}"
            )
            for acte in actes
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
            initial={
                "id_acte": id_acte_preselectionne
            }
        )

    form.fields["id_acte"].choices = [
        (
            acte.id_acte,
            f"{acte.code_acte} - {acte.libelle}"
        )
        for acte in actes
    ]

    return render(
        request,
        "core/sous_acte_form.html",
        {
            "form": form,
            "titre": "Nouveau sous-acte",
            "permissions": permissions,
        }
    )

def sous_acte_modifier(request, id_sous_acte):
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
            "Vous n'avez pas l'autorisation de modifier un sous-acte."
        )
        return redirect("sous_actes")

    try:
        sous_acte = SousActe.objects.get(
            id_sous_acte=id_sous_acte
        )
    except SousActe.DoesNotExist:
        messages.error(
            request,
            "Sous-acte introuvable."
        )
        return redirect("sous_actes")

    actes = (
        Acte.objects
        .filter(statut="ACTIF")
        .order_by("libelle")
    )
    id_acte_preselectionne = request.GET.get("id_acte", "").strip()
    if request.method == "POST":
          form = SousActeForm(request.POST)

          form.fields["id_acte"].choices = [
            (
                acte.id_acte,
                f"{acte.code_acte} - {acte.libelle}"
            )
            for acte in actes
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
            initial={
                "id_acte": id_acte_preselectionne
            }
        )

        form.fields["id_acte"].choices = [
            (
                acte.id_acte,
                f"{acte.code_acte} - {acte.libelle}"
            )
            for acte in actes
        ]

    return render(
        request,
        "core/sous_acte_form.html",
        {
            "form": form,
            "titre": "Modifier le sous-acte",
            "permissions": permissions,
        }
    )

def sous_acte_radier(request, id_sous_acte):
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
            "Vous n'avez pas l'autorisation de radier un sous-acte."
        )
        return redirect("sous_actes")

    try:
        sous_acte = SousActe.objects.get(
            id_sous_acte=id_sous_acte
        )
    except SousActe.DoesNotExist:
        messages.error(
            request,
            "Sous-acte introuvable."
        )
        return redirect("sous_actes")

    if request.method == "POST":
        sous_acte.statut = "INACTIF"
        sous_acte.save()

        messages.success(
            request,
            "Sous-acte radié avec succès."
        )

    return redirect("sous_actes")

def tarif_sous_acte_create(request):
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
            "Vous n'avez pas l'autorisation de créer un tarif de sous-acte."
        )
        return redirect("tarifs_sous_actes")

    sous_actes = (
        SousActe.objects
        .filter(statut="ACTIF")
        .select_related("id_acte")
        .order_by("libelle")
    )

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    if request.method == "POST":

        form = TarifSousActeForm(request.POST)

        form.fields["id_sous_acte"].choices = [
            (
                sous_acte.id_sous_acte,
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        form.fields["id_prestataire"].choices = [
            (
                prestataire.id_prestataire,
                f"{prestataire.code_prestataire} - {prestataire.raison_sociale}"
            )
            for prestataire in prestataires
        ]

        print("DONNEES FORMULAIRE :", form.data)

        if form.is_valid():
            print("FORMULAIRE VALIDE")

            id_sous_acte = form.cleaned_data["id_sous_acte"]
            id_prestataire = form.cleaned_data["id_prestataire"]
            montant = form.cleaned_data["montant"]
            date_debut = form.cleaned_data["date_debut"]
            date_fin = form.cleaned_data["date_fin"]

            if date_fin and date_fin < date_debut:
                form.add_error(
                    "date_fin",
                    "La date de fin doit être supérieure ou égale à la date de début."
                )
            else:

                tarifs_existants = TarifSousActe.objects.filter(
                    id_sous_acte_id=id_sous_acte,
                    id_prestataire_id=id_prestataire
                )

                # Recherche d'une période qui chevauche la nouvelle période.
                if date_fin:
                    tarifs_existants = tarifs_existants.filter(
                        date_debut__lte=date_fin
                    ).filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_debut)
                    )
                else:
                    tarifs_existants = tarifs_existants.filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_debut)
                    )

                if tarifs_existants.exists():

                    messages.error(
                        request,
                        "Impossible de créer ce tarif : "
                        "une autre période tarifaire existe déjà "
                        "pour ce sous-acte et ce prestataire."
                    )

                else:

                    tarif = TarifSousActe.objects.create(
                        id_sous_acte_id=id_sous_acte,
                        id_prestataire_id=id_prestataire,
                        montant=montant,
                        date_debut=date_debut,
                        date_fin=date_fin,
                        statut="ACTIF",
                    )

                    messages.success(
                        request,
                        f"Tarif {tarif.montant} créé avec succès."
                    )

                    return redirect("tarifs_sous_actes")
        else:
            print("FORMULAIRE INVALIDE")
            print("ERREURS FORMULAIRE :", form.errors)

    else:

        form = TarifSousActeForm()

        form.fields["id_sous_acte"].choices = [
            (
                sous_acte.id_sous_acte,
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        form.fields["id_prestataire"].choices = [
            (
                prestataire.id_prestataire,
                f"{prestataire.code_prestataire} - {prestataire.raison_sociale}"
            )
            for prestataire in prestataires
        ]

    return render(
        request,
        "core/tarif_sous_acte_form.html",
        {
            "form": form,
            "titre": "Nouveau tarif sous-acte",
            "permissions": permissions,
        }
    )

def tarif_sous_acte_modifier(request, id_tarif_sous_acte):
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
            "Vous n'avez pas l'autorisation de modifier un tarif de sous-acte."
        )
        return redirect("tarifs_sous_actes")

    try:
        tarif = TarifSousActe.objects.get(
            id_tarif_sous_acte=id_tarif_sous_acte
        )
    except TarifSousActe.DoesNotExist:
        messages.error(
            request,
            "Tarif sous-acte introuvable."
        )
        return redirect("tarifs_sous_actes")

    sous_actes = (
        SousActe.objects
        .filter(statut="ACTIF")
        .select_related("id_acte")
        .order_by("libelle")
    )

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    if request.method == "POST":

        form = TarifSousActeForm(request.POST)

        form.fields["id_sous_acte"].choices = [
            (
                sous_acte.id_sous_acte,
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        form.fields["id_prestataire"].choices = [
            (
                prestataire.id_prestataire,
                f"{prestataire.code_prestataire} - {prestataire.raison_sociale}"
            )
            for prestataire in prestataires
        ]

        if form.is_valid():

            id_sous_acte = form.cleaned_data["id_sous_acte"]
            id_prestataire = form.cleaned_data["id_prestataire"]
            montant = form.cleaned_data["montant"]
            date_debut = form.cleaned_data["date_debut"]
            date_fin = form.cleaned_data["date_fin"]

            if date_fin and date_fin < date_debut:

                form.add_error(
                    "date_fin",
                    "La date de fin doit être supérieure ou égale à la date de début."
                )

            else:

                tarifs_existants = (
                    TarifSousActe.objects
                    .filter(
                        id_sous_acte_id=id_sous_acte,
                        id_prestataire_id=id_prestataire
                    )
                    .exclude(
                        id_tarif_sous_acte=id_tarif_sous_acte
                    )
                )

                if date_fin:

                    tarifs_existants = tarifs_existants.filter(
                        date_debut__lte=date_fin
                    ).filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_debut)
                    )

                else:

                    tarifs_existants = tarifs_existants.filter(
                        Q(date_fin__isnull=True) |
                        Q(date_fin__gte=date_debut)
                    )

                if tarifs_existants.exists():

                    messages.error(
                        request,
                        "Impossible de modifier ce tarif : "
                        "une autre période tarifaire existe déjà "
                        "pour ce sous-acte et ce prestataire."
                    )

                else:

                    tarif.id_sous_acte_id = id_sous_acte
                    tarif.id_prestataire_id = id_prestataire
                    tarif.montant = montant
                    tarif.date_debut = date_debut
                    tarif.date_fin = date_fin

                    tarif.save()

                    messages.success(
                        request,
                        "Tarif sous-acte modifié avec succès."
                    )

                    return redirect("tarifs_sous_actes")

    else:

        form = TarifSousActeForm(
            initial={
                "id_sous_acte": tarif.id_sous_acte_id,
                "id_prestataire": tarif.id_prestataire_id,
                "montant": tarif.montant,
                "date_debut": tarif.date_debut,
                "date_fin": tarif.date_fin,
                "statut": tarif.statut,
            }
        )

        form.fields["id_sous_acte"].choices = [
            (
                sous_acte.id_sous_acte,
                f"{sous_acte.code_sous_acte} - {sous_acte.libelle}"
            )
            for sous_acte in sous_actes
        ]

        form.fields["id_prestataire"].choices = [
            (
                prestataire.id_prestataire,
                f"{prestataire.code_prestataire} - {prestataire.raison_sociale}"
            )
            for prestataire in prestataires
        ]

    return render(
        request,
        "core/tarif_sous_acte_form.html",
        {
            "form": form,
            "titre": "Modifier le tarif sous-acte",
            "permissions": permissions,
        }
    )

def tarif_sous_acte_radier(request, id_tarif_sous_acte):
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
            "Vous n'avez pas l'autorisation de radier un tarif de sous-acte."
        )
        return redirect("tarifs_sous_actes")

    try:
        tarif = TarifSousActe.objects.get(
            id_tarif_sous_acte=id_tarif_sous_acte
        )
    except TarifSousActe.DoesNotExist:
        messages.error(
            request,
            "Tarif sous-acte introuvable."
        )
        return redirect("tarifs_sous_actes")

    if request.method == "POST":
        tarif.statut = "INACTIF"
        tarif.save()

        messages.success(
            request,
            "Tarif sous-acte radié avec succès."
        )

    return redirect("tarifs_sous_actes")

def tarifs_sous_actes(request):
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
            "Vous n'avez pas l'autorisation de consulter les tarifs des sous-actes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    id_sous_acte = request.GET.get("id_sous_acte", "").strip()
    id_prestataire = request.GET.get("id_prestataire", "").strip()
    statut = request.GET.get("statut", "").strip()

    tarifs = (
        TarifSousActe.objects
        .select_related(
            "id_sous_acte",
            "id_sous_acte__id_acte",
            "id_prestataire"
        )
        .all()
        .order_by("-id_tarif_sous_acte")
    )

    if recherche:
        tarifs = tarifs.filter(
            Q(id_sous_acte__code_sous_acte__icontains=recherche)
            | Q(id_sous_acte__libelle__icontains=recherche)
            | Q(id_sous_acte__id_acte__code_acte__icontains=recherche)
            | Q(id_sous_acte__id_acte__libelle__icontains=recherche)
            | Q(id_prestataire__code_prestataire__icontains=recherche)
            | Q(id_prestataire__raison_sociale__icontains=recherche)
        )

    if id_sous_acte:
        tarifs = tarifs.filter(
            id_sous_acte_id=id_sous_acte
        )

    if id_prestataire:
        tarifs = tarifs.filter(
            id_prestataire_id=id_prestataire
        )

    if statut:
        tarifs = tarifs.filter(
            statut=statut
        )

    sous_actes = (
        SousActe.objects
        .filter(statut="ACTIF")
        .select_related("id_acte")
        .order_by("libelle")
    )

    prestataires = (
        Prestataire.objects
        .filter(statut="ACTIF")
        .order_by("raison_sociale")
    )

    return render(
        request,
        "core/tarifs_sous_actes.html",
        {
            "tarifs": tarifs,
            "sous_actes": sous_actes,
            "prestataires": prestataires,
            "recherche": recherche,
            "id_sous_acte": id_sous_acte,
            "id_prestataire": id_prestataire,
            "statut": statut,
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
                    code_acte=_generer_code_acte(),
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

