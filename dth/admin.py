from django.contrib import admin
from dth.models import UserProfile, Department, Nomina

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cargo', 'firma')
    search_fields = ('user__username', 'cargo')

class NominaAdmin(admin.ModelAdmin):
    list_display = ('id_number', 'name', 'surname', 'position', 'salary')
    search_fields = ('id_number', 'name', 'surname', 'position')

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Nomina, NominaAdmin)
# admin.site.register(Department)