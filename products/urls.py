from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # All products - /products/
    path('', views.product, name="product"),
    
    # Sale products - /products/sale/
    path('sale/', views.sale_products, name='sale_products'),
    
    # Thrift products - /products/thrift/
    path('thrift/', views.thrift_products, name='thrift_products'),
    
    # Thrift by category - /products/thrift/category/electronics/
    path('thrift/category/<slug:category_slug>/', views.thrift_products, name='thrift_by_category'),

    # Products by category - /products/category/electronics/
    path('category/<slug:category_slug>/', views.product, name='products_by_category'),

    # Product detail - /products/category/electronics/laptop-hp/
    path('category/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),

    # Search - /products/search/
    path('search/', views.search, name="search"),

    # Review
    path('review/submit/<int:product_id>/', views.submit_review, name='submit_review'),

    # Seller path 
    path('seller/<int:seller_id>/', views.seller_products, name='seller_products'),

]