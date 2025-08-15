from .models import Cart, CartItem
from .views import _cart_id

def counter(request):
    cart_count = 0
    if 'admin' in request.path:
        return {}
    try:
        cart = Cart.objects.filter(cart_id=_cart_id(request)).first() # FIX
        if cart:
            for item in CartItem.objects.filter(cart=cart):
                cart_count += item.quantity
    except Exception:
        cart_count = 0
    return {'cart_count': cart_count}   