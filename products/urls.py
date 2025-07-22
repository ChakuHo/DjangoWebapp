from django.urls import path
from . import views

urlpatterns = [
    path('', views.product, name='product'),
    path('<int:id>/', views.productDetails, name='productDetails')
]
