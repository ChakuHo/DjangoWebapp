# users/notification_utils.py
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def create_notification(user, notification_type, title, message, icon='fa-bell', color='primary', url=''):
    """Create a new notification for a user"""
    try:
        from django.apps import apps
        Notification = apps.get_model('users', 'Notification')
        
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            icon=icon,
            color=color,
            url=url
        )
        logger.info(f"Notification created for {user.username}: {title}")
        return notification
    except Exception as e:
        logger.error(f"Error creating notification for {user.username}: {e}")
        return None

def notify_new_message(receiver, sender, product=None):
    """Notify user about new message"""
    try:
        if product:
            title = "New Message About Product"
            message = f"{sender.get_full_name() or sender.username} sent you a message about {product.name}"
            url = reverse('chat_list')
        else:
            title = "New Message"
            message = f"{sender.get_full_name() or sender.username} sent you a message"
            url = reverse('chat_list')
        
        create_notification(
            user=receiver,
            notification_type='message',
            title=title,
            message=message,
            icon='fa-comments',
            color='info',
            url=url
        )
        logger.info(f"Message notification sent to {receiver.username} from {sender.username}")
    except Exception as e:
        logger.error(f"Error creating message notification: {e}")

def notify_new_order(seller, order):
    """Notify seller about new order"""
    try:
        title = "New Order Received!"
        message = f"Order #{order.order_number} received from {order.user.get_full_name() or order.user.username}"
        url = reverse('seller_received_orders')
        
        create_notification(
            user=seller,
            notification_type='order',
            title=title,
            message=message,
            icon='fa-shopping-bag',
            color='success',
            url=url
        )
        logger.info(f"New order notification sent to seller {seller.username} for order {order.order_number}")
    except Exception as e:
        logger.error(f"Error creating new order notification: {e}")

def notify_qr_payment_verification(seller, order):
    """Notify seller about QR payment needing verification"""
    try:
        title = "QR Payment Verification Needed"
        message = f"Order #{order.order_number} payment needs verification"
        url = reverse('verify_qr_payments')
        
        create_notification(
            user=seller,
            notification_type='qr_payment',
            title=title,
            message=message,
            icon='fa-qrcode',
            color='warning',
            url=url
        )
        logger.info(f"QR payment verification notification sent to {seller.username} for order {order.order_number}")
    except Exception as e:
        logger.error(f"Error creating QR payment verification notification: {e}")

def notify_product_approved(seller, product):
    """Notify seller about product approval"""
    try:
        title = "Product Approved!"
        message = f'Your product "{product.name}" has been approved and is now live'
        url = reverse('my_selling_items')
        
        create_notification(
            user=seller,
            notification_type='product_approved',
            title=title,
            message=message,
            icon='fa-check-circle',
            color='success',
            url=url
        )
        logger.info(f"Product approval notification sent to {seller.username} for product {product.name}")
    except Exception as e:
        logger.error(f"Error creating product approval notification: {e}")

def notify_product_rejected(seller, product):
    """Notify seller about product rejection"""
    try:
        title = "Product Rejected"
        message = f'Your product "{product.name}" was not approved. Please review and resubmit.'
        url = reverse('my_selling_items')
        
        create_notification(
            user=seller,
            notification_type='product_rejected',
            title=title,
            message=message,
            icon='fa-times-circle',
            color='danger',
            url=url
        )
        logger.info(f"Product rejection notification sent to {seller.username} for product {product.name}")
    except Exception as e:
        logger.error(f"Error creating product rejection notification: {e}")

def notify_order_status_update(customer, order):
    """Notify customer about order status update"""
    try:
        title = "Order Status Updated"
        message = f"Order #{order.order_number} status: {order.get_order_status_display()}"
        url = "/orders/my-orders/"
        
        create_notification(
            user=customer,
            notification_type='order_status',
            title=title,
            message=message,
            icon='fa-truck',
            color='info',
            url=url
        )
        logger.info(f"Order status update notification sent to {customer.username} for order {order.order_number}")
    except Exception as e:
        logger.error(f"Error creating order status update notification: {e}")

def notify_seller_approved(seller):
    """Notify user when they become an approved seller"""
    try:
        title = "Seller Application Approved!"
        message = "Congratulations! Your seller application has been approved. You can now start adding products."
        url = reverse('add_product')
        
        create_notification(
            user=seller,
            notification_type='system',
            title=title,
            message=message,
            icon='fa-store',
            color='success',
            url=url
        )
        logger.info(f"Seller approval notification sent to {seller.username}")
    except Exception as e:
        logger.error(f"Error creating seller approval notification: {e}")

def notify_seller_rejected(user):
    """Notify user when their seller application is rejected"""
    try:
        title = "Seller Application Not Approved"
        message = "Your seller application was not approved at this time. Please review requirements and reapply."
        url = reverse('become_seller')
        
        create_notification(
            user=user,
            notification_type='system',
            title=title,
            message=message,
            icon='fa-times-circle',
            color='danger',
            url=url
        )
        logger.info(f"Seller rejection notification sent to {user.username}")
    except Exception as e:
        logger.error(f"Error creating seller rejection notification: {e}")

def notify_welcome(user):
    """Send welcome notification to new users"""
    try:
        title = "Welcome to ISLINGTON MARKETPLACE!"
        message = "Welcome! Start exploring products or apply to become a seller to start your business."
        url = reverse('dashboard')
        
        create_notification(
            user=user,
            notification_type='system',
            title=title,
            message=message,
            icon='fa-hand-wave',
            color='primary',
            url=url
        )
        logger.info(f"Welcome notification sent to {user.username}")
    except Exception as e:
        logger.error(f"Error creating welcome notification: {e}")

def mark_all_notifications_read(user):
    """Mark all notifications as read for a user"""
    try:
        from django.apps import apps
        Notification = apps.get_model('users', 'Notification')
        
        updated_count = Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        logger.info(f"Marked {updated_count} notifications as read for {user.username}")
        return True
    except Exception as e:
        logger.error(f"Error marking notifications as read for {user.username}: {e}")
        return False

def get_unread_notification_count(user):
    """Get count of unread notifications for user"""
    try:
        from django.apps import apps
        Notification = apps.get_model('users', 'Notification')
        
        count = Notification.objects.filter(user=user, is_read=False).count()
        return count
    except Exception as e:
        logger.error(f"Error getting notification count for {user.username}: {e}")
        return 0

def get_recent_notifications(user, limit=10):
    """Get recent notifications for user"""
    try:
        from django.apps import apps
        Notification = apps.get_model('users', 'Notification')
        
        notifications = Notification.objects.filter(user=user).order_by('-created_at')[:limit]
        return notifications
    except Exception as e:
        logger.error(f"Error getting notifications for {user.username}: {e}")
        return []

def clean_old_notifications(user, days=30):
    """Clean notifications older than specified days"""
    try:
        from django.apps import apps
        Notification = apps.get_model('users', 'Notification')
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = Notification.objects.filter(user=user, created_at__lt=cutoff_date).delete()[0]
        logger.info(f"Cleaned {deleted_count} old notifications for {user.username}")
        return True
    except Exception as e:
        logger.error(f"Error cleaning notifications for {user.username}: {e}")
        return False

def bulk_mark_notifications_read(user, notification_ids):
    """Mark specific notifications as read"""
    try:
        from django.apps import apps
        Notification = apps.get_model('users', 'Notification')
        
        updated_count = Notification.objects.filter(
            user=user, 
            id__in=notification_ids,
            is_read=False
        ).update(is_read=True)
        logger.info(f"Marked {updated_count} specific notifications as read for {user.username}")
        return True
    except Exception as e:
        logger.error(f"Error marking specific notifications as read for {user.username}: {e}")
        return False

def delete_notification(user, notification_id):
    """Delete a specific notification"""
    try:
        from django.apps import apps
        Notification = apps.get_model('users', 'Notification')
        
        deleted_count = Notification.objects.filter(user=user, id=notification_id).delete()[0]
        if deleted_count > 0:
            logger.info(f"Deleted notification {notification_id} for {user.username}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id} for {user.username}: {e}")
        return False

def get_notifications_by_type(user, notification_type, limit=10):
    """Get notifications of specific type for user"""
    try:
        from django.apps import apps
        Notification = apps.get_model('users', 'Notification')
        
        notifications = Notification.objects.filter(
            user=user, 
            notification_type=notification_type
        ).order_by('-created_at')[:limit]
        return notifications
    except Exception as e:
        logger.error(f"Error getting {notification_type} notifications for {user.username}: {e}")
        return []

def create_system_notification(user, title, message, url=''):
    """Create a system notification"""
    return create_notification(
        user=user,
        notification_type='system',
        title=title,
        message=message,
        icon='fa-info-circle',
        color='info',
        url=url
    )

def notify_low_stock(seller, product, threshold=5):
    """Notify seller when product stock is low"""
    try:
        if product.stock <= threshold:
            title = "Low Stock Alert"
            message = f'Your product "{product.name}" has only {product.stock} units left in stock'
            url = reverse('my_selling_items')
            
            create_notification(
                user=seller,
                notification_type='system',
                title=title,
                message=message,
                icon='fa-exclamation-triangle',
                color='warning',
                url=url
            )
            logger.info(f"Low stock notification sent to {seller.username} for product {product.name}")
    except Exception as e:
        logger.error(f"Error creating low stock notification: {e}")

def notify_payment_received(seller, order):
    """Notify seller when payment is received"""
    try:
        title = "Payment Received"
        message = f"Payment confirmed for Order #{order.order_number}"
        url = reverse('seller_received_orders')
        
        create_notification(
            user=seller,
            notification_type='order',
            title=title,
            message=message,
            icon='fa-money-bill-wave',
            color='success',
            url=url
        )
        logger.info(f"Payment received notification sent to {seller.username} for order {order.order_number}")
    except Exception as e:
        logger.error(f"Error creating payment received notification: {e}")