def adherent_import_excel(request):

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

    if "ADHERENT_CREATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'importer des adhérents."
        )
        return redirect("adherents")

    if request.method == "POST":

        form = ImportAdherentForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            try:

                import openpyxl

                fichier = form.cleaned_data["fichier"]

                if not fichier.name.lower().endswith(".xlsx"):
                    messages.error(
                        request,
                        "Veuillez sélectionner un fichier Excel au format .xlsx."
                    )
                    return redirect("adherent_import_excel")

                workbook = openpyxl.load_workbook(
                    fichier,
                    data_only=True
                )

                feuille = workbook.active

                nombre_importes = 0
                erreurs = []

                with transaction.atomic():

                    for numero_ligne, ligne in enumerate(
                        feuille.iter_rows(
                            min_row=2,
                            values_only=True
                        ),
                        start=2
                    ):

                        if not any(ligne):
                            continue

                        nom = ligne[0]
                        prenom = ligne[1]
                        date_naissance = ligne[2]
                        sexe = ligne[3]
                        adresse = ligne[4]
                        telephone = ligne[5]
                        email = ligne[6]
                        date_adhesion = ligne[7]

                        if not nom or not prenom:

                            erreurs.append(
                                f"Ligne {numero_ligne} : "
                                "Nom ou prénom manquant."
                            )

                            continue

                        # Vérification doublon
                        doublon = (
                            Adherent.objects
                            .filter(
                                statut="ACTIF",
                                id_personne__nom__iexact=str(nom).strip(),
                                id_personne__prenom__iexact=str(prenom).strip(),
                                id_personne__date_naissance=date_naissance,
                            )
                            .first()
                        )

                        if doublon:

                            erreurs.append(
                                f"Ligne {numero_ligne} : "
                                f"Cet adhérent existe déjà "
                                f"({doublon.numero_adherent})."
                            )

                            continue

                        # Création de la personne
                        personne = Personne.objects.create(

                            numero_personne=_generer_numero_personne(),

                            nom=str(nom).strip(),

                            prenom=str(prenom).strip(),

                            date_naissance=date_naissance,

                            sexe=(
                                str(sexe).strip()
                                if sexe
                                else None
                            ),

                            adresse=(
                                str(adresse).strip()
                                if adresse
                                else None
                            ),

                            telephone=(
                                str(telephone).strip()
                                if telephone
                                else None
                            ),

                            email=(
                                str(email).strip()
                                if email
                                else None
                            ),

                            statut="ACTIF",

                            date_creation=timezone.now(),

                            date_modification=None,
                        )

                        # Création de l'adhérent
                        adherent = Adherent.objects.create(

                            id_personne=personne,

                            numero_adherent=_generer_numero_adherent(),

                            date_creation=timezone.now(),

                            statut="ACTIF",

                            date_adhesion=date_adhesion,

                            date_radiation=None,
                        )

                        # Audit
                        enregistrer_audit(
                            request=request,
                            type_action="IMPORTATION",
                            module="ADHERENTS",
                            table_cible="adherent",
                            id_enregistrement=adherent.id_adherent,
                            nouvelle_valeur=(
                                f"Import Excel - "
                                f"Adhérent : {adherent.numero_adherent}"
                            ),
                            description=(
                                f"Importation de l'adhérent "
                                f"{adherent.numero_adherent}"
                            ),
                        )

                        nombre_importes += 1


                if nombre_importes > 0:

                    messages.success(
                        request,
                        f"{nombre_importes} adhérent(s) importé(s) "
                        "avec succès."
                    )

                if erreurs:

                    for erreur in erreurs[:10]:

                        messages.warning(
                            request,
                            erreur
                        )

                    if len(erreurs) > 10:

                        messages.warning(
                            request,
                            f"{len(erreurs) - 10} autre(s) erreur(s)."
                        )

                return redirect("adherents")

            except Exception as e:

                messages.error(
                    request,
                    f"Erreur lors de l'importation : {str(e)}"
                )

    else:

        form = ImportAdherentForm()

    return render(
        request,
        "core/adherent_import_excel.html",
        {
            "form": form,
        }
    )
