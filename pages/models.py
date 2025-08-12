from django.db import models
from django.utils import timezone
from django.utils.text import slugify

# Create your models here.
class Page(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug or Page.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Page.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Page"
        verbose_name_plural = "Pages"
        ordering = ['-created_at']