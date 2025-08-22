from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Order, OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order_status_display', 'status', 'payment_method', 
                   'grand_total', 'created_at', 'tracking_number')
    list_filter = ('status', 'order_status', 'payment_method', 'created_at', 'shipped_date')
    search_fields = ('user__username', 'user__email', 'transaction_id', 'tracking_number')
    readonly_fields = ('created_at', 'transaction_id')
    

    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'created_at')
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'country', 'zip')
        }),
        ('Order Details', {
            'fields': ('payment_method', 'total', 'tax', 'grand_total', 'transaction_id')
        }),
        ('Order Status', {
            'fields': ('status', 'order_status'),
            'classes': ('wide',),
        }),
        ('Tracking Information', {
            'fields': ('tracking_number', 'shipped_date', 'delivered_date', 'completed_date'),
            'classes': ('wide',),
        }),
    )

    actions = ['mark_as_confirmed', 'mark_as_processing', 'mark_as_shipped', 
              'mark_as_delivered', 'mark_as_completed', 'mark_as_cancelled']
    
    def order_status_display(self, obj):
        status = obj.order_status or obj.status
        color_map = {
            'pending': 'orange',
            'confirmed': 'blue', 
            'processing': 'purple',
            'shipped': 'lightblue',
            'delivered': 'green',
            'completed': 'darkgreen',
            'cancelled': 'red',
            'refunded': 'gray'
        }
        color = color_map.get(status.lower(), 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status.title()
        )
    order_status_display.short_description = 'Current Status'
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(order_status='confirmed')
        self.message_user(request, f'{updated} orders marked as confirmed.')
    mark_as_confirmed.short_description = "Mark as Confirmed"
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(order_status='processing')
        self.message_user(request, f'{updated} orders marked as processing.')
    mark_as_processing.short_description = "Mark as Processing"
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(order_status='shipped', shipped_date=timezone.now())
        self.message_user(request, f'{updated} orders marked as shipped.')
    mark_as_shipped.short_description = "Mark as Shipped"
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(order_status='delivered', delivered_date=timezone.now())
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark as Delivered"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(order_status='completed', completed_date=timezone.now())
        self.message_user(request, f'{updated} orders marked as completed.')
    mark_as_completed.short_description = "Mark as Completed (Users can now review)"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(order_status='cancelled')
        self.message_user(request, f'{updated} orders cancelled.')
    mark_as_cancelled.short_description = "Cancel Orders"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'seller')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing order
            return ('product', 'quantity', 'price', 'seller')
        return ()


OrderAdmin.inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'seller', 'quantity', 'price', 'order_status')
    list_filter = ('order__status', 'order__order_status', 'seller', 'order__created_at')
    search_fields = ('product__name', 'order__user__username', 'seller__username')
    readonly_fields = ('order', 'product', 'quantity', 'price')
    
    def order_status(self, obj):
        return obj.order.order_status or obj.order.status
    order_status.short_description = 'Order Status'