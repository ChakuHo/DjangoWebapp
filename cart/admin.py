from django.contrib import admin
from .models import Cart, CartItem
# Register your models here.

class CartAdmin(admin.ModelAdmin):
    exclude = ('created_at',)
    list_display = ('user',)
admin.site.register(Cart, CartAdmin)

class ItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'added_at')
admin.site.register(CartItem, ItemAdmin)