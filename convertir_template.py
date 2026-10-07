import re
import sys
import os

def convertir_template(chemin_fichier, nom_template, titre, sous_titre):
    """
    Convertit un template HTML autonome en template qui étend base.html.
    """
    with open(chemin_fichier, 'r', encoding='utf-8') as f:
        contenu = f.read()
    
    # Extraire le CSS (entre <style> et </style>)
    css_match = re.search(r'<style>(.*?)</style>', contenu, re.DOTALL)
    css = css_match.group(1) if css_match else ""
    
    # Extraire le contenu du body (entre <body> et </body>)
    body_match = re.search(r'<body[^>]*>(.*?)</body>', contenu, re.DOTALL)
    body = body_match.group(1) if body_match else contenu
    
    # Construire le nouveau template
    nouveau_template = f'''{{% extends "core/base.html" %}}
{{% load static %}}

{{% block title %}}{titre} - Tiers Payant{{% endblock %}}
{{% block header_title %}}{titre}{{% endblock %}}
{{% block header_sub %}}{sous_titre}{{% endblock %}}

{{% block extra_css %}}
<style>
{css}
</style>
{{% endblock %}}

{{% block content %}}
{body}
{{% endblock %}}
'''
    
    # Sauvegarder le nouveau template
    with open(chemin_fichier, 'w', encoding='utf-8') as f:
        f.write(nouveau_template)
    
    print(f"✅ {os.path.basename(chemin_fichier)} converti")
    print(f"   CSS : {len(css)} caractères")
    print(f"   Body : {len(body)} caractères")

# Templates à convertir
TEMPLATES = [
    {
        "chemin": "core/templates/core/prise_en_charge_details.html",
        "titre": "Détail de la prise en charge",
        "sous_titre": "Informations et actes pris en charge",
    },
    {
        "chemin": "core/templates/core/demande_tp_details.html",
        "titre": "Détail de la demande TP",
        "sous_titre": "Gestion des demandes de tiers payant",
    },
    {
        "chemin": "core/templates/core/adherent_detail.html",
        "titre": "Détail adhérent",
        "sous_titre": "Informations de l'adhérent",
    },
    {
        "chemin": "core/templates/core/contrat_detail.html",
        "titre": "Détail du contrat",
        "sous_titre": "Informations du contrat",
    },
    {
        "chemin": "core/templates/core/garantie_detail.html",
        "titre": "Détail de la garantie",
        "sous_titre": "Informations de la garantie",
    },
    {
        "chemin": "core/templates/core/acte_detail.html",
        "titre": "Détail de l'acte",
        "sous_titre": "Informations de l'acte",
    },
]

print("🚀 Conversion des templates...\n")

for t in TEMPLATES:
    if os.path.exists(t["chemin"]):
        convertir_template(
            t["chemin"],
            t["titre"],
            t["titre"],
            t["sous_titre"],
        )
    else:
        print(f"❌ {t['chemin']} introuvable")

print("\n🎉 Terminé !")
