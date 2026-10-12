# remboursement/urls.py
"""URLs du module Remboursement Classique."""
from django.urls import path

from remboursement.views import (
    bulletins, validation, recaps, virements,
    config_cnas, dashboard, ribs, rapports
)


urlpatterns = [
    # Bulletins
    path('bulletins/', bulletins.bulletins, name='remb_bulletins'),
    path('bulletins/nouveau/', bulletins.bulletin_create, name='remb_bulletin_create'),
    path('bulletins/<int:id_bulletin>/', bulletins.bulletin_detail, name='remb_bulletin_detail'),
    path('bulletins/<int:id_bulletin>/ligne/ajouter/', bulletins.ligne_create, name='remb_ligne_create'),
    path('lignes/<int:id_ligne>/supprimer/', bulletins.ligne_delete, name='remb_ligne_delete'),
    
    # Workflow bulletin
    path('bulletins/<int:id_bulletin>/valider/', validation.valider, name='remb_bulletin_valider'),
    path('bulletins/<int:id_bulletin>/recalculer/', validation.recalculer, name='remb_bulletin_recalculer'),
    path('bulletins/<int:id_bulletin>/controler/', validation.controler, name='remb_bulletin_controler'),
    path('bulletins/<int:id_bulletin>/rejeter/', validation.rejeter, name='remb_bulletin_rejeter'),
    path('bulletins/<int:id_bulletin>/reactiver/', validation.reactiver, name='remb_bulletin_reactiver'),
    
    # Récaps
    path('recaps/', recaps.recaps, name='remb_recaps'),
    path('recaps/nouveau/', recaps.recap_create, name='remb_recap_create'),
    path('recaps/rattrapage/', recaps.recap_rattrapage, name='remb_recap_rattrapage'),
    path('recaps/<int:id_recap>/', recaps.recap_detail, name='remb_recap_detail'),
    path('recaps/<int:id_recap>/envoyer/', recaps.recap_envoyer, name='remb_recap_envoyer'),
    path('recaps/<int:id_recap>/valider/', recaps.recap_valider, name='remb_recap_valider'),
    path('recaps/<int:id_recap>/payer/', recaps.recap_payer, name='remb_recap_payer'),
    path('recaps/<int:id_recap>/rejeter/', recaps.recap_rejeter, name='remb_recap_rejeter'),
    path('recaps/<int:id_recap>/recalculer/', recaps.recap_recalculer, name='remb_recap_recalculer'),
    path('recaps/<int:id_recap>/pdf/', recaps.recap_pdf, name='remb_recap_pdf'),
    path('recaps/<int:id_recap>/excel/', recaps.recap_excel, name='remb_recap_excel'),
    # Virements
    path('virements/', virements.virements, name='remb_virements'),
    path('virements/a-payer/', virements.virements_a_payer, name='remb_virements_a_payer'),
    path('virements/<int:id_virement>/', virements.virement_detail, name='remb_virement_detail'),
    path('virements/<int:id_virement>/payer/', virements.virement_payer, name='remb_virement_payer'),
    path('virements/<int:id_virement>/echec/', virements.virement_echec, name='remb_virement_echec'),
    path('virements/<int:id_virement>/corriger-rib/', virements.virement_corriger_rib, name='remb_virement_corriger_rib'),
    path('virements/<int:id_virement>/annuler/', virements.virement_annuler, name='remb_virement_annuler'),
    # Configuration CNAS
    path('config-cnas/', config_cnas.config_cnas, name='remb_config_cnas'),
        path('config-cnas/<int:id_config>/supprimer/', config_cnas.config_cnas_supprimer, name='remb_config_cnas_supprimer'),
    # Tableau de bord (dédié au remboursement)
    path('dashboard/', dashboard.dashboard, name='remb_dashboard'),
    # Coordonnées bancaires (RIB)
    path('ribs/', ribs.ribs_manquants, name='remb_ribs_manquants'),
    path('ribs/ajouter/<int:id_adherent>/', ribs.rib_ajouter, name='remb_rib_ajouter'),
    path('ribs/<int:id_rib>/modifier/', ribs.rib_modifier, name='remb_rib_modifier'),
    path('ribs/<int:id_rib>/supprimer/', ribs.rib_supprimer, name='remb_rib_supprimer'),

    # ============================================================
    # RAPPORTS DE SUIVI
    # ============================================================
    path('rapports/par-mois/', rapports.remb_par_mois, name='rapport_remb_par_mois'),
    path('rapports/par-mois/pdf/', rapports.remb_par_mois_pdf, name='rapport_remb_par_mois_pdf'),
    
    path('rapports/par-souscripteur/', rapports.remb_par_souscripteur, name='rapport_remb_par_souscripteur'),
    path('rapports/par-souscripteur/pdf/', rapports.remb_par_souscripteur_pdf, name='rapport_remb_par_souscripteur_pdf'),
    
    path('rapports/en-attente/', rapports.remb_en_attente, name='rapport_remb_en_attente'),
    path('rapports/en-attente/pdf/', rapports.remb_en_attente_pdf, name='rapport_remb_en_attente_pdf'),
    
    path('rapports/echecs/', rapports.remb_echecs, name='rapport_remb_echecs'),
    path('rapports/echecs/pdf/', rapports.remb_echecs_pdf, name='rapport_remb_echecs_pdf'),
    
    path('rapports/ecarts/', rapports.remb_ecarts, name='rapport_remb_ecarts'),
    path('rapports/ecarts/pdf/', rapports.remb_ecarts_pdf, name='rapport_remb_ecarts_pdf'),
]
