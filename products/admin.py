from django.contrib import admin
from .models import Product, Category, Review, VariationType, VariationOption, CategoryVariation, ProductVariation  # Added variation imports
from django.utils.html import format_html


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id','category_name')
admin.site.register(Category, CategoryAdmin)

# Variation Inline for ProductAdmin
class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 0
    fields = ('variation_type', 'variation_option', 'price_adjustment', 'stock_quantity', 'sku', 'is_active')
    autocomplete_fields = ['variation_option'] 


class ProductAdmin(admin.ModelAdmin):
    exclude = ('created_at',)
    readonly_fields = ('slug', 'submitted_for_approval')  
    

    inlines = [ProductVariationInline]
    

    list_display = ('id', 'name', 'seller', 'price', 'short_description', 'brand', 'stock', 
                   'admin_approved', 'approval_status', 'status', 'category', 'created_at', 'show_image')
    

    list_filter = ('status', 'admin_approved', 'approval_status', 'category', 'brand', 'seller')
    
    search_fields = ('name', 'brand', 'slug', 'seller__username')
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'description', 'category', 'price', 'stock', 'image', 'brand', 'spec')
        }),
        ('Seller Information', {
            'fields': ('seller',)
        }),
        ('Approval Management', {
            'fields': ('admin_approved', 'approval_status', 'rejection_reason', 'submitted_for_approval'),
            'classes': ('wide',),
        }),
        ('Status', {
            'fields': ('status', 'slug')
        }),
    )
    
    actions = ['approve_products', 'reject_products', 'make_active', 'make_inactive']
    
    def approve_products(self, request, queryset):
        updated = queryset.update(admin_approved=True, approval_status='approved', status=True)
        self.message_user(request, f'{updated} products have been approved and activated.')
    approve_products.short_description = "✅ Approve and activate selected products"
    
    def reject_products(self, request, queryset):
        updated = queryset.update(admin_approved=False, approval_status='rejected', status=False)
        self.message_user(request, f'{updated} products have been rejected.')
    reject_products.short_description = "❌ Reject selected products"
    
    def make_active(self, request, queryset):
        updated = queryset.update(status=True)
        self.message_user(request, f'{updated} products have been activated.')
    make_active.short_description = "🟢 Activate selected products"
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(status=False)
        self.message_user(request, f'{updated} products have been deactivated.')
    make_inactive.short_description = "🔴 Deactivate selected products"

    def short_description(self, obj):
        return ' '.join(obj.description.split()[:6]) + '...'

    def show_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit: cover; border-radius:50%;" />', obj.image.url)
        return "No Image"
    show_image.short_description = 'Image'

admin.site.register(Product, ProductAdmin)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'status', 'created_at', 'verified_purchase_badge')
    list_filter = ('status', 'rating', 'created_at', 'verified_purchase')
    search_fields = ('product__name', 'user__username', 'subject')
    readonly_fields = ('created_at', 'updated_at', 'ip')
    
    def verified_purchase_badge(self, obj):
        if hasattr(obj, 'verified_purchase') and obj.verified_purchase:
            return format_html('<span style="color: green;">✅ Verified</span>')
        return format_html('<span style="color: orange;">⚠️ Unverified</span>')
    verified_purchase_badge.short_description = 'Purchase Status'
    
    actions = ['approve_reviews', 'reject_reviews']
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(status=True)
        self.message_user(request, f'{updated} reviews have been approved.')
    approve_reviews.short_description = "✅ Approve selected reviews"
    
    def reject_reviews(self, request, queryset):
        updated = queryset.update(status=False)
        self.message_user(request, f'{updated} reviews have been hidden.')
    reject_reviews.short_description = "❌ Hide selected reviews"

@admin.register(VariationType)
class VariationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'display_name')

@admin.register(VariationOption)
class VariationOptionAdmin(admin.ModelAdmin):
    list_display = ('variation_type', 'value', 'display_value', 'color_code', 'is_active', 'sort_order')
    list_filter = ('variation_type', 'is_active')
    search_fields = ('value', 'display_value')
    list_editable = ('sort_order', 'is_active')

@admin.register(CategoryVariation)
class CategoryVariationAdmin(admin.ModelAdmin):
    list_display = ('category', 'variation_type', 'is_required', 'sort_order')
    list_filter = ('category', 'variation_type', 'is_required')
    list_editable = ('is_required', 'sort_order')

@admin.register(ProductVariation)
class ProductVariationAdmin(admin.ModelAdmin):
    list_display = ('product', 'variation_type', 'variation_option', 'price_adjustment', 'stock_quantity', 'is_active')
    list_filter = ('variation_type', 'is_active', 'product__category')
    search_fields = ('product__name', 'variation_option__value')
    list_editable = ('price_adjustment', 'stock_quantity', 'is_active')
    autocomplete_fields = ['product', 'variation_option']