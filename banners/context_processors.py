from .models import Banner

def active_banners(request):
    try:
        banners = Banner.objects.select_related('category').filter(is_active=True)
        # Filter only live banners
        live_banners = [b for b in banners if b.is_live()]
        return {'banners': live_banners}
    except Exception as e:
        print(f"Error in banner context processor: {e}")  # For debugging
        return {'banners': []}