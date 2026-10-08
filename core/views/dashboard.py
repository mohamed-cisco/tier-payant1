# core/views/dashboard.py
"""
Vues du tableau de bord et fonctions utilitaires.

Fonctions :
- enregistrer_audit : enregistre une action dans le journal
- aide : page d'aide
- accueil : tableau de bord
"""

from datetime import timedelta

from django.contrib import messages
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import (
    Adherent,
    AuditLog,
    Contrat,
    Convention,
    DemandeTp,
    DemandeTpDetail,
    Facture,
    Reglement,
    RolePermission,
    UtilisateurRole,
)


def enregistrer_audit(
    request,
    type_action,
    module,
    table_cible=None,
    id_enregistrement=None,
    ancienne_valeur=None,
    nouvelle_valeur=None,
    description=None,
):
    """Enregistre une action dans le journal d'audit."""
    id_utilisateur = request.session.get("id_utilisateur")

    AuditLog.objects.create(
        id_utilisateur_id=id_utilisateur,
        date_action=timezone.now(),
        type_action=type_action,
        module=module,
        table_cible=table_cible,
        id_enregistrement=id_enregistrement,
        ancienne_valeur=ancienne_valeur,
        nouvelle_valeur=nouvelle_valeur,
        adresse_ip=request.META.get("REMOTE_ADDR"),
        poste=request.META.get("COMPUTERNAME"),
        description=description,
    )


def aide(request):
    """Page d'aide utilisateur."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    return render(request, "core/aide.html", {
        "page": "aide",
    })


def accueil(request):
    """Tableau de bord principal."""
    from django.core.cache import cache

    # Récupérer l'utilisateur (via session)
    id_utilisateur = request.session.get("id_utilisateur")

    if not id_utilisateur:
        return redirect("connexion")

    # Récupérer l'utilisateur
    from core.models import Utilisateur
    utilisateur = Utilisateur.objects.get(id_utilisateur=id_utilisateur)

    # Cache des stats pendant 5 minutes
    cache_key_stats = "dashboard_stats"

    stats = cache.get(cache_key_stats)

    if stats is None:
        stats = {
            "nombre_adherents": Adherent.objects.count(),
            "contrats_actifs": Contrat.objects.filter(statut="ACTIF").count(),
            "demandes_en_attente": DemandeTp.objects.filter(statut="EN_ATTENTE").count(),
            "factures_en_attente": Facture.objects.filter(statut="EN_ATTENTE").count(),
            "adherents_actifs": Adherent.objects.filter(statut="ACTIF").count(),
            "demandes_acceptees": DemandeTp.objects.filter(statut="ACCEPTEE").count(),
            "factures_payees": Facture.objects.filter(statut="PAYEE").count(),
            "montant_factures_validees": (
                Facture.objects
                .filter(statut__in=["VALIDEE", "PAYEE"])
                .aggregate(total=Sum("montant_valide"))["total"] or 0
            ),
            "montant_paye": (
                Reglement.objects
                .filter(statut="VALIDEE")
                .aggregate(total=Sum("montant"))["total"] or 0
            ),
        }
        cache.set(cache_key_stats, stats, 300)

    nombre_adherents = stats["nombre_adherents"]
    contrats_actifs = stats["contrats_actifs"]
    demandes_en_attente = stats["demandes_en_attente"]
    factures_en_attente = stats["factures_en_attente"]
    adherents_actifs = stats["adherents_actifs"]
    demandes_acceptees = stats["demandes_acceptees"]
    factures_payees = stats["factures_payees"]
    montant_factures_validees = stats["montant_factures_validees"]
    montant_paye = stats["montant_paye"]

    reste_a_payer = montant_factures_validees - montant_paye

    roles = (
        UtilisateurRole.objects
        .filter(id_utilisateur=id_utilisateur, statut="ACTIF")
        .select_related("id_role")
    )

    permissions = set(
        RolePermission.objects
        .filter(
            id_role__utilisateurrole__id_utilisateur=id_utilisateur,
            id_role__utilisateurrole__statut="ACTIF",
            id_permission__statut="ACTIF"
        )
        .values_list("id_permission__code_permission", flat=True)
    )

    # =========================
    # FILTRE PAR PÉRIODE
    # =========================
    periode = request.GET.get("periode", "annee")
    aujourd_hui = timezone.now().date()

    if periode == "mois":
        date_debut = aujourd_hui.replace(day=1)
    elif periode == "trimestre":
        mois_debut = ((aujourd_hui.month - 1) // 3) * 3 + 1
        date_debut = aujourd_hui.replace(month=mois_debut, day=1)
    elif periode == "annee":
        date_debut = aujourd_hui.replace(month=1, day=1)
    else:
        date_debut = None

    # =========================
    # STATISTIQUES GÉNÉRALES
    # =========================
    nombre_adherents = Adherent.objects.count()
    contrats_actifs = Contrat.objects.filter(statut="ACTIF").count()
    demandes_en_attente = DemandeTp.objects.filter(statut="EN_ATTENTE").count()
    factures_en_attente = Facture.objects.filter(statut="EN_ATTENTE").count()

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
    demandes_acceptees = DemandeTp.objects.filter(statut="ACCEPTEE").count()
    factures_payees = Facture.objects.filter(statut="PAYEE").count()

    # =========================
    # KPIs AVANCÉS
    # =========================
    total_demandes = DemandeTp.objects.count()

    if total_demandes:
        taux_acceptation = round((demandes_acceptees / total_demandes) * 100, 1)
    else:
        taux_acceptation = 0

    montant_moyen_demande = (
        DemandeTp.objects.aggregate(moyenne=Avg("montant_demande"))["moyenne"]
        or 0
    )

    # Délai moyen de traitement
    delai_moyen_jours = 0
    try:
        demandes_traitees = DemandeTp.objects.filter(
            statut="ACCEPTEE",
            date_decision__isnull=False
        ).exclude(date_demande__isnull=True)

        if demandes_traitees.exists():
            delais = [
                (d.date_decision.date() - d.date_demande.date()).days
                for d in demandes_traitees
                if d.date_decision and d.date_demande
            ]
            if delais:
                delai_moyen_jours = round(sum(delais) / len(delais), 1)
    except Exception:
        pass

    # =========================
    # GRAPHIQUE 1 : DEMANDES PAR MOIS
    # =========================
    demandes_qs = DemandeTp.objects.all()
    if date_debut:
        demandes_qs = demandes_qs.filter(date_demande__date__gte=date_debut)

    demandes_par_mois = (
        demandes_qs
        .annotate(mois=TruncMonth("date_demande"))
        .values("mois")
        .annotate(total=Count("id_demande"))
        .order_by("mois")
    )
    graphique_labels = [item["mois"].strftime("%m/%Y") for item in demandes_par_mois]
    graphique_demandes = [item["total"] for item in demandes_par_mois]

    # =========================
    # GRAPHIQUE 2 : RÉPARTITION PAR TYPE DE PRESTATION
    # =========================
    prestations_par_type = (
        DemandeTpDetail.objects
        .values("id_acte__id_type_prestation__libelle")
        .annotate(total=Count("id_detail"))
        .order_by("-total")
    )
    prestation_labels = [
        item["id_acte__id_type_prestation__libelle"] or "Non défini"
        for item in prestations_par_type
    ]
    prestation_totaux = [item["total"] for item in prestations_par_type]

    # =========================
    # GRAPHIQUE 3 : FACTURES PAR STATUT
    # =========================
    factures_par_statut = (
        Facture.objects
        .values("statut")
        .annotate(total=Count("id_facture"))
        .order_by("-total")
    )
    facture_statut_labels = [item["statut"] for item in factures_par_statut]
    facture_statut_totaux = [item["total"] for item in factures_par_statut]

    # =========================
    # GRAPHIQUE 4 : TOP 5 PRESTATAIRES PAR MONTANT VALIDÉ
    # =========================
    top_prestataires = (
        Facture.objects
        .values("id_prestataire__raison_sociale")
        .annotate(total=Sum("montant_valide"))
        .order_by("-total")[:5]
    )
    top_prestataire_labels = [item["id_prestataire__raison_sociale"] for item in top_prestataires]
    top_prestataire_totaux = [float(item["total"] or 0) for item in top_prestataires]

    # =========================
    # ALERTES
    # =========================
    date_limite_30j = aujourd_hui + timedelta(days=30)

    conventions_bientot_expirees = (
        Convention.objects
        .filter(
            statut="ACTIF",
            date_fin__isnull=False,
            date_fin__lte=date_limite_30j,
            date_fin__gte=aujourd_hui
        )
        .select_related("id_prestataire")
        .order_by("date_fin")
    )

    date_retard = aujourd_hui - timedelta(days=30)

    factures_en_retard = (
        Facture.objects
        .filter(statut="EN_ATTENTE", date_facture__lte=date_retard)
        .select_related("id_prestataire")
        .order_by("date_facture")
    )

    # =========================
    # ACTIVITÉ RÉCENTE
    # =========================
    dernieres_demandes = DemandeTp.objects.order_by("-date_demande")[:5]
    dernieres_factures = Facture.objects.order_by("-date_facture")[:5]

    return render(
        request,
        "core/accueil.html",
        {
            "utilisateur": utilisateur,
            "roles": roles,
            "permissions": permissions,
            "page": "accueil",
            "periode": periode,

            # Stats générales
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

            # KPIs avancés
            "taux_acceptation": taux_acceptation,
            "montant_moyen_demande": montant_moyen_demande,
            "delai_moyen_jours": delai_moyen_jours,

            # Graphiques
            "graphique_labels": graphique_labels,
            "graphique_demandes": graphique_demandes,
            "prestation_labels": prestation_labels,
            "prestation_totaux": prestation_totaux,
            "facture_statut_labels": facture_statut_labels,
            "facture_statut_totaux": facture_statut_totaux,
            "top_prestataire_labels": top_prestataire_labels,
            "top_prestataire_totaux": top_prestataire_totaux,

            # Alertes
            "conventions_bientot_expirees": conventions_bientot_expirees,
            "factures_en_retard": factures_en_retard,

            # Activité récente
            "dernieres_demandes": dernieres_demandes,
            "dernieres_factures": dernieres_factures,
        }
    )


def a_propos(request):
    """Page À propos avec l'historique des versions."""
    if not request.session.get("id_utilisateur"):
        return redirect("connexion")

    from core.version import (
        VERSION, DATE_VERSION, NOM_VERSION, get_historique
    )

    return render(
        request,
        "core/a_propos.html",
        {
            "VERSION": VERSION,
            "DATE_VERSION": DATE_VERSION,
            "NOM_VERSION": NOM_VERSION,
            "historique": get_historique(),
            "page": "a_propos",
        }
    )