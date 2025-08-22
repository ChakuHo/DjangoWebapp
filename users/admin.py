from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    
    list_display = ('user', 'phone_number', 'city', 'country', 'seller_status', 'business_name', 'seller_application_date')
    list_filter = ('city', 'country', 'seller_status', 'seller_application_date')  
    search_fields = ('user__username', 'user__email', 'phone_number', 'business_name')  
    readonly_fields = ('seller_application_date',)  
    
  
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'profile_picture')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state', 'country')
        }),
        ('Seller Management', {
            'fields': ('seller_status', 'business_name', 'business_description', 
                      'seller_application_date', 'seller_approved_date'),
            'classes': ('wide',),
        }),
    )
    
  
    actions = ['approve_sellers', 'suspend_sellers', 'ban_sellers', 'activate_sellers']
    
    def approve_sellers(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            seller_status='approved',
            seller_approved_date=timezone.now()
        )
        self.message_user(request, f'{updated} sellers have been approved.')
    approve_sellers.short_description = "✅ Approve selected sellers"
    
    def suspend_sellers(self, request, queryset):
        updated = queryset.update(seller_status='suspended')
        self.message_user(request, f'{updated} sellers have been suspended.')
    suspend_sellers.short_description = "⏸️ Suspend selected sellers"
    
    def ban_sellers(self, request, queryset):
        updated = queryset.update(seller_status='banned')
        self.message_user(request, f'{updated} sellers have been banned.')
    ban_sellers.short_description = "🚫 Ban selected sellers"
    
    def activate_sellers(self, request, queryset):
        updated = queryset.update(seller_status='approved')
        self.message_user(request, f'{updated} sellers have been activated.')
    activate_sellers.short_description = "✅ Activate selected sellers"
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return ('user', 'seller_application_date')
        return ('seller_application_date',)


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_seller_status', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__seller_status', 'date_joined')
    
    def get_seller_status(self, obj):
        try:
            return obj.profile.seller_status.title()
        except:
            return 'Not Set'
    get_seller_status.short_description = 'Seller Status'
    get_seller_status.admin_order_field = 'profile__seller_status'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)