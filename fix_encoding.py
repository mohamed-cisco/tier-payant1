"""
Corrige :
  1. Le BOM UTF-8 (\ufeff) en début de fichier
  2. Les séquences UTF-8 mal décodées (Ã©, Ã¨, Ã , ...) dans les fichiers

À exécuter UNE SEULE FOIS à la racine du projet, puis à supprimer.
"""

import os
from pathlib import Path

# Racine du projet = dossier de ce script
RACINE = Path(__file__).resolve().parent

# Dossiers/fichiers à ignorer
IGNORER = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "node_modules", "media", "staticfiles",
    "fix_encoding.py",
}

# Motifs de remplacement (UTF-8 mal décodé -> correct)
REMPLACEMENTS = [
    ("Ã©", "é"),
    ("Ã¨", "è"),
    ("Ãª", "ê"),
    ("Ã«", "ë"),
    ("Ã ", "à"),
    ("Ã¢", "â"),
    ("Ã¤", "ä"),
    ("Ã®", "î"),
    ("Ã¯", "ï"),
    ("Ã´", "ô"),
    ("Ã¶", "ö"),
    ("Ã¹", "ù"),
    ("Ã»", "û"),
    ("Ã¼", "ü"),
    ("Ã§", "ç"),
    ("Ã‰", "É"),
    ("Ãˆ", "È"),
    ("ÃŠ", "Ê"),
    ("Ã€", "À"),
    ("Ã‚", "Â"),
    ("ÃŽ", "Î"),
    ("Ã”", "Ô"),
    ("Ã™", "Ù"),
    ("Ã›", "Û"),
    ("Ã‡", "Ç"),
    ("Å“", "œ"),
    ("â€™", "'"),
    ("â€œ", '"'),
    ("â€\x9d", '"'),
    ("â€“", "–"),
    ("â€”", "—"),
    ("â€¦", "…"),
    ("Â ", " "),
    ("Â°", "°"),
    ("Â«", "«"),
    ("Â»", "»"),
]

# Extensions à traiter
EXTENSIONS = {".py", ".html", ".htm", ".txt", ".md", ".css", ".js", ".json", ".csv", ".xml"}


def corriger_fichier(chemin: Path):
    """Retourne (modifié, nb_bom, nb_remplacements)."""
    try:
        contenu_brut = chemin.read_bytes()
    except Exception as e:
        print(f"  [!] Impossible de lire {chemin} : {e}")
        return False, 0, 0

    # 1. Détection BOM UTF-8
    bom = 0
    if contenu_brut.startswith(b"\xef\xbb\xbf"):
        contenu_brut = contenu_brut[3:]
        bom = 1

    # 2. Décodage strict UTF-8
    try:
        texte = contenu_brut.decode("utf-8")
    except UnicodeDecodeError:
        try:
            texte = contenu_brut.decode("latin-1")
        except Exception as e:
            print(f"  [!] Décodage impossible {chemin} : {e}")
            return False, 0, 0

    # 3. Remplacements
    total = 0
    for avant, apres in REMPLACEMENTS:
        n = texte.count(avant)
        if n:
            texte = texte.replace(avant, apres)
            total += n

    # 4. Écriture seulement si modifié
    if bom or total:
        chemin.write_bytes(texte.encode("utf-8"))
        return True, bom, total

    return False, 0, 0


def main():
    total_bom = 0
    total_remplaces = 0
    total_fichiers = 0

    for dossier, sous_dossiers, fichiers in os.walk(RACINE):
        sous_dossiers[:] = [d for d in sous_dossiers if d not in IGNORER]

        for nom in fichiers:
            chemin = Path(dossier) / nom
            if chemin.name in IGNORER:
                continue
            if chemin.suffix.lower() not in EXTENSIONS:
                continue

            modifie, bom, n = corriger_fichier(chemin)
            if modifie:
                rel = chemin.relative_to(RACINE)
                print(f"[OK] {rel}  (BOM: {bom}, remplacements: {n})")
                total_bom += bom
                total_remplaces += n
                total_fichiers += 1

    print()
    print("=" * 50)
    print(f"Fichiers corriges : {total_fichiers}")
    print(f"BOM supprimes     : {total_bom}")
    print(f"Caracteres fixes  : {total_remplaces}")
    print("=" * 50)


if __name__ == "__main__":
    main()
