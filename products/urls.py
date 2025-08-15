from django.urls import path
from . import views

urlpatterns = [
    path('', views.product, name="product"),
    # path('category/<str:category>/<str:product>/', views.product_detail, name='product_detail'), 
    # path('<int:id>/', views.productDetails, name='productDetails'),
    path('category/<slug:category_slug>/', views.product, name='products_by_category'),
    path('category/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('search/', views.search, name="search"),
]