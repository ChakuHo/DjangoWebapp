from django.db import models

# Create your models here.
class SiteSetting(models.Model):
    site_title = models.CharField(max_length=100, verbose_name="Site Name")
    meta_description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='site_logos/', blank=True, null=True)
    favicon = models.ImageField(upload_to='site_favicons/', blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True, verbose_name="Contact Email")
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Contact Phone")
    address = models.TextField(blank=True, null=True, verbose_name="Address")
    copyright_text = models.CharField(max_length=255, default="© 2025 MySite. All rights reserved.")
    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    site_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return "Site Setting"

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

