from django.contrib import admin

# Register your models here.
from core.models import ConfigCNAS


@admin.register(ConfigCNAS)
class ConfigCNASAdmin(admin.ModelAdmin):
    list_display = ('type_prestation', 'forfait', 'taux_pourcentage', 'actif')
    list_filter = ('actif', 'type_prestation')
    search_fields = ('type_prestation__libelle',)
    ordering = ('type_prestation__libelle',)
    
    fieldsets = (
        ('Type de prestation', {
            'fields': ('type_prestation',)
        }),
        ('Calcul', {
            'fields': ('forfait', 'taux_pourcentage'),
            'description': 'Remplissez SOIT le forfait (montant fixe), SOIT le taux (pourcentage).'
        }),
        ('Statut', {
            'fields': ('actif',)
        }),
    )