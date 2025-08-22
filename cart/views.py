from django.shortcuts import render, redirect, get_object_or_404
from .models import Cart, CartItem
from products.models import Product
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def _get_cart(request):
    """Get cart based on user status - user-based if logged in, session-based if anonymous"""
    if request.user.is_authenticated:
        # For authenticated users, get or create cart by user
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # For anonymous users, get or create cart by session
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id=_cart_id(request))
    return cart

def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = _get_cart(request)

    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f"{product.name} added to cart!")
        else:
            messages.error(request, f"Sorry, only {product.stock} {product.name} available!")
    except CartItem.DoesNotExist:
        if product.stock > 0:
            CartItem.objects.create(product=product, quantity=1, cart=cart)
            messages.success(request, f"{product.name} added to cart!")
        else:
            messages.error(request, f"Sorry, {product.name} is out of stock!")

    return redirect('cart')

def remove_cart(request, product_id):
    cart = _get_cart(request)
    product = get_object_or_404(Product, id=product_id)
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    return redirect('cart')
    
def remove_cart_item(request, product_id):
    cart = _get_cart(request)
    product = get_object_or_404(Product, id=product_id)
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    return redirect('cart')

def cart(request, total=0, quantity=0, cart_items=None):
    try:
        cart = _get_cart(request)
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity

    except ObjectDoesNotExist:
        cart_items = []
        
    tax = 0.13 * total
    grand_total = total + tax

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total
    }

    return render(request, 'cart/cart.html', context)

def merge_cart_on_login(request):
    """Call this when user logs in to merge session cart with user cart"""
    if request.user.is_authenticated:
        try:
            # Get session cart
            session_cart = Cart.objects.get(cart_id=_cart_id(request))
            session_cart_items = CartItem.objects.filter(cart=session_cart, is_active=True)
            
            # Get or create user cart
            user_cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Merge session cart items into user cart
            for session_item in session_cart_items:
                try:
                    # If item already exists in user cart, add quantities
                    user_item = CartItem.objects.get(product=session_item.product, cart=user_cart)
                    user_item.quantity += session_item.quantity
                    user_item.save()
                except CartItem.DoesNotExist:
                    # If item doesn't exist in user cart, create it
                    CartItem.objects.create(
                        product=session_item.product,
                        cart=user_cart,
                        quantity=session_item.quantity
                    )
            
            # Delete session cart after merging
            session_cart_items.delete()
            session_cart.delete()
            
        except Cart.DoesNotExist:
            # No session cart to merge
            pass

def merge_session_cart_to_user(request):
    """Merge session cart into user cart when user logs in"""
    if request.user.is_authenticated:
        # Get session cart
        session_cart_id = request.session.session_key
        if session_cart_id:
            try:
                session_cart = Cart.objects.get(cart_id=session_cart_id)
                session_items = CartItem.objects.filter(cart=session_cart, is_active=True)
                
                if session_items.exists():
                    # Get or create user cart
                    user_cart, created = Cart.objects.get_or_create(user=request.user)
                    
                    # Merge each item
                    for session_item in session_items:
                        try:
                            # If item exists in user cart, add quantities
                            user_item = CartItem.objects.get(product=session_item.product, cart=user_cart)
                            user_item.quantity += session_item.quantity
                            user_item.save()
                        except CartItem.DoesNotExist:
                            # Create new item in user cart
                            CartItem.objects.create(
                                product=session_item.product,
                                cart=user_cart,
                                quantity=session_item.quantity
                            )
                    
                    # Delete session cart after merging
                    session_items.delete()
                    session_cart.delete()
                    
            except Cart.DoesNotExist:
                pass