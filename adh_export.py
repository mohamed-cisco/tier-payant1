def adherent_export_excel(request):

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

    if "ADHERENT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'exporter les adhérents."
        )
        return redirect("adherents")

    import openpyxl

    from openpyxl.styles import Font
    from django.http import HttpResponse


    adherents_list = (
        Adherent.objects
        .select_related("id_personne")
        .order_by("numero_adherent")
    )


    workbook = openpyxl.Workbook()

    feuille = workbook.active

    feuille.title = "Adherents"


    entetes = [

        "Numéro adhérent",

        "Numéro personne",

        "Nom",

        "Prénom",

        "Date de naissance",

        "Sexe",

        "Adresse",

        "Téléphone",

        "Email",

        "Date adhésion",

        "Statut",

    ]


    feuille.append(entetes)


    for cellule in feuille[1]:

        cellule.font = Font(bold=True)


    for adherent in adherents_list:

        personne = adherent.id_personne

        feuille.append([

            adherent.numero_adherent,

            personne.numero_personne,

            personne.nom,

            personne.prenom,

            personne.date_naissance,

            personne.sexe,

            personne.adresse,

            personne.telephone,

            personne.email,

            adherent.date_adhesion,

            adherent.statut,

        ])


    for colonne in feuille.columns:

        longueur_max = 0

        lettre_colonne = colonne[0].column_letter


        for cellule in colonne:

            try:

                longueur = len(
                    str(cellule.value)
                )

                if longueur > longueur_max:

                    longueur_max = longueur

            except Exception:

                pass


        feuille.column_dimensions[
            lettre_colonne
        ].width = longueur_max + 2


    response = HttpResponse(

        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    )


    response[
        "Content-Disposition"
    ] = (

        'attachment; filename="adherents.xlsx"'

    )


    workbook.save(response)


    return response
