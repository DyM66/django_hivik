from django.contrib import admin
from .models import *

from django.utils import timezone


# Definición de la clase SuministroAdmin
class SuministroAdmin(admin.ModelAdmin):
    list_display = ('item', 'cantidad', 'display_asset', 'equipo')
    list_filter = ('asset',)  # Filtro para Asset
    search_fields = ('item__name', 'item__reference')

    def display_asset(self, obj):
        return obj.asset if obj.asset else "---"
    display_asset.short_description = 'Asset'  # Etiqueta para la columna en el admin

# Registro del modelo Suministro con su clase admin personalizada
admin.site.register(Suministro, SuministroAdmin)


class OtAdmin(admin.ModelAdmin):
    list_display = (
        'num_ot',
        'creation_date',
        'description',
        'system',
        'supervisor'
        )

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cargo', 'firma')
    search_fields = ('user__username', 'cargo')

admin.site.register(UserProfile, UserProfileAdmin)

admin.site.register(Asset)
admin.site.register(MaintenanceRequirement)
admin.site.register(Operation)
admin.site.register(FailureReport)
admin.site.register(Ruta)
admin.site.register(Equipo)
admin.site.register(System)
admin.site.register(HistoryHour)
admin.site.register(Item)
admin.site.register(Document)
admin.site.register(Ot, OtAdmin)
admin.site.register(Task)



class SolicitudAdmin(admin.ModelAdmin):
    list_display = ('solicitante', 'ot', 'asset', 'creation_date', 'approved', 'num_sc', 'display_approval_date')
    list_filter = ('approved', 'creation_date', 'solicitante', 'asset')
    search_fields = ('solicitante__username', 'ot__description', 'asset__name', 'num_sc')
    date_hierarchy = 'creation_date'
    readonly_fields = ('creation_date',)

    fieldsets = (
        (None, {
            'fields': ('solicitante', 'ot', 'asset', 'suministros', 'num_sc', 'approved')
        }),
        ('Dates', {
            'fields': ('creation_date', 'approval_date', 'sc_change_date', 'cancel_date')
        }),
        ('Cancellation Details', {
            'fields': ('cancel', 'cancel_reason'),
        }),
    )

    def display_approval_date(self, obj):
        return obj.approval_date.strftime('%Y-%m-%d') if obj.approval_date else '---'
    display_approval_date.short_description = 'Approval Date'

    actions = ['mark_as_approved', 'mark_as_cancelled']

    def mark_as_approved(self, request, queryset):
        queryset.update(approved=True, approval_date=timezone.now())
    mark_as_approved.short_description = 'Mark selected as approved'

    def mark_as_cancelled(self, request, queryset):
        queryset.update(cancel=True, cancel_date=timezone.now())
    mark_as_cancelled.short_description = 'Mark selected as cancelled'

# Registro del modelo Solicitud con la clase SolicitudAdmin
admin.site.register(Solicitud, SolicitudAdmin)