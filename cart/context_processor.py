from .models import Cart, CartItem
from .views import _cart_id

def counter(request):
    cart_count = 0
    if 'admin' in request.path:
        return {}
    
    try:
        # Check if user is logged in
        if request.user.is_authenticated:
            # For logged-in users, get cart by user
            cart = Cart.objects.filter(user=request.user).first()
        else:
            # For anonymous users, get cart by session (your existing logic)
            cart = Cart.objects.filter(cart_id=_cart_id(request)).first()
        
        if cart:
            for item in CartItem.objects.filter(cart=cart, is_active=True):
                cart_count += item.quantity
    except Exception:
        cart_count = 0
    
    return {'cart_count': cart_count}