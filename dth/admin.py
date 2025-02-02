from django.contrib import admin
from dth.models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cargo', 'firma')
    search_fields = ('user__username', 'cargo')

admin.site.register(UserProfile, UserProfileAdmin)
