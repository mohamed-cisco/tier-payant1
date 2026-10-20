# core/views/backup.py
"""
Vues de gestion des sauvegardes.

Fonctions :
- _dossier_backups : retourne le chemin du dossier backups
- sauvegardes_liste : liste des sauvegardes
- sauvegarde_creer : crée une sauvegarde
- sauvegarde_telecharger : télécharge une sauvegarde
- sauvegarde_supprimer : supprime une sauvegarde
- sauvegarde_restaurer : restaure une sauvegarde
"""

import os
import gzip
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.management import call_command
from django.http import FileResponse
from django.shortcuts import redirect, render

from core.models import RolePermission


def _dossier_backups():
    """Retourne le chemin absolu du dossier backups."""
    return os.path.join(settings.BASE_DIR, "backups")


def sauvegardes_liste(request):
    """Liste des sauvegardes disponibles."""
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

    if "USER_VIEW" not in permissions and "ROLE_VIEW" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("accueil")

    # Liste des fichiers de sauvegarde
    dossier = _dossier_backups()
    Path(dossier).mkdir(parents=True, exist_ok=True)

    fichiers = []
    for f in Path(dossier).glob("backup_*.json.gz"):
        try:
            stat = f.stat()
            nom = f.name.replace(".json.gz", "").replace("backup_", "")
            date_backup = datetime.strptime(nom, "%Y-%m-%d_%H-%M-%S")
            fichiers.append({
                "nom": f.name,
                "date": date_backup,
                "taille_ko": round(stat.st_size / 1024, 1),
            })
        except Exception:
            continue

    # Trier par date (plus récent en premier)
    fichiers.sort(key=lambda x: x["date"], reverse=True)

    # Taille totale
    taille_totale_ko = sum(f["taille_ko"] for f in fichiers)

    return render(
        request,
        "core/sauvegardes/liste.html",
        {
            "fichiers": fichiers,
            "nombre_sauvegardes": len(fichiers),
            "taille_totale_ko": round(taille_totale_ko, 1),
            "permissions": permissions,
            "page": "sauvegardes",
        }
    )


def sauvegarde_creer(request):
    """Crée une nouvelle sauvegarde."""
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

    if "USER_CREATE" not in permissions and "ROLE_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("sauvegardes_liste")

    if request.method == "POST":
        try:
            dossier = _dossier_backups()
            Path(dossier).mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            nom_fichier = f"backup_{timestamp}.json"
            chemin_json = os.path.join(dossier, nom_fichier)
            chemin_gz = chemin_json + ".gz"

            # Exporter la base
            with open(chemin_json, "w", encoding="utf-8") as f:
                call_command(
                    "dumpdata",
                    indent=2,
                    stdout=f,
                    exclude=["contenttypes", "auth.permission", "sessions"],
                )

            # Compresser
            with open(chemin_json, "rb") as f_in:
                with gzip.open(chemin_gz, "wb") as f_out:
                    f_out.write(f_in.read())

            os.remove(chemin_json)

            taille_ko = round(os.path.getsize(chemin_gz) / 1024, 1)

            # Audit
            from core.views_old import enregistrer_audit
            enregistrer_audit(
                request=request,
                type_action="SAUVEGARDE",
                module="SYSTEME",
                table_cible="backup",
                description=f"Sauvegarde créée : {nom_fichier}.gz ({taille_ko} Ko)",
            )

            messages.success(
                request,
                f"✅ Sauvegarde créée avec succès ({taille_ko} Ko)."
            )
        except Exception as e:
            messages.error(request, f"❌ Erreur : {e}")

    return redirect("sauvegardes_liste")


def sauvegarde_telecharger(request, nom_fichier):
    """Télécharge une sauvegarde."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    # Sécuriser le nom (pas de chemin)
    nom_fichier = os.path.basename(nom_fichier)

    if not nom_fichier.startswith("backup_") or not nom_fichier.endswith(".json.gz"):
        messages.error(request, "Nom de fichier invalide.")
        return redirect("sauvegardes_liste")

    chemin = os.path.join(_dossier_backups(), nom_fichier)

    if not os.path.exists(chemin):
        messages.error(request, "Fichier introuvable.")
        return redirect("sauvegardes_liste")

    # Audit
    from core.views_old import enregistrer_audit
    enregistrer_audit(
        request=request,
        type_action="TELECHARGEMENT_SAUVEGARDE",
        module="SYSTEME",
        table_cible="backup",
        description=f"Téléchargement de la sauvegarde : {nom_fichier}",
    )

    return FileResponse(
        open(chemin, "rb"),
        as_attachment=True,
        filename=nom_fichier,
    )


def sauvegarde_supprimer(request, nom_fichier):
    """Supprime une sauvegarde."""
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

    if "USER_UPDATE" not in permissions and "ROLE_UPDATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("sauvegardes_liste")

    nom_fichier = os.path.basename(nom_fichier)

    if not nom_fichier.startswith("backup_") or not nom_fichier.endswith(".json.gz"):
        messages.error(request, "Nom de fichier invalide.")
        return redirect("sauvegardes_liste")

    chemin = os.path.join(_dossier_backups(), nom_fichier)

    if request.method == "POST":
        try:
            if os.path.exists(chemin):
                os.remove(chemin)

                from core.views_old import enregistrer_audit
                enregistrer_audit(
                    request=request,
                    type_action="SUPPRESSION_SAUVEGARDE",
                    module="SYSTEME",
                    table_cible="backup",
                    description=f"Suppression de la sauvegarde : {nom_fichier}",
                )

                messages.success(request, "Sauvegarde supprimée.")
            else:
                messages.error(request, "Fichier introuvable.")
        except Exception as e:
            messages.error(request, f"Erreur : {e}")

    return redirect("sauvegardes_liste")


def sauvegarde_restaurer(request, nom_fichier):
    """Restaure une sauvegarde (⚠️ ÉCRASE la base actuelle)."""
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

    if "USER_CREATE" not in permissions and "ROLE_CREATE" not in permissions:
        messages.error(request, "Vous n'avez pas l'autorisation.")
        return redirect("sauvegardes_liste")

    nom_fichier = os.path.basename(nom_fichier)

    if not nom_fichier.startswith("backup_") or not nom_fichier.endswith(".json.gz"):
        messages.error(request, "Nom de fichier invalide.")
        return redirect("sauvegardes_liste")

    chemin = os.path.join(_dossier_backups(), nom_fichier)

    if not os.path.exists(chemin):
        messages.error(request, "Fichier introuvable.")
        return redirect("sauvegardes_liste")

    if request.method == "POST":
        try:
            # Décompresser vers un fichier temporaire
            chemin_temp = chemin.replace(".gz", "")

            with gzip.open(chemin, "rb") as f_in:
                with open(chemin_temp, "wb") as f_out:
                    f_out.write(f_in.read())

            # Charger les données
            call_command("loaddata", chemin_temp)

            # Nettoyer
            os.remove(chemin_temp)

            from core.views_old import enregistrer_audit
            enregistrer_audit(
                request=request,
                type_action="RESTAURATION",
                module="SYSTEME",
                table_cible="backup",
                description=f"Restauration de la sauvegarde : {nom_fichier}",
            )

            messages.success(
                request,
                f"✅ Restauration réussie depuis {nom_fichier}."
            )
        except Exception as e:
            messages.error(request, f"❌ Erreur de restauration : {e}")

    return redirect("sauvegardes_liste")