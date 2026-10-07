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
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
import openpyxl
from openpyxl.styles import Font
from django.http import HttpResponse

from core.forms import (
    ConventionForm,
    PrestataireForm,
)
from core.models import (
    Convention,
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

def conventions(request):
    """Liste des conventions."""
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

    if "CONVENTION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les conventions."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    conventions_liste = (
        Convention.objects
        .select_related("id_prestataire")
        .all()
        .order_by("-date_debut", "numero_convention")
    )

    if recherche:
        conventions_liste = conventions_liste.filter(
            Q(numero_convention__icontains=recherche)
            | Q(id_prestataire__code_prestataire__icontains=recherche)
            | Q(id_prestataire__raison_sociale__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        conventions_liste = conventions_liste.filter(statut=statut)

    statuts = (
        Convention.objects
        .exclude(statut__isnull=True)
        .exclude(statut="")
        .values_list("statut", flat=True)
        .distinct()
        .order_by("statut")
    )

    return render(
        request,
        "core/conventions.html",
        {
            "conventions": conventions_liste,
            "permissions": permissions,
            "recherche": recherche,
            "statut": statut,
            "statuts": statuts,
            "page": "conventions",
        }
    )


def _generer_numero_convention():
    """Génère un numéro unique de convention."""
    annee = timezone.now().year
    prefixe = f"CONV-{annee}-"

    numeros = (
        Convention.objects
        .filter(numero_convention__startswith=prefixe)
        .values_list("numero_convention", flat=True)
    )

    valeurs = []
    for numero in numeros:
        try:
            valeurs.append(int(numero.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1
    numero_convention = f"{prefixe}{prochain:04d}"

    while Convention.objects.filter(numero_convention=numero_convention).exists():
        prochain += 1
        numero_convention = f"{prefixe}{prochain:04d}"

    return numero_convention


def convention_create(request):
    """Créer une nouvelle convention."""
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

    if "CONVENTION_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer une convention."
        )
        return redirect("conventions")

    if request.method == "POST":
        form = ConventionForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    convention = Convention.objects.create(
                        id_prestataire=form.cleaned_data["id_prestataire"],
                        numero_convention=_generer_numero_convention(),
                        date_debut=form.cleaned_data["date_debut"],
                        date_fin=form.cleaned_data["date_fin"],
                        statut=form.cleaned_data["statut"],
                        description=form.cleaned_data["description"] or None,
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="CREATION",
                        module="CONVENTION",
                        table_cible="convention",
                        id_enregistrement=convention.id_convention,
                        nouvelle_valeur=(
                            f"Numéro : {convention.numero_convention}, "
                            f"Prestataire : {convention.id_prestataire.raison_sociale}, "
                            f"Statut : {convention.statut}"
                        ),
                        description=f"Création de la convention {convention.numero_convention}",
                    )

                messages.success(request, "Convention créée avec succès.")
                return redirect("conventions")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la création de la convention : {e}"
                )
    else:
        form = ConventionForm()

    return render(
        request,
        "core/convention_form.html",
        {
            "form": form,
            "titre": "Nouvelle convention",
            "page": "conventions",
        }
    )


def convention_modifier(request, id_convention):
    """Modifier une convention existante."""
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

    if "CONVENTION_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier une convention."
        )
        return redirect("conventions")

    try:
        convention = (
            Convention.objects
            .select_related("id_prestataire")
            .get(id_convention=id_convention)
        )
    except Convention.DoesNotExist:
        messages.error(request, "Convention introuvable.")
        return redirect("conventions")

    if request.method == "POST":
        form = ConventionForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    ancienne_valeur = (
                        f"Numéro : {convention.numero_convention}, "
                        f"Prestataire : {convention.id_prestataire.raison_sociale}, "
                        f"Date début : {convention.date_debut}, "
                        f"Date fin : {convention.date_fin}, "
                        f"Statut : {convention.statut}"
                    )

                    convention.id_prestataire = form.cleaned_data["id_prestataire"]
                    convention.date_debut = form.cleaned_data["date_debut"]
                    convention.date_fin = form.cleaned_data["date_fin"]
                    convention.statut = form.cleaned_data["statut"]
                    convention.description = form.cleaned_data["description"] or None
                    convention.save()

                    nouvelle_valeur = (
                        f"Numéro : {convention.numero_convention}, "
                        f"Prestataire : {convention.id_prestataire.raison_sociale}, "
                        f"Date début : {convention.date_debut}, "
                        f"Date fin : {convention.date_fin}, "
                        f"Statut : {convention.statut}"
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="MODIFICATION",
                        module="CONVENTION",
                        table_cible="convention",
                        id_enregistrement=convention.id_convention,
                        ancienne_valeur=ancienne_valeur,
                        nouvelle_valeur=nouvelle_valeur,
                        description=f"Modification de la convention {convention.numero_convention}",
                    )

                messages.success(request, "Convention modifiée avec succès.")
                return redirect("conventions")

            except Exception as e:
                messages.error(request, f"Erreur lors de la modification : {e}")
    else:
        form = ConventionForm(initial={
            "id_prestataire": convention.id_prestataire,
            "numero_convention": convention.numero_convention,
            "date_debut": convention.date_debut,
            "date_fin": convention.date_fin,
            "statut": convention.statut,
            "description": convention.description,
        })

    return render(
        request,
        "core/convention_form.html",
        {
            "form": form,
            "titre": "Modifier la convention",
        }
    )


def convention_cloturer(request, id_convention):
    """Clôturer une convention."""
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

    if "CONVENTION_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de clôturer une convention."
        )
        return redirect("conventions")

    try:
        convention = Convention.objects.get(id_convention=id_convention)
    except Convention.DoesNotExist:
        messages.error(request, "Convention introuvable.")
        return redirect("conventions")

    if request.method == "POST":
        try:
            ancienne_valeur = f"Statut : {convention.statut}"

            convention.statut = "CLOTUREE"
            convention.date_fin = timezone.now().date()
            convention.save()

            enregistrer_audit(
                request=request,
                type_action="CLOTURE",
                module="CONVENTION",
                table_cible="convention",
                id_enregistrement=convention.id_convention,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=(
                    f"Statut : {convention.statut}, "
                    f"Date fin : {convention.date_fin}"
                ),
                description=f"Clôture de la convention {convention.numero_convention}",
            )

            messages.success(request, "Convention clôturée avec succès.")

        except Exception as e:
            messages.error(request, f"Erreur lors de la clôture : {e}")

        return redirect("conventions")

    return render(
        request,
        "core/convention_cloturer.html",
        {
            "convention": convention,
            "page": "conventions",
        }
    )



def prestataire_import_excel(request):

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

    if "PRESTATAIRE_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'importer les prestataires."
        )
        return redirect("prestataires")

    if request.method == "POST":

        fichier = request.FILES.get("fichier")

        if not fichier:

            messages.error(
                request,
                "Veuillez sélectionner un fichier Excel."
            )

            return redirect(
                "prestataire_import_excel"
            )

        if not fichier.name.endswith(".xlsx"):

            messages.error(
                request,
                "Le fichier doit être au format .xlsx"
            )

            return redirect(
                "prestataire_import_excel"
            )

        try:

            import openpyxl

            workbook = openpyxl.load_workbook(
                fichier
            )

            feuille = workbook.active

            nombre_importes = 0
            nombre_doublons = 0

            with transaction.atomic():

                for ligne in feuille.iter_rows(
                    min_row=2,
                    values_only=True
                ):

                    raison_sociale = ligne[1]

                    type_prestataire = ligne[2]

                    nif = ligne[3]

                    registre_commerce = ligne[4]

                    adresse = ligne[5]

                    telephone = ligne[6]

                    email = ligne[7]

                    statut = ligne[8]


                    if not raison_sociale:

                      continue


                    Prestataire.objects.create(

                        code_prestataire=_generer_code_prestataire(),

                        raison_sociale=str(
                            raison_sociale or ""
                        ).strip(),

                        type_prestataire=str(
                            type_prestataire or ""
                        ).strip(),

                        nif=str(
                            nif or ""
                        ).strip() or None,

                        registre_commerce=str(
                            registre_commerce or ""
                        ).strip() or None,

                        adresse=str(
                            adresse or ""
                        ).strip() or None,

                        telephone=str(
                            telephone or ""
                        ).strip() or None,

                        email=str(
                            email or ""
                        ).strip() or None,

                        statut=str(
                            statut or "ACTIF"
                        ).strip(),

                        date_creation=timezone.now(),

                    )

                    nombre_importes += 1


            messages.success(
                request,
                f"{nombre_importes} prestataire(s) importé(s) avec succès."
            )


            if nombre_doublons > 0:

                messages.warning(
                    request,
                    f"{nombre_doublons} doublon(s) ignoré(s)."
                )


            return redirect("prestataires")


        except Exception as e:

            messages.error(
                request,
                f"Erreur lors de l'importation : {str(e)}"
            )


    return render(
        request,
        "core/prestataire_import_excel.html",
        {
            "permissions": permissions,
            "page": "prestataires",
        }
    )
def prestataire_export_excel(request):

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

    if "PRESTATAIRE_VIEW" not in permissions:

        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les prestataires."
        )

        return redirect("prestataires")


    import openpyxl

    from openpyxl.styles import Font

    from django.http import HttpResponse


    prestataires_list = (
        Prestataire.objects
        .all()
        .order_by("code_prestataire")
    )


    workbook = openpyxl.Workbook()

    feuille = workbook.active

    feuille.title = "Prestataires"


    entetes = [

        "Code prestataire",

        "Raison sociale",

        "Type prestataire",

        "NIF",

        "Registre de commerce",

        "Adresse",

        "Téléphone",

        "Email",

        "Statut",

        "Date création",

    ]


    feuille.append(entetes)


    for cellule in feuille[1]:

        cellule.font = Font(bold=True)


    for prestataire in prestataires_list:

        feuille.append([

            prestataire.code_prestataire,

            prestataire.raison_sociale,

            prestataire.type_prestataire,

            prestataire.nif,

            prestataire.registre_commerce,

            prestataire.adresse,

            prestataire.telephone,

            prestataire.email,

            prestataire.statut,

            prestataire.date_creation,

        ])


    for colonne in feuille.columns:

        longueur_max = 0

        lettre_colonne = colonne[0].column_letter


        for cellule in colonne:

            try:

                longueur = len(
                    str(cellule.value)
                ) if cellule.value else 0


                if longueur > longueur_max:

                    longueur_max = longueur

            except Exception:

                pass


        feuille.column_dimensions[
            lettre_colonne
        ].width = min(longueur_max + 2, 50)


    response = HttpResponse(

        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )

    )


    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="prestataires.xlsx"'
    )


    workbook.save(response)


    return response

# ============================================================
# CHAMPS PERSONNALISÉS
# ============================================================

