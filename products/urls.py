from django.urls import path
from . import views

app_name = 'products' 

urlpatterns = [
    # All products - /products/
    path('', views.product, name="product"),
    
    # Products by category - /products/category/electronics/
    path('category/<slug:category_slug>/', views.product, name='products_by_category'),
    
    # Product detail - /products/category/electronics/laptop-hp/
    path('category/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    
    # Search - /products/search/
    path('search/', views.search, name="search"),
]