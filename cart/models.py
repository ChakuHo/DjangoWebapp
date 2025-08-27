from django.db import models
from products.models import Product, ProductVariation
from django.contrib.auth.models import User
import json

class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.cart_id

class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # ⭐ NEW: Safe variation fields (optional)
    variations = models.ManyToManyField(ProductVariation, blank=True)
    variation_data = models.TextField(blank=True, help_text="JSON data of selected variations")

    def sub_total(self):
        """Enhanced but backward compatible subtotal calculation"""
        base_price = float(self.product.price)
        
        # Only calculate variation adjustments if variations exist
        if self.variations.exists():
            variation_adjustment = sum(float(v.price_adjustment) for v in self.variations.all())
            final_price = base_price + variation_adjustment
        else:
            final_price = base_price  # Keep original behavior
            
        return final_price * self.quantity
    
    def get_available_stock(self):
        """Get available stock for this specific cart item considering its variations"""
        if not self.variations.exists():
            return self.product.stock
        
        # For items with variations, get the minimum stock among all variations
        min_stock = self.product.stock
        for variation in self.variations.all():
            if variation.stock_quantity < min_stock:
                min_stock = variation.stock_quantity
        return min_stock    

    def get_final_price_per_unit(self):
        """Get price per unit including variations"""
        base_price = float(self.product.price)
        if self.variations.exists():
            variation_adjustment = sum(float(v.price_adjustment) for v in self.variations.all())
            return base_price + variation_adjustment
        return base_price

    def get_variations_display(self):
        """Get readable variation text"""
        if not self.variations.exists():
            return []
        
        variations_list = []
        for variation in self.variations.all():
            variations_list.append(f"{variation.variation_type.display_name}: {variation.variation_option.get_display_value()}")
        return variations_list

    def has_variations(self):
        """Check if this cart item has variations"""
        return self.variations.exists()

    def __str__(self):
        if self.has_variations():
            variations = ', '.join(self.get_variations_display())
            return f"{self.product.name} ({variations})"
        return self.product.name