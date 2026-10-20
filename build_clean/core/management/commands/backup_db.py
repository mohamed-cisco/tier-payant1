"""
Commande Django pour sauvegarder la base de données au format JSON.

Usage :
    python manage.py backup_db
    python manage.py backup_db --keep 60

Stratégie :
    - Export JSON de toute la base via dumpdata
    - Compression gzip
    - Nom : backup_YYYY-MM-DD_HH-MM-SS.json.gz
    - Rotation automatique (garde les N derniers jours)
"""

import os
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = "Sauvegarde la base de données au format JSON compressé"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            type=int,
            default=30,
            help="Nombre de jours de sauvegarde à conserver (défaut: 30)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Dossier de destination (défaut: <BASE_DIR>/backups)",
        )

    def handle(self, *args, **options):
        keep_days = options["keep"]
        output_dir = options["output"] or os.path.join(settings.BASE_DIR, "backups")

        # Créer le dossier s'il n'existe pas
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Nom du fichier
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nom_fichier = f"backup_{timestamp}.json"
        chemin_json = os.path.join(output_dir, nom_fichier)
        chemin_gz = chemin_json + ".gz"

        self.stdout.write("🔄 Sauvegarde de la base de données...")

        try:
            # Exporter toute la base au format JSON
            with open(chemin_json, "w", encoding="utf-8") as f:
                call_command(
                    "dumpdata",
                    indent=2,
                    stdout=f,
                    exclude=[
                        "contenttypes",
                        "auth.permission",
                        "sessions",
                    ],
                )

            # Compresser
            self.stdout.write("📦 Compression...")
            with open(chemin_json, "rb") as f_in:
                with gzip.open(chemin_gz, "wb") as f_out:
                    f_out.write(f_in.read())

            # Supprimer le fichier non compressé
            os.remove(chemin_json)

            # Taille
            taille_ko = os.path.getsize(chemin_gz) / 1024

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Sauvegarde réussie : {chemin_gz} ({taille_ko:.1f} Ko)"
                )
            )

                        # Rotation
            self.stdout.write(f"🧹 Nettoyage (> {keep_days} jours)...")
            self._rotation(output_dir, keep_days)

            # Sauvegarder les fichiers media (optionnel)
            self._backup_media(output_dir, timestamp)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Erreur : {e}"))

    def _backup_media(self, output_dir, timestamp):
        """Sauvegarde le dossier media/ dans une archive ZIP."""
        import zipfile

        media_dir = os.path.join(settings.BASE_DIR, "media")

        if not os.path.exists(media_dir):
            self.stdout.write("   ℹ️ Pas de dossier media/ à sauvegarder")
            return

        # Vérifier s'il y a des fichiers
        fichiers = [f for f in Path(media_dir).rglob("*") if f.is_file()]
        if not fichiers:
            self.stdout.write("   ℹ️ Dossier media/ vide")
            return

        self.stdout.write(f"📎 Sauvegarde de {len(fichiers)} fichier(s) media...")

        nom_zip = f"media_{timestamp}.zip"
        chemin_zip = os.path.join(output_dir, nom_zip)

        with zipfile.ZipFile(chemin_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for fichier in fichiers:
                arcname = fichier.relative_to(media_dir)
                zf.write(fichier, arcname)

        taille_mo = os.path.getsize(chemin_zip) / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(
                f"   ✅ Media sauvegardé : {nom_zip} ({taille_mo:.2f} MB)"
            )
        )

    def _rotation(self, dossier, keep_days):
        """Supprime les sauvegardes plus anciennes que keep_days jours."""
        limite = datetime.now() - timedelta(days=keep_days)
        nb_supprimes = 0

        for fichier in Path(dossier).glob("backup_*.json.gz"):
            try:
                nom = fichier.stem.replace(".json", "")
                date_str = nom.replace("backup_", "")
                date_fichier = datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S")

                if date_fichier < limite:
                    fichier.unlink()
                    nb_supprimes += 1
                    self.stdout.write(f"   🗑️ Supprimé : {fichier.name}")
            except (ValueError, IndexError):
                continue

        if nb_supprimes == 0:
            self.stdout.write("   ✅ Aucune sauvegarde à supprimer")
        else:
            self.stdout.write(f"   ✅ {nb_supprimes} sauvegarde(s) supprimée(s)")