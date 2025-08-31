from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/', views.home, name='home'),
    path('', views.home, name="home"),
    path('products/', include('products.urls', namespace='products')),
    path('store/', include('products.urls', namespace='store')),  # Same as products but different namespace
    path('blog/', include('blog.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    
    # Users URLs at root level for clean URLs
    path('users/', include('users.urls')),
    
    # Contact pages
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)