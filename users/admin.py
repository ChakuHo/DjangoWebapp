from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'city', 'country')
    list_filter = ('city', 'country')
    search_fields = ('user__username', 'user__email', 'phone_number')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return ('user',)
        return ()