from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-complete/<int:order_id>/', views.order_complete, name='order_complete'),
    path('esewa-success/', views.esewa_success, name='esewa_success'),
    path('esewa-failure/', views.esewa_failure, name='esewa_failure'),
    path('khalti-verify/', views.khalti_verify, name='khalti_verify'),
    path('esewa-start/<int:order_id>/', views.esewa_start, name='esewa_start'),
    path('esewa-return/<int:order_id>/', views.esewa_return, name='esewa_return'),


]