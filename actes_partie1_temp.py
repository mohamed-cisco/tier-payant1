def actes(request):
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

    if "ACTE_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les actes."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    statut = request.GET.get("statut", "").strip()

    actes = (
        Acte.objects
        .select_related("id_type_prestation")
        .all()
        .order_by("-id_acte")
    )

    if recherche:
        from django.db.models import Q

        actes = actes.filter(
            Q(code_acte__icontains=recherche)
            | Q(libelle__icontains=recherche)
            | Q(description__icontains=recherche)
        )

    if statut:
        actes = actes.filter(statut=statut)

    return render(
        request,
        "core/actes.html",
        {
            "actes": actes,
            "recherche": recherche,
            "statut": statut,
            "permissions": permissions,
            "page": "actes",       # ← AJOUTE
        }
    )

def acte_detail(request, id_acte):
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

    if "ACTE_VIEW" not in permissions:
        return redirect("accueil")

    acte = get_object_or_404(
        Acte.objects.select_related("id_type_prestation"),
        id_acte=id_acte
    )

    sous_actes = (
        SousActe.objects
        .filter(id_acte=acte)
        .order_by("libelle")
    )

    return render(
        request,
        "core/acte_detail.html",
        {
            "acte": acte,
            "sous_actes": sous_actes,
            "permissions": permissions,
        }
    )

def sous_actes(request):
