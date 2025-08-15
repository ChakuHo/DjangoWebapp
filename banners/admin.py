from django.contrib import admin
from django.utils.html import format_html
from .models import Banner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'category', 'preview')
    list_filter = ('is_active', 'category')
    search_fields = ('title', 'subtitle', 'alt_text')
    list_editable = ('order', 'is_active')

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;object-fit:cover;border-radius:4px" />', obj.image.url)
        return "-"
    preview.short_description = 'Preview'