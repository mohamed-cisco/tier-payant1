"""Vue de la page d'accueil (tableau de bord)."""

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render

from core.auth_utils import session_utilisateur_required
from core.models import (
    Adherent,
    Contrat,
    DemandeTp,
    DemandeTpDetail,
    Facture,
    Reglement,
    RolePermission,
    UtilisateurRole,
)


@session_utilisateur_required
def accueil(request):
    utilisateur = request.utilisateur
    id_utilisateur = utilisateur.id_utilisateur

    roles = (
        UtilisateurRole.objects
        .filter(
            id_utilisateur=id_utilisateur,
            statut="ACTIF"
        )
        .select_related("id_role")
    )

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

    # =========================
    # STATISTIQUES DU TABLEAU DE BORD
    # =========================

    nombre_adherents = Adherent.objects.count()

    contrats_actifs = Contrat.objects.filter(statut="ACTIF").count()

    demandes_en_attente = DemandeTp.objects.filter(
        statut="EN_ATTENTE"
    ).count()

    factures_en_attente = Facture.objects.filter(
        statut="EN_ATTENTE"
    ).count()

    montant_factures_validees = (
        Facture.objects
        .filter(statut__in=["VALIDEE", "PAYEE"])
        .aggregate(total=Sum("montant_valide"))["total"]
        or 0
    )

    montant_paye = (
        Reglement.objects
        .filter(statut="VALIDEE")
        .aggregate(total=Sum("montant"))["total"]
        or 0
    )

    reste_a_payer = montant_factures_validees - montant_paye

    adherents_actifs = Adherent.objects.filter(statut="ACTIF").count()

    demandes_acceptees = DemandeTp.objects.filter(
        statut="ACCEPTEE"
    ).count()

    factures_payees = Facture.objects.filter(statut="PAYEE").count()

    dernieres_demandes = DemandeTp.objects.order_by("-date_demande")[:5]

    dernieres_factures = Facture.objects.order_by("-date_facture")[:5]

    # =========================
    # DONNÉES GRAPHIQUE DEMANDES TP
    # =========================

    demandes_par_mois = (
        DemandeTp.objects
        .annotate(mois=TruncMonth("date_demande"))
        .values("mois")
        .annotate(total=Count("id_demande"))
        .order_by("mois")
    )

    graphique_labels = [
        item["mois"].strftime("%m/%Y")
        for item in demandes_par_mois
    ]

    graphique_demandes = [
        item["total"]
        for item in demandes_par_mois
    ]

    # =========================
    # RÉPARTITION PAR TYPE DE PRESTATION
    # =========================

    prestations_par_type = (
        DemandeTpDetail.objects
        .values("id_acte__id_type_prestation__libelle")
        .annotate(total=Count("id_detail"))
        .order_by("-total")
    )

    prestation_labels = [
        item["id_acte__id_type_prestation__libelle"]
        for item in prestations_par_type
    ]

    prestation_totaux = [
        item["total"]
        for item in prestations_par_type
    ]

    return render(
        request,
        "core/accueil.html",
        {
            "utilisateur": utilisateur,
            "roles": roles,
            "permissions": permissions,
            "nombre_adherents": nombre_adherents,
            "contrats_actifs": contrats_actifs,
            "demandes_en_attente": demandes_en_attente,
            "factures_en_attente": factures_en_attente,
            "montant_factures_validees": montant_factures_validees,
            "montant_paye": montant_paye,
            "reste_a_payer": reste_a_payer,
            "adherents_actifs": adherents_actifs,
            "demandes_acceptees": demandes_acceptees,
            "factures_payees": factures_payees,
            "dernieres_demandes": dernieres_demandes,
            "dernieres_factures": dernieres_factures,
            "graphique_labels": graphique_labels,
            "graphique_demandes": graphique_demandes,
            "prestation_labels": prestation_labels,
            "prestation_totaux": prestation_totaux,
        }
    )
