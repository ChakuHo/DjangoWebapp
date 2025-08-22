from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    address_line_1 = models.CharField(max_length=100, blank=True)
    address_line_2 = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=20, blank=True)
    state = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=20, blank=True)

    gender = models.CharField(max_length=20, choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say')
    ], blank=True)
    
    date_of_birth = models.DateField(null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself")
    newsletter_subscription = models.BooleanField(default=True)
    preferred_language = models.CharField(max_length=10, choices=[
        ('en', 'English'),
        ('ne', 'Nepali')
    ], default='en', blank=True)
    
  
    is_seller = models.BooleanField(default=False)
    seller_verified = models.BooleanField(default=False)
    seller_status = models.CharField(max_length=20, choices=[
        ('not_applied', 'Not Applied'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
        ('banned', 'Banned')
    ], default='not_applied', blank=True)
    
    seller_application_date = models.DateTimeField(null=True, blank=True)
    seller_approved_date = models.DateTimeField(null=True, blank=True)
    business_name = models.CharField(max_length=100, blank=True)
    business_description = models.TextField(blank=True)


    
    def __str__(self):
        return self.user.username
    

    def can_sell(self):
        return self.seller_status == 'approved'
    
    def is_seller_pending(self):
        return self.seller_status == 'pending'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()