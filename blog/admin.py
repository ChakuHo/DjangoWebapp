from django.contrib import admin
from . models import Blog, Category

# Register your models here.
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)

admin.site.register(Category, CategoryAdmin)

class BlogAdmin(admin.ModelAdmin):
    exclude = ('created_at',) # helps to exclude selecting date and time everytime adding product.
    list_display = ('id', 'name', 'category', 'description', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('name', 'description')

admin.site.register(Blog,BlogAdmin)
