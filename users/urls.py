from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('logout/', views.logout_view, name='logout'),
    path('my-selling-items/', views.my_selling_items, name='my_selling_items'),
    path('received-orders/', views.received_orders, name='received_orders'),
    path('become-seller/', views.become_seller, name='become_seller'),
    path('add-product/', views.add_product, name='add_product'),

    # Chat URLs
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/<int:chat_id>/', views.chat_detail, name='chat_detail'),
    path('chat/user/<str:username>/', views.start_chat_with_user, name='start_chat_with_user'),
    path('chat/send-message/', views.send_message, name='send_message'),

    # CUSTOMER received orders (items they've received)
    path('received-orders/', views.received_orders, name='received_orders'),
    
    # SELLER received orders (orders from customers) 
    path('seller/orders/', views.seller_received_orders, name='seller_received_orders'),

    path('update-product-stock/<int:product_id>/', views.update_product_stock, name='update_product_stock'),
    path('toggle-product-status/<int:product_id>/', views.toggle_product_status, name='toggle_product_status'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('bulk-update-stock/', views.bulk_update_stock, name='bulk_update_stock'),


]