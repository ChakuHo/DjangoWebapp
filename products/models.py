from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from django.contrib.auth.models import User

# Create your models here.

class Category(models.Model):
    category_name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    category_image = models.ImageField(upload_to="photos/categories/", blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'category'
        verbose_name_plural = 'categories'
    
    def get_url(self):
        return reverse('produtcs:products_by_Category', args=[self.slug])

    def __str__(self):
        return self.category_name
    
    def save(self, *args, **kwargs):
        if not self.slug or Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            base_slug = slugify(self.category_name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        print(f"Saving category: {self.category_name}, slug: {self.slug}")
        super().save(*args, **kwargs)
    
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    description = models.TextField()
    stock = models.IntegerField(default=1)
    status = models.BooleanField(default=0)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    brand = models.CharField(max_length=100, blank=True, default="") 
    spec = models.CharField(max_length=255, blank=True, default="") 
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    admin_approved = models.BooleanField(default=False)
    approval_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending', blank=True)
    rejection_reason = models.TextField(blank=True)
    submitted_for_approval = models.DateTimeField(default=timezone.now ,blank=True)

# NEW FIELDS FOR DISCOUNT FUNCTIONALITY
    original_price = models.FloatField(null=True, blank=True, help_text="Original price before discount")
    discount_percentage = models.IntegerField(default=0, blank=True, help_text="Discount percentage (0-100)")
    is_on_sale = models.BooleanField(default=False, help_text="Is this product on sale?")
    sale_start_date = models.DateTimeField(null=True, blank=True)
    sale_end_date = models.DateTimeField(null=True, blank=True)

     # NEW FIELDS FOR THRIFT FUNCTIONALITY  
    product_type = models.CharField(max_length=20, choices=[
        ('new', 'New Product'),
        ('thrift', 'Thrift/Used Product'),
        ('refurbished', 'Refurbished')
    ], default='new', help_text="Type of product")
    
    condition = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent - Like New'),
        ('good', 'Good - Minor wear'),
        ('fair', 'Fair - Noticeable wear'),
        ('poor', 'Poor - Heavy wear')
    ], blank=True, null=True, help_text="Condition (for thrift/used products)")
    
    years_used = models.IntegerField(null=True, blank=True, help_text="How many years used (for thrift products)")

    def get_url(self):
        if self.category and self.category.slug and self.slug:
            return reverse('products:product_detail', args=[self.category.slug, self.slug])
        return None

    def __str__(self):
        return self.name
      
    def save(self, *args, **kwargs):
        if not self.slug or Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    
    def get_final_price(self):
        """Get the final price after discount"""
        if self.is_on_sale and self.original_price:
            return self.original_price * (1 - self.discount_percentage / 100)
        return self.price
    
    def get_savings(self):
        """Get the amount saved"""
        if self.is_on_sale and self.original_price:
            return self.original_price - self.get_final_price()
        return 0
    
    def is_sale_active(self):
        """Check if sale is currently active"""
        if not self.is_on_sale:
            return False
        
        now = timezone.now()
        if self.sale_start_date and now < self.sale_start_date:
            return False
        if self.sale_end_date and now > self.sale_end_date:
            return False
        return True

    
    def get_available_stock(self):
        """Get available stock considering variations"""
        if self.variations.exists():
            # Get the minimum stock among all variations
            min_stock = self.stock
            for variation in self.variations.all():
                if variation.stock_quantity < min_stock:
                    min_stock = variation.stock_quantity
            return min_stock
        return self.stock    


    def get_available_variations(self):
        """Get variations available for this product based on its category"""
        if not self.category:
            return {}
        
        available_variations = {}
        category_variations = CategoryVariation.objects.filter(
            category=self.category, 
            variation_type__is_active=True
        ).select_related('variation_type')
        
        for cv in category_variations:
            variation_type = cv.variation_type
            # Get options that are actually available for this product
            available_options = VariationOption.objects.filter(
                variation_type=variation_type,
                is_active=True,
                productvariation__product=self,
                productvariation__is_active=True
            ).distinct()
            
            if available_options.exists():
                available_variations[variation_type] = {
                    'type': variation_type,
                    'options': available_options,
                    'is_required': cv.is_required
                }
        
        return available_variations

    def has_variations(self):
        """Check if this product has any variations"""
        return self.variations.filter(is_active=True).exists()

    def get_category_variations(self):
        """Get all possible variations for this product's category (even if not set up for this product)"""
        if not self.category:
            return CategoryVariation.objects.none()
        
        return CategoryVariation.objects.filter(
            category=self.category,
            variation_type__is_active=True
        ).select_related('variation_type').order_by('sort_order')

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(max_length=500, blank=True)
    rating = models.FloatField()
    ip = models.CharField(max_length=20, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    verified_purchase = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return self.subject
    
    def is_verified_purchase(self):
        return self.verified_purchase and self.order is not None

class VariationType(models.Model):
    """Types of variations like Color, Size, Storage, etc."""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class VariationOption(models.Model):
    """Specific options for each variation type"""
    variation_type = models.ForeignKey(VariationType, on_delete=models.CASCADE, related_name='options')
    value = models.CharField(max_length=100)
    display_value = models.CharField(max_length=100, blank=True)
    color_code = models.CharField(max_length=7, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('variation_type', 'value')
        ordering = ['sort_order', 'value']
    
    def __str__(self):
        return f"{self.variation_type.name}: {self.value}"
    
    def get_display_value(self):
        return self.display_value if self.display_value else self.value

class CategoryVariation(models.Model):
    """Which variation types are available for which categories"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='available_variations')
    variation_type = models.ForeignKey(VariationType, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('category', 'variation_type')
        ordering = ['sort_order']
    
    def __str__(self):
        return f"{self.category.category_name} - {self.variation_type.name}"

class ProductVariation(models.Model):
    """Specific product variations (e.g., Red T-shirt in Size Large)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    variation_type = models.ForeignKey(VariationType, on_delete=models.CASCADE)
    variation_option = models.ForeignKey(VariationOption, on_delete=models.CASCADE)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    #  Multiple images for each variation
    image1 = models.ImageField(upload_to='product_variations/', null=True, blank=True)
    image2 = models.ImageField(upload_to='product_variations/', null=True, blank=True) 
    image3 = models.ImageField(upload_to='product_variations/', null=True, blank=True)
    
    class Meta:
        unique_together = ('product', 'variation_type', 'variation_option')
    
    def __str__(self):
        return f"{self.product.name} - {self.variation_type.name}: {self.variation_option.value}"
    
    def get_price(self):
        """Get the final price with adjustment"""
        return float(self.product.price) + float(self.price_adjustment)
    
    def get_primary_image(self):
        """Get the main image for this variation"""
        return self.image1 if self.image1 else self.product.image
    
    def get_all_images(self):
        """Get all images for this variation"""
        images = []
        if self.image1: images.append(self.image1)
        if self.image2: images.append(self.image2)
        if self.image3: images.append(self.image3)
        return images if images else [self.product.image] if self.product.image else []