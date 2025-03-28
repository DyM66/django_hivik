from django.contrib import admin
from django.contrib.auth.models import Permission
from .models import *

class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'content_type', 'content_type_app_label', 'content_type_model')
    list_filter = ('content_type__app_label', )
    search_fields = ('name', 'codename')

    def content_type_app_label(self, obj):
        return obj.content_type.app_label if obj.content_type else 'None'
    content_type_app_label.short_description = 'App'

    def content_type_model(self, obj):
        return obj.content_type.model if obj.content_type else 'None'
    content_type_model.short_description = 'Modelo'

# Definición de la clase SuministroAdmin
class SuministroAdmin(admin.ModelAdmin):
    list_display = ('item', 'cantidad', 'display_asset', 'equipo')
    list_filter = ('asset',)  # Filtro para Asset
    search_fields = ('item__name', 'item__reference')

    def display_asset(self, obj):
        return obj.asset if obj.asset else "---"
    display_asset.short_description = 'Asset'  # Etiqueta para la columna en el admin

class OtAdmin(admin.ModelAdmin):
    list_display = ('num_ot', 'creation_date', 'description', 'system', 'supervisor')

admin.site.register(Permission, PermissionAdmin)
admin.site.register(Asset)
admin.site.register(MaintenanceRequirement)
admin.site.register(FailureReport)
admin.site.register(Ruta)
admin.site.register(Equipo)
admin.site.register(System)
admin.site.register(HistoryHour)
admin.site.register(Item)
admin.site.register(Document)
admin.site.register(Ot, OtAdmin)
admin.site.register(Task)
admin.site.register(Suministro, SuministroAdmin)