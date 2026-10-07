def adhesion_export_excel(request):

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

    if "ADHESION_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les adhésions."
        )
        return redirect("adhesions")

    import openpyxl
    from openpyxl.styles import Font
    from django.http import HttpResponse

    adhesions_list = (
        Adhesion.objects
        .select_related(
            "id_adherent",
            "id_adherent__id_personne",
            "id_contrat",
            "id_contrat__id_souscripteur",
        )
        .all()
        .order_by("numero_adhesion")
    )

    workbook = openpyxl.Workbook()
    feuille = workbook.active
    feuille.title = "Adhesions"

    entetes = [
        "Numéro adhésion",
        "Numéro adhérent",
        "Nom",
        "Prénom",
        "Numéro contrat",
        "Souscripteur",
        "Date début",
        "Date fin",
        "Statut",
        "Date création",
    ]

    feuille.append(entetes)

    for cellule in feuille[1]:
        cellule.font = Font(bold=True)

    for adhesion in adhesions_list:

        personne = adhesion.id_adherent.id_personne
        contrat = adhesion.id_contrat
        souscripteur = contrat.id_souscripteur

        feuille.append([
            adhesion.numero_adhesion,
            adhesion.id_adherent.numero_adherent,
            personne.nom,
            personne.prenom,
            contrat.numero_contrat,
            souscripteur.raison_sociale,
            adhesion.date_debut,
            adhesion.date_fin,
            adhesion.statut,
            adhesion.date_creation,
        ])

    for colonne in feuille.columns:

        longueur_max = 0
        lettre_colonne = colonne[0].column_letter

        for cellule in colonne:

            try:
                longueur = (
                    len(str(cellule.value))
                    if cellule.value
                    else 0
                )

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
    ] = 'attachment; filename="adhesions.xlsx"'

    workbook.save(response)

    return response

