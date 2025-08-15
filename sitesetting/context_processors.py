from . models import SiteSetting

def site_settings(request):
    setting = SiteSetting.objects.first()  # Get the first SiteSetting object
    return {
        'site_settings': setting
    }