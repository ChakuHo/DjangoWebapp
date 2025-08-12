from django.urls import path
from . import views

urlpatterns = [
    path('', views.product, name='product'),
    path('category/<str:category>/<str:product>/', views.product_detail, name='product_detail'), 
    path('<int:id>/', views.productDetails, name='productDetails'),
]