from django.contrib import admin
from .models import (
    Asset, System, Ot, Task, Equipo, Ruta, HistoryHour, FailureReport, Location, Operation, Solicitud, Item,
    Megger, Suministro, UserProfile
)


class OtAdmin(admin.ModelAdmin):
    list_display = (
        'num_ot',
        'creation_date',
        'description',
        'system',
        'super'
        )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'ot',
        'responsible',
        'description',
        'start_date',
        'is_overdue'
    )

    list_filter = (
        'start_date', 'finished'
    )

    search_fields = (
        'ot_description', 'description', 'responsible_username'
    )

    date_hierarchy = 'start_date'

    fieldsets = (
        (None, {
            'fields': (
                'ot',
                'responsible',
                'description',
                'news',
                'evidence',
                'start_date'
            )
        }),
        ('Timing', {
            'fields': ('men_time', 'finished')
        }),
    )

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cargo', 'firma')
    search_fields = ('user__username', 'cargo')

admin.site.register(UserProfile, UserProfileAdmin)

admin.site.register(Asset)
admin.site.register(Suministro)
admin.site.register(Megger)
admin.site.register(Operation)
admin.site.register(FailureReport)
admin.site.register(Ruta)
admin.site.register(Equipo)
admin.site.register(System)
admin.site.register(HistoryHour)
admin.site.register(Solicitud)
admin.site.register(Item)
admin.site.register(Location)
admin.site.register(Ot, OtAdmin)
