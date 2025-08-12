from .models import Page

def all_pages(request):
    return {
        'pages': Page.objects.all()
    }