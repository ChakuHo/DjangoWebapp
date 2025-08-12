from django.contrib import admin
from . models import SiteSetting
# Register your models here.

class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('site_title', 'meta_description', 'logo', 'favicon')    
    def __str__(self):
        return self.site_name

admin.site.register(SiteSetting, SiteSettingAdmin)