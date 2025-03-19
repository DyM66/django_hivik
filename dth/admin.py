from django.contrib import admin
from dth.models import UserProfile, Department, Nomina

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cargo', 'firma')
    search_fields = ('user__username', 'cargo')

class NominaAdmin(admin.ModelAdmin):
    list_display = ('doc_number', 'name', 'surname', 'position', 'salary', 'category')
    search_fields = ('doc_number', 'name', 'surname', 'position', 'category')

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Nomina, NominaAdmin)
# admin.site.register(Department)