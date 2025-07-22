from django.contrib import admin
from . models import Category, Product
from django.utils.html import format_html

# Register your models here.

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

admin.site.register(Category, CategoryAdmin)


class ProductAdmin(admin.ModelAdmin):
    exclude = ('created_at',) # helps to exclude selecting date and time everytime adding product.
    list_display = ('id', 'name', 'category', 'price', 'stock', 'status', 'show_image') # showing everything in admin dashboard in products page.

    def show_image(self, obj): # showing image as the form of thumbnail in admin panel
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit: cover; border-radius:50%;" />', obj.image.url)
        return "No image"

    show_image.short_description = 'Image'

admin.site.register(Product, ProductAdmin)