from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

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
    
    # QR CODE PAYMENT FIELDS
    payment_qr_code = models.ImageField(
        upload_to='seller_qr_codes/', 
        blank=True, 
        null=True,
        help_text="Upload your QR code for payments (eSewa, Khalti, Bank QR, etc.)"
    )
    qr_payment_method = models.CharField(
        max_length=50, 
        blank=True,
        choices=[
            ('esewa', 'eSewa'),
            ('bank', 'Bank QR'),
            ('fonepay', 'FonePay'),
            ('connectips', 'ConnectIPS'),
            ('other', 'Other')
        ],
        help_text="Which payment method does this QR code support?"
    )
    qr_payment_info = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Additional info like phone number or account name"
    )

    #  Chat activity tracking
    last_seen = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(default=False)

# Wishlist

    def get_wishlist_count(self):
        """Get wishlist count for this user"""
        return Wishlist.objects.filter(user=self.user).count()    

    def has_payment_qr(self):
        """Check if profile has a payment QR code"""
        return bool(self.payment_qr_code)

    def get_qr_display_name(self):
        """Get display name for QR payment method"""
        method_names = {
            'esewa': 'eSewa',
            'khalti': 'Khalti', 
            'fonepay': 'FonePay',
            'connectips': 'ConnectIPS',
            'imepay': 'IME Pay',
            'other': 'Other'
        }
        return method_names.get(self.qr_payment_method, 'Digital Wallet')    
    
    def __str__(self):
        return self.user.username
    
    def can_sell(self):
        return self.seller_status == 'approved'
    
    def is_seller_pending(self):
        return self.seller_status == 'pending'
    
    def get_unread_messages_count(self):
        """Get count of unread messages for this user"""
        return ChatMessage.objects.filter(
            chat_room__participants=self.user,
            is_read=False
        ).exclude(sender=self.user).count()
    
    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])


class ChatRoom(models.Model):
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For product-specific chats
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, null=True, blank=True)
    
    #  Chat room settings
    is_active = models.BooleanField(default=True)
    archived_by = models.ManyToManyField(User, related_name='archived_chats', blank=True)
    
    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()])
        product_info = f" (About: {self.product.name})" if self.product else ""
        return f"Chat: {participant_names}{product_info}"
    
    def get_other_participant(self, current_user):
        """Get the other participant in a 2-person chat"""
        try:
            participants = self.participants.all()
            for participant in participants:
                if participant != current_user:
                    return participant
            return None
        except Exception:
            return None
    
    def get_last_message(self):
        return self.messages.last()
    
    def get_unread_count_for_user(self, user):
        """Get unread message count for specific user"""
        return self.messages.filter(
            is_read=False
        ).exclude(sender=user).count()


class ChatMessage(models.Model):
    # Message status choices
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]
    
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # Enhanced message status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    read_at = models.DateTimeField(null=True, blank=True)
    
    # File attachments
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    attachment_type = models.CharField(max_length=20, blank=True)  # image, document, etc.
    
    #  Message type for system messages
    message_type = models.CharField(max_length=20, default='text', choices=[
        ('text', 'Text'),
        ('image', 'Image'),
        ('document', 'Document'),
        ('system', 'System'),
    ])
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"
    
    def mark_as_read(self, by_user=None):
        """Mark message as read"""
        if not self.is_read and self.sender != by_user:
            self.is_read = True
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'status', 'read_at'])
    
    def get_status_icon(self):
        """Get status icon for message"""
        icons = {
            'sent': '✓',
            'delivered': '✓✓',
            'read': '✓✓',
        }
        return icons.get(self.status, '✓')
    
    def get_time_display(self):
        """Get human-readable time display"""
        now = timezone.now()
        diff = now - self.timestamp
        
        if diff.days > 7:
            return self.timestamp.strftime('%m/%d/%Y')
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"


# NEW: Typing indicator model
class TypingIndicator(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='typing_indicators')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['chat_room', 'user']
    
    def __str__(self):
        return f"{self.user.username} typing in {self.chat_room}"
        
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('system', 'System'),
        ('order', 'Order'),
        ('message', 'Message'),
        ('product_approved', 'Product Approved'),
        ('product_rejected', 'Product Rejected'),
        ('qr_payment', 'QR Payment'),
        ('order_status', 'Order Status'),
    ]
    
    COLOR_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('success', 'Success'),
        ('danger', 'Danger'),
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('light', 'Light'),
        ('dark', 'Dark'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=100)
    message = models.TextField()
    icon = models.CharField(max_length=50, default='fa-bell')
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='primary')
    url = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def get_time_display(self):
        """Get human-readable time display"""
        now = timezone.now()
        diff = now - self.created_at
        
        if diff.days > 7:
            return self.created_at.strftime('%m/%d/%Y')
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

    @staticmethod
    def get_wishlist_count(user):
        """Get wishlist count for user"""
        if user.is_authenticated:
            return Wishlist.objects.filter(user=user).count()
        return 0

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()