def audit_logs(request):
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

    if "AUDIT_VIEW" not in permissions:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de consulter les journaux d'audit."
        )
        return redirect("accueil")

    recherche = request.GET.get("recherche", "").strip()
    module = request.GET.get("module", "").strip()
    type_action = request.GET.get("type_action", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    audits = (
        AuditLog.objects
        .select_related("id_utilisateur")
        .all()
        .order_by("-date_action", "-id_audit")
    )

    if recherche:
        from django.db.models import Q

        audits = audits.filter(
            Q(module__icontains=recherche)
            | Q(table_cible__icontains=recherche)
            | Q(description__icontains=recherche)
            | Q(type_action__icontains=recherche)
            | Q(adresse_ip__icontains=recherche)
            | Q(poste__icontains=recherche)
        )

    if module:
        audits = audits.filter(module=module)

    if type_action:
        audits = audits.filter(type_action=type_action)

    if date_debut:
        audits = audits.filter(date_action__date__gte=date_debut)

    if date_fin:
        audits = audits.filter(date_action__date__lte=date_fin)

    modules = (
        AuditLog.objects
        .exclude(module__isnull=True)
        .exclude(module="")
        .values_list("module", flat=True)
        .distinct()
        .order_by("module")
    )

    types_action = (
        AuditLog.objects
        .exclude(type_action__isnull=True)
        .exclude(type_action="")
        .values_list("type_action", flat=True)
        .distinct()
        .order_by("type_action")
    )

    return render(
        request,
        "core/audit.html",
        {
            "audits": audits,
            "permissions": permissions,
            "recherche": recherche,
            "module": module,
            "type_action": type_action,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "modules": modules,
            "types_action": types_action,
            "page": "audit",
        }
    )
