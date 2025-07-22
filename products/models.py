from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField()
    description = models.TextField()
    stock = models.IntegerField(default=1)
    status = models.BooleanField(default=0)  #yo boolean vayeko vara 0 vaneko false ani 1 vaneko true ho.
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', null=True, blank=True)# upload_to='products/' means images go inside MEDIA_ROOT/products/
    created_at = models.DateTimeField(default=timezone.now) # yo garyo vane laptop ko default timezone linxa.

    def __str__(self):
        return self.name