from django.db import models
from django.utils import timezone
from products.models import Category
from django.urls import reverse

class Banner(models.Model):
    title = models.CharField(max_length=150, blank=True, default="")
    subtitle = models.CharField(max_length=255, blank=True, default="")
    image = models.ImageField(upload_to='banners/')
    alt_text = models.CharField(max_length=150, blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    link_url = models.URLField(blank=True, default="")
    open_in_new_tab = models.BooleanField(default=False)
    
    # scheduling window
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:  # This needs to be indented inside Banner class
        ordering = ['order', '-created_at']
    
    def __str__(self):  # This needs to be indented inside Banner class
        return self.title or f"Banner #{self.pk}"
    
    def is_live(self):  # This needs to be indented inside Banner class
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True
    
    def target_href(self):
    # If there's a custom link_url, use it
        if self.link_url:
            return self.link_url
    
    # If there's a category, link to products filtered by that category
        if self.category:
        # Check what URL name you have in products/urls.py for category filtering
        # Replace 'products_by_category' with your actual URL name
            try:
                return f"/products/category/{self.category.slug}/"  # Direct URL path
            except:
                return "/products/"  # Fallback to products page
    
    # Default to homepage
        return "/"