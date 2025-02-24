from django.contrib import admin
from django.utils import timezone
from inv.models import Solicitud

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