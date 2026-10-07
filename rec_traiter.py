def recours_traiter(request, id_recours):
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

    if "RECOURS_VALIDATE" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de traiter les recours."
        )
        return redirect("recours")

    try:
        recours_obj = Recours.objects.get(id_recours=id_recours)
    except Recours.DoesNotExist:
        messages.error(request, "Recours introuvable.")
        return redirect("recours")

    if recours_obj.statut != "EN_ATTENTE":
        messages.error(
            request,
            "Ce recours a déjà été traité."
        )
        return redirect("recours")

    if request.method == "POST":
        form = DecisionRecoursForm(request.POST)

        if form.is_valid():
            decision = form.save(commit=False)

            decision.id_recours = recours_obj
            decision.utilisateur_decision = (
                request.session.get("nom_utilisateur")
            )

            decision.save()

            if decision.type_decision == "ACCEPTEE":
             recours_obj.statut = "ACCEPTEE"

            elif decision.type_decision == "REJETEE":
             recours_obj.statut = "REJETEE"

            elif decision.type_decision == "ACCEPTEE_PARTIELLEMENT":
             recours_obj.statut = "ACCEPTEE_PARTIELLEMENT"

            recours_obj.date_cloture = timezone.now().date()
            recours_obj.observation = decision.observation
            recours_obj.save()

            messages.success(
                request,
                "La décision du recours a été enregistrée."
            )

            return redirect("recours")

    else:
        form = DecisionRecoursForm(
            initial={
                "date_decision": timezone.now().date()
            }
        )

    return render(
        request,
        "core/recours_traiter.html",
        {
            "recours": recours_obj,
            "form": form,
            "permissions": permissions,
            "page": "recours",
        }
    )

