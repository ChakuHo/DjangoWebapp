from django.db import models
from django.contrib.auth.models import User
from products.models import Product

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
    
    # NEW ENHANCED STATUS SYSTEM (additive)
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
    
    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"
    

    def is_completed(self):
        return self.order_status == 'completed'
    
    def get_effective_status(self):
        if self.order_status and self.order_status != 'pending':
            return self.order_status
        return self.status.lower()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.FloatField()
    
    # SELLER TRACKING 
    seller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sold_items')
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"