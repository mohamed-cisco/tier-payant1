# core/views/documents.py
"""
Vues de gestion des documents.

Fonctions :
- documents : liste
- document_create : déposer
- document_modifier : modifier
- document_archiver : archiver
- document_ouvrir : ouvrir
"""

import os

from django.contrib import messages
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from core.forms import DocumentForm
from core.models import (
    Document,
    RolePermission,
)
from core.views.dashboard import enregistrer_audit


def document_create(request):
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

    if "DOCUMENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de déposer un document."
        )
        return redirect("documents")

    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                with transaction.atomic():
                    fichier = form.cleaned_data["fichier"]

                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    document = Document.objects.create(
                        nom_fichier=fichier.name,
                        type_document=(
                            form.cleaned_data["type_document"]
                            or getattr(fichier, "content_type", None)
                            or "INCONNU"
                        ),
                        extension=extension or None,
                        taille=fichier.size,
                        emplacement=chemin,
                        hash_fichier=hash_sha256.hexdigest(),
                        date_depot=timezone.now(),
                        id_utilisateur_id=id_utilisateur,
                        statut=form.cleaned_data["statut"],
                    )

                    enregistrer_audit(
                        request=request,
                        type_action="DEPOT_DOCUMENT",
                        module="DOCUMENT",
                        table_cible="document",
                        id_enregistrement=document.id_document,
                        nouvelle_valeur=(
                            f"Fichier : {document.nom_fichier}, "
                            f"Type : {document.type_document}, "
                            f"Taille : {document.taille} octets, "
                            f"Statut : {document.statut}"
                        ),
                        description=(
                            f"Dépôt du document "
                            f"{document.nom_fichier}"
                        ),
                    )

                messages.success(
                    request,
                    "Document déposé avec succès."
                )

                return redirect("documents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors du dépôt du document : {e}"
                )

    else:
        form = DocumentForm()

    return render(
        request,
        "core/document_form.html",
        {
            "form": form,
            "titre": "Déposer un document",
            "page": "documents",
        }
    )



def document_modifier(request, id_document):
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

    if "DOCUMENT_UPDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier un document."
        )
        return redirect("documents")

    try:
        document = Document.objects.get(
            id_document=id_document
        )
    except Document.DoesNotExist:
        messages.error(
            request,
            "Document introuvable."
        )
        return redirect("documents")

    if request.method == "POST":
        form = DocumentForm(
            request.POST,
            request.FILES
        )

        form.fields["fichier"].required = False

        if form.is_valid():
            try:
                ancienne_valeur = (
                    f"Nom : {document.nom_fichier}, "
                    f"Type : {document.type_document}, "
                    f"Statut : {document.statut}"
                )

                fichier = form.cleaned_data.get("fichier")

                if fichier:
                    extension = os.path.splitext(
                        fichier.name
                    )[1].lower()

                    hash_sha256 = hashlib.sha256()

                    for chunk in fichier.chunks():
                        hash_sha256.update(chunk)

                    fichier.seek(0)

                    chemin = default_storage.save(
                        f"documents/{fichier.name}",
                        fichier
                    )

                    document.nom_fichier = fichier.name
                    document.extension = (
                        extension or None
                    )
                    document.taille = fichier.size
                    document.emplacement = chemin
                    document.hash_fichier = (
                        hash_sha256.hexdigest()
                    )

                document.type_document = (
                    form.cleaned_data["type_document"]
                    or document.type_document
                )

                document.statut = (
                    form.cleaned_data["statut"]
                )

                document.save()

                nouvelle_valeur = (
                    f"Nom : {document.nom_fichier}, "
                    f"Type : {document.type_document}, "
                    f"Statut : {document.statut}"
                )

                enregistrer_audit(
                    request=request,
                    type_action="MODIFICATION",
                    module="DOCUMENT",
                    table_cible="document",
                    id_enregistrement=document.id_document,
                    ancienne_valeur=ancienne_valeur,
                    nouvelle_valeur=nouvelle_valeur,
                    description=(
                        f"Modification du document "
                        f"{document.nom_fichier}"
                    ),
                )

                messages.success(
                    request,
                    "Document modifié avec succès."
                )

                return redirect("documents")

            except Exception as e:
                messages.error(
                    request,
                    f"Erreur lors de la modification : {e}"
                )

    else:
        form = DocumentForm(
            initial={
                "type_document": document.type_document,
                "statut": document.statut,
            }
        )

        form.fields["fichier"].required = False

    return render(
        request,
        "core/document_form.html",
        {
            "form": form,
            "titre": "Modifier le document",
        }
    )



def document_archiver(request, id_document):
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

    if "DOCUMENT_DELETE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'archiver un document."
        )
        return redirect("documents")

    try:
        document = Document.objects.get(
            id_document=id_document
        )
    except Document.DoesNotExist:
        messages.error(
            request,
            "Document introuvable."
        )
        return redirect("documents")

    if request.method == "POST":
        try:
            ancienne_valeur = f"Statut : {document.statut}"

            document.statut = "ARCHIVE"
            document.save()

            enregistrer_audit(
                request=request,
                type_action="ARCHIVAGE",
                module="DOCUMENT",
                table_cible="document",
                id_enregistrement=document.id_document,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur="Statut : ARCHIVE",
                description=(
                    f"Archivage du document "
                    f"{document.nom_fichier}"
                ),
            )

            messages.success(
                request,
                "Document archivé avec succès."
            )

        except Exception as e:
            messages.error(
                request,
                f"Erreur lors de l'archivage : {e}"
            )

        return redirect("documents")

    return render(
        request,
        "core/document_archiver.html",
        {
            "document": document,
            "page": "documents",
        }
    )



def document_ouvrir(request, id_document):
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

    if "DOCUMENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ouvrir ce document."
        )
        return redirect("documents")

    try:
        document = Document.objects.get(
            id_document=id_document
        )
    except Document.DoesNotExist:
        messages.error(
            request,
            "Document introuvable."
        )
        return redirect("documents")

    if not default_storage.exists(document.emplacement):
        messages.error(
            request,
            "Le fichier physique est introuvable."
        )
        return redirect("documents")

    fichier = default_storage.open(
        document.emplacement,
        "rb"
    )

    response = FileResponse(
        fichier,
        as_attachment=False,
        filename=document.nom_fichier
    )

    return response




def documents(request):
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

    if "DOCUMENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les documents."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    documents = (
        Document.objects
        .select_related("id_utilisateur")
        .all()
        .order_by("-date_depot")
    )

    if recherche:
        documents = documents.filter(
            Q(nom_fichier__icontains=recherche)
            | Q(type_document__icontains=recherche)
            | Q(extension__icontains=recherche)
            | Q(hash_fichier__icontains=recherche)
        )

    if statut:
        documents = documents.filter(statut=statut)

    statuts = (
        Document.objects
        .exclude(statut__isnull=True)
        .exclude(statut="")
        .values_list("statut", flat=True)
        .distinct()
        .order_by("statut")
    )

    return render(
        request,
        "core/documents.html",
        {
            "documents": documents,
            "permissions": permissions,
            "recherche": recherche,
            "statut": statut,
            "statuts": statuts,
            "page": "documents",
        }
    )
