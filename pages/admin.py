from django.contrib import admin
from . models import Page 
# Register your models here.

class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'content')
    ordering = ('-created_at',)

admin.site.register(Page, PageAdmin)