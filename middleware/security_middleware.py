from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse

class LoginRequiredMiddleware:
    """
    Middleware to ensure login is required for all protected URLs
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define ALL protected URL patterns
        self.protected_patterns = [
            # Users app - Dashboard and profile
            '/users/dashboard/',
            '/users/edit-profile/',
            '/users/change-password/',
            
            # Seller functionality
            '/users/become-seller/',
            '/users/my-selling-items/',
            '/users/add-product/',
            '/users/received-orders/',
            '/users/seller/orders/',
            '/users/update-qr/',
            '/users/remove-qr/',
            '/users/verify-qr-payments/',
            
            # Product management
            '/users/update-product-stock/',
            '/users/toggle-product-status/',
            '/users/delete-product/',
            '/users/duplicate-product/',
            '/users/edit-product/',
            '/users/bulk-operations/',
            
            # Chat system
            '/users/chat/',
            
            # Notifications
            '/users/clear-messages/',
            '/users/notifications/',
            '/users/clear-notifications-only/',
            '/users/clear-django-messages-only/',
            
            # Wishlist
            '/users/wishlist/',
            
            # Order management
            '/users/update-order-status/',
            '/users/mark-shipped/',
            '/users/order-details/',
            '/users/mark-delivered/',
            
            # Orders app
            '/orders/checkout/',
            '/orders/place-order/',
            '/orders/my-orders/',
            '/orders/order-complete/',
            '/orders/esewa-start/',
            '/orders/esewa-return/',
            '/orders/confirm-qr-payment/',
            
            # Cart checkout
            '/cart/checkout/',
        ]
        
        # URLs that should always be accessible
        self.public_patterns = [
            '/',
            '/home/',
            '/users/login/',
            '/users/register/',
            '/users/logout/',
            '/products/',
            '/store/',
            '/blog/',
            '/cart/',  # Cart viewing is OK for guests
            '/cart/add/',  # Adding to cart is OK for guests
            '/cart/remove/',
            '/cart/remove_item/',
            '/contact/',
            '/about/',
            '/admin/',
            '/media/',
            '/static/',
        ]

    def __call__(self, request):
        current_path = request.path
        
        # Skip check for public URLs
        if any(current_path.startswith(pattern) for pattern in self.public_patterns):
            return self.get_response(request)
        
        # Check if current path needs authentication
        needs_login = any(current_path.startswith(pattern) for pattern in self.protected_patterns)
        
        if needs_login and not request.user.is_authenticated:
            # For AJAX requests, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please login to access this feature.',
                    'redirect_url': f"{settings.LOGIN_URL}?next={request.get_full_path()}"
                }, status=401)
            
            # Store the URL user was trying to access
            request.session['next'] = request.get_full_path()
            
            messages.warning(request, '🔒 Please login to access this page.')
            return redirect(f"{settings.LOGIN_URL}?next={request.get_full_path()}")
        
        response = self.get_response(request)
        return response