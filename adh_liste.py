def adhesions(request):
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
            "Vous n'avez pas l'autorisation de consulter les adhésions."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    adhesions = (
        Adhesion.objects
        .select_related(
            "id_adherent",
            "id_adherent__id_personne",
            "id_contrat",
            "id_contrat__id_souscripteur",
        )
        .all()
        .order_by("-id_adhesion")
    )
    
    
    if recherche:
        from django.db.models import Q

        adhesions = adhesions.filter(
            Q(numero_adhesion__icontains=recherche)
            | Q(
                id_adherent__numero_adherent__icontains=recherche
            )
            | Q(
                id_contrat__numero_contrat__icontains=recherche
            )
            | Q(
                id_contrat__id_souscripteur__raison_sociale__icontains=recherche
            )
        )

    if statut:
        adhesions = adhesions.filter(
            statut=statut
        )

    return render(
        request,
        "core/adhesions.html",
        {
            "adhesions": adhesions,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "adhesions",
        }
    )
