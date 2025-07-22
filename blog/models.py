from django.db import models
from django.utils import timezone


# Create your models here.
class Category(models.Model):
    name= models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
class Blog(models.Model):
    name=models.CharField(max_length=100)
    description=models.TextField()
    status=models.BooleanField(default=0) # check box for status updating(kei saman xa ki xaina dekahune)
    category= models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at=models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name