from django.db import models
from django.contrib.auth.models import User
from products.models import Product, ProductVariation

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=100)
    amount_paid = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.payment_id

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip = models.CharField(max_length=20)
    payment_method = models.CharField(max_length=50, default='eSewa')
    total = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    grand_total = models.FloatField(default=0)
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    order_number = models.CharField(max_length=20, blank=True)
    is_ordered = models.BooleanField(default=False)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)

    order_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'), 
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),  
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded')
    ], default='pending', blank=True)

    # TRACKING FIELDS
    shipped_date = models.DateTimeField(null=True, blank=True)
    delivered_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    shipping_notes = models.TextField(blank=True, null=True, help_text="Seller's shipping notes")
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When order was confirmed by seller")
    processing_at = models.DateTimeField(null=True, blank=True, help_text="When order started processing")

    # ENHANCED PAYMENT PROCESSING FIELDS
    payment_status = models.CharField(max_length=30, choices=[
        ('pending', 'Pending'),
        ('initiated', 'Payment Initiated'),
        ('pending_qr_confirmation', 'Pending QR Confirmation'),
        ('completed', 'Payment Completed'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded')
    ], default='pending')    

    payment_gateway_response = models.TextField(blank=True, null=True, help_text="Raw response from payment gateway")
    payment_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Payment gateway reference ID or QR reference")
    
    # QR PAYMENT SPECIFIC FIELDS
    qr_payment_confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When QR payment was confirmed")
    qr_payment_notes = models.TextField(blank=True, help_text="Additional notes for QR payment")

    qr_payment_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    qr_payment_screenshot = models.ImageField(upload_to='payment_screenshots/', blank=True, null=True)
    qr_payment_verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    qr_payment_verified_at = models.DateTimeField(null=True, blank=True)

    # Delivery fields
    delivered_date = models.DateTimeField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)  # User-specified delivery date
    delivery_notes = models.TextField(blank=True)

    def get_effective_status(self):
        """Return the current effective status of the order"""
        return self.order_status if hasattr(self, 'order_status') and self.order_status else 'pending'
    
    def get_status_display_name(self):
        """Get human readable status name"""
        status_names = {
            'pending': 'Pending',
            'confirmed': 'Confirmed', 
            'processing': 'Processing',
            'shipped': 'Shipped',
            'delivered': 'Delivered',
            'completed': 'Completed',
            'cancelled': 'Cancelled'
        }
        return status_names.get(self.order_status, self.order_status.title() if self.order_status else 'Pending')


    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def is_completed(self):
        return self.order_status == 'completed'

    def get_effective_status(self):
        if self.order_status and self.order_status != 'pending':
            return self.order_status
        return self.status.lower()
    
    def get_payment_display(self):
        """Return user-friendly payment status"""
        if self.payment_method == 'Cash on Delivery':
            if self.payment_status == 'completed':
                return "Cash on Delivery"
            else:
                return "Pay on Delivery"
        elif self.payment_method == 'QR Payment':
            if self.payment_status == 'completed':
                return f"Paid via QR Code (Ref: {self.payment_reference})"
            elif self.payment_status == 'pending_qr_confirmation':
                return f"QR Payment Pending (Ref: {self.payment_reference})"
            else:
                return "QR Payment"
        else:
            if self.payment_status == 'completed':
                return "Payment Completed"
            elif self.payment_status == 'pending':
                return "Payment Pending"
            elif self.payment_status == 'failed':
                return "Payment Failed"
            else:
                return self.payment_status.title()
    
    def get_payment_icon(self):
        """Return appropriate icon for payment method"""
        if self.payment_method == 'Cash on Delivery':
            return "💰"
        elif self.payment_method == 'eSewa':
            return "💳"
        elif self.payment_method == 'QR Payment':
            return "📱"
        else:
            return "💳"
        
    def save(self, *args, **kwargs):
        # Generate order number if not set
        if not self.order_number:
            # Create order number based on timestamp and ID
            if not self.pk:
                super().save(*args, **kwargs)  # Save first to get ID
            self.order_number = f"ORD{self.created_at.strftime('%Y%m%d')}{self.id:04d}"
            super().save(update_fields=['order_number'])
        else:
            super().save(*args, **kwargs)

        
        
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.FloatField()
    
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    ordered = models.BooleanField(default=False)

    # SELLER TRACKING 
    seller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sold_items')
    
    #  Variation support for order items
    variations = models.ManyToManyField(ProductVariation, blank=True)
    variation_data = models.TextField(blank=True, help_text="JSON data of selected variations at time of purchase")



    def __str__(self):
        if self.variations.exists():
            variations = ', '.join([f"{v.variation_type.display_name}: {v.variation_option.get_display_value()}" 
                                  for v in self.variations.all()])
            return f"{self.product.name} ({variations}) x {self.quantity}"
        return f"{self.product.name} x {self.quantity}"

    def has_variations(self):
        return self.variations.exists()
    
    def get_unit_price(self):
        """Calculate unit price from total price and quantity"""
        if self.quantity > 0:
            return self.price / self.quantity
        return 0