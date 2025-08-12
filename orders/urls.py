from django.urls import path
from . import views

urlpatterns = [
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-complete/<int:order_id>/', views.order_complete, name='order_complete'),
    path('place-order/', views.place_order, name='place_order'),
]