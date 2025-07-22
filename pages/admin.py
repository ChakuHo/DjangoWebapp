from django.contrib import admin
from . models import Page

# Register your models here.
class PageAdmin(admin.ModelAdmin):
    exclude = ('created_at',) # helps to exclude selecting date and time everytime adding product.
    list_display = ('title', 'slug', 'content', 'created_at')

admin.site.register(Page, PageAdmin)