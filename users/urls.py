from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard and Profile URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Seller URLs
    path('become-seller/', views.become_seller, name='become_seller'),
    path('my-selling-items/', views.my_selling_items, name='my_selling_items'),
    path('add-product/', views.add_product, name='add_product'),
    
    # Orders URLs
    path('received-orders/', views.received_orders, name='received_orders'),
    path('seller/orders/', views.seller_received_orders, name='seller_received_orders'),
    
    # QR Payment URLs
    path('update-qr/', views.update_qr, name='update_qr'),
    path('remove-qr/', views.remove_qr, name='remove_qr'),
    path('verify-qr-payments/', views.verify_qr_payments, name='verify_qr_payments'),

    # Product Management AJAX URLs 
    path('update-product-stock/<int:product_id>/', views.update_product_stock, name='update_product_stock'),
    path('toggle-product-status/<int:product_id>/', views.toggle_product_status, name='toggle_product_status'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('duplicate-product/<int:product_id>/', views.duplicate_product, name='duplicate_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('bulk-operations/', views.bulk_product_operations, name='bulk_product_operations'),
    
    # Chat URLs
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/<int:chat_id>/', views.chat_detail, name='chat_detail'),
    path('chat/user/<str:username>/', views.start_chat_with_user, name='start_chat_with_user'),
    path('chat/product/<int:product_id>/', views.start_chat_about_product, name='start_chat_about_product'),
    path('chat/send-message/', views.send_message, name='send_message'),
    path('chat/get-messages/<int:chat_id>/', views.get_new_messages, name='get_new_messages'),

    # Typing indicator URLs
    path('chat/<int:chat_id>/typing/set/', views.set_typing, name='set_typing'),
    path('chat/<int:chat_id>/typing/clear/', views.clear_typing, name='clear_typing'),
    path('chat/<int:chat_id>/typing/get/', views.get_typing_users, name='get_typing_users'),

    # Notification URLs
    path('clear-messages/', views.clear_messages, name='clear_messages'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/ajax/', views.get_notifications_ajax, name='get_notifications_ajax'),
    path('clear-notifications-only/', views.clear_notifications_only, name='clear_notifications_only'),
    path('clear-django-messages-only/', views.clear_django_messages_only, name='clear_django_messages_only'),
    
    # Wishlist URLs
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/check/', views.check_wishlist_status, name='check_wishlist_status'),
    path('wishlist/clear-all/', views.clear_all_wishlist, name='clear_all_wishlist'),

    # for customers
    path('received-orders/', views.received_orders, name='received_orders'),

    # for seller to update order status
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('mark-shipped/<int:order_id>/', views.mark_as_shipped, name='mark_as_shipped'),
    path('order-details/<int:order_id>/', views.order_details_modal, name='order_details_modal'),
    path('mark-delivered/<int:order_id>/', views.mark_delivered, name='mark_delivered'),

    # for admin approval
    path('admin/approve-seller/<int:user_id>/', views.approve_seller, name='approve_seller'),
    path('admin/reject-seller/<int:user_id>/', views.reject_seller, name='reject_seller'),
    path('admin/bulk-approve-sellers/', views.bulk_approve_sellers, name='bulk_approve_sellers'),
]