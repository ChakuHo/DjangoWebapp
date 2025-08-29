from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Order, OrderItem, Payment

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order_status_display', 'status', 'payment_method', 
                   'payment_status', 'qr_verification_status', 'grand_total', 'created_at', 'tracking_number')
    list_filter = ('status', 'order_status', 'payment_method', 'payment_status', 'created_at', 'shipped_date')
    search_fields = ('user__username', 'user__email', 'transaction_id', 'tracking_number', 
                    'order_number', 'qr_payment_transaction_id')
    readonly_fields = ('created_at', 'transaction_id', 'order_number', 'qr_payment_confirmed_at', 
                      'qr_payment_verified_by', 'qr_payment_verified_at')
    

    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'created_at', 'order_number')
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'country', 'zip')
        }),
        ('Order Details', {
            'fields': ('payment_method', 'total', 'tax', 'grand_total', 'transaction_id')
        }),
        ('Payment Status', {
            'fields': ('payment_status',),
            'classes': ('wide',),
        }),
        ('QR Payment Details', {
            'fields': ('qr_payment_transaction_id', 'qr_payment_confirmed_at', 
                      'qr_payment_verified_by', 'qr_payment_verified_at'),
            'classes': ('collapse',),
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

    # Combined actions - existing + QR verification
    actions = ['mark_as_confirmed', 'mark_as_processing', 'mark_as_shipped', 
              'mark_as_delivered', 'mark_as_completed', 'mark_as_cancelled',
              'verify_qr_payment', 'reject_qr_payment']
    
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
            'refunded': 'gray',
            'payment under verification': 'orange',
            'payment rejected': 'red'
        }
        color = color_map.get(status.lower(), 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status.title()
        )
    order_status_display.short_description = 'Current Status'
    
    def qr_verification_status(self, obj):
        """Show QR verification status"""
        if obj.payment_method == 'QR Payment':
            if obj.payment_status == 'pending_verification':
                return format_html('<span style="color: orange; font-weight: bold;">🔍 Pending</span>')
            elif obj.payment_status == 'completed':
                return format_html('<span style="color: green; font-weight: bold;">✅ Verified</span>')
            elif obj.payment_status == 'rejected':
                return format_html('<span style="color: red; font-weight: bold;">❌ Rejected</span>')
            else:
                return format_html('<span style="color: blue;">📱 QR Payment</span>')
        return "-"
    qr_verification_status.short_description = "QR Status"
    
    # Existing order status actions
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
    
    # NEW QR Payment verification actions
    def verify_qr_payment(self, request, queryset):
        """Verify QR payments"""
        from .views import send_order_confirmation_email
        
        count = 0
        for order in queryset.filter(payment_method='QR Payment', payment_status='pending_verification'):
            order.payment_status = 'completed'
            order.status = 'Confirmed'
            order.order_status = 'confirmed'
            order.qr_payment_verified_by = request.user
            order.qr_payment_verified_at = timezone.now()
            order.save()
            
            # Send confirmation email
            try:
                send_order_confirmation_email(order)
            except Exception as e:
                print(f"Error sending email for order {order.id}: {e}")
            
            count += 1
        
        self.message_user(request, f'Successfully verified {count} QR payments and sent confirmation emails')
    verify_qr_payment.short_description = "✅ Verify selected QR payments"
    
    def reject_qr_payment(self, request, queryset):
        """Reject QR payments"""
        count = 0
        for order in queryset.filter(payment_method='QR Payment', payment_status='pending_verification'):
            order.payment_status = 'rejected'
            order.status = 'Payment Rejected'
            order.order_status = 'cancelled'
            order.save()
            count += 1
        
        self.message_user(request, f'Rejected {count} QR payments. Customers will need to be notified manually.')
    reject_qr_payment.short_description = "❌ Reject selected QR payments"


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

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'user', 'payment_method', 'amount_paid', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('payment_id', 'user__username', 'user__email')
    readonly_fields = ('created_at',)