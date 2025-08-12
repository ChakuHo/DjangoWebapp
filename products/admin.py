from django.contrib import admin
from . models import Product, ProductCategory
from django.utils.html import format_html

# Register your models here.

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id','name')
admin.site.register(ProductCategory, CategoryAdmin)

class ProductAdmin(admin.ModelAdmin):
    exclude = ('created_at',)
    readonly_fields = ('slug',)
    list_display = ('id', 'name', 'price', 'short_description', 'stock', 'status', 'category', 'created_at', 'show_image')
    list_filter = ('status', 'category')
    
    def short_description(self, obj):
        return ' '.join(obj.description.split()[:6]) + '...'


    def show_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit: cover; border-radius:50%;" />', obj.image.url)
        return "No Image"
    show_image.short_description = 'Image'

admin.site.register(Product, ProductAdmin)