from django.shortcuts import render, redirect, get_object_or_404
from .models import Cart, CartItem
from products.models import Product, ProductVariation
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
import json
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse

def _cart_id(request):
    """Get or create session cart ID"""
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def _get_cart(request):
    """Get cart based on user authentication status"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id=_cart_id(request))
    return cart

def get_available_stock(product, variations):
    """Calculate available stock considering variations"""
    if not variations:
        return product.stock
    
    min_stock = product.stock
    for variation in variations:
        if variation.stock_quantity < min_stock:
            min_stock = variation.stock_quantity
    
    return max(0, min_stock)

def add_cart(request, product_id):
    """Enhanced add to cart with variation support and seller validation"""
    product = get_object_or_404(Product, id=product_id)
    cart = _get_cart(request)

    # Prevent seller from buying their own products
    if request.user.is_authenticated and product.seller == request.user:
        error_message = '❌ You cannot buy your own product!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': error_message}, status=400)
        else:
            messages.error(request, error_message)
            return redirect('products:product_detail', product.category.slug, product.slug)
    
    # Parse variations from request (if any)
    selected_variations = []
    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('variation_') and value:
                try:
                    variation_type_id = key.split('_')[1]
                    variation_option_id = value
                    product_variation = ProductVariation.objects.get(
                        product=product,
                        variation_type_id=variation_type_id,
                        variation_option_id=variation_option_id,
                        is_active=True
                    )
                    selected_variations.append(product_variation)
                except (ProductVariation.DoesNotExist, IndexError, ValueError):
                    continue
    
    # Check for existing cart item with same variations
    existing_item = None
    cart_items = CartItem.objects.filter(product=product, cart=cart, is_active=True)
    
    for item in cart_items:
        item_variations = list(item.variations.all())
        if len(item_variations) == len(selected_variations):
            match = True
            for variation in item_variations:
                if variation not in selected_variations:
                    match = False
                    break
            if match:
                existing_item = item
                break
    
    try:
        # Calculate available stock for the selected variations
        available_stock = get_available_stock(product, selected_variations)
        
        if existing_item:
            if existing_item.quantity < available_stock:
                existing_item.quantity += 1
                existing_item.save()
                success_message = f"{product.name} added to cart!"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    cart_count = CartItem.objects.filter(cart=cart, is_active=True).count()
                    return JsonResponse({
                        'success': True,
                        'message': success_message,
                        'cart_count': cart_count
                    })
                else:
                    messages.success(request, success_message)
                    return redirect('cart')
            else:
                error_message = f"Sorry, only {available_stock} available!"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': error_message}, status=400)
                else:
                    messages.error(request, error_message)
                    return redirect('cart')
        else:
            if available_stock > 0:
                cart_item = CartItem.objects.create(
                    product=product, 
                    quantity=1, 
                    cart=cart
                )
                # Add variations if any
                if selected_variations:
                    cart_item.variations.set(selected_variations)
                    cart_item.save()
                
                success_message = f"{product.name} added to cart!"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    cart_count = CartItem.objects.filter(cart=cart, is_active=True).count()
                    return JsonResponse({
                        'success': True,
                        'message': success_message,
                        'cart_count': cart_count
                    })
                else:
                    messages.success(request, success_message)
                    return redirect('cart')
            else:
                error_message = f"Sorry, {product.name} is out of stock!"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': error_message}, status=400)
                else:
                    messages.error(request, error_message)
                    return redirect('cart')
                
    except Exception as e:
        print(f"Error in add_cart: {e}")
        error_message = "Error adding to cart. Please try again."
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': error_message}, status=500)
        else:
            messages.error(request, error_message)
            return redirect('cart')

def remove_cart(request, product_id, cart_item_id=None):
    """Remove one quantity"""
    cart = _get_cart(request)
    
    try:
        if cart_item_id:
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
        else:
            cart_item = CartItem.objects.filter(product_id=product_id, cart=cart, is_active=True).first()
        
        if cart_item:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    
    return redirect('cart')

def remove_cart_item(request, product_id, cart_item_id=None):
    """Remove entire cart item"""
    cart = _get_cart(request)
    
    try:
        if cart_item_id:
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
        else:
            cart_item = CartItem.objects.filter(product_id=product_id, cart=cart, is_active=True).first()
        
        if cart_item:
            product_name = str(cart_item)
            cart_item.delete()
            messages.success(request, f"{product_name} removed from cart!")
    except CartItem.DoesNotExist:
        pass
    
    return redirect('cart')

def cart(request, total=0, quantity=0, cart_items=None):
    """Enhanced cart view with seller validation"""
    try:
        cart = _get_cart(request)
        cart_items = CartItem.objects.filter(cart=cart, is_active=True).prefetch_related(
            'variations__variation_type',
            'variations__variation_option'
        )
        
        # Remove seller's own products from cart
        if request.user.is_authenticated:
            own_products = cart_items.filter(product__seller=request.user)
            if own_products.exists():
                own_product_names = [item.product.name for item in own_products]
                own_products.delete()
                messages.warning(request, f"🗑️ Removed your own products from cart: {', '.join(own_product_names)}")
                # Refresh cart_items after deletion
                cart_items = CartItem.objects.filter(cart=cart, is_active=True).prefetch_related(
                    'variations__variation_type',
                    'variations__variation_option'
                )
        
        for cart_item in cart_items:
            total += cart_item.sub_total()
            quantity += cart_item.quantity
            
    except ObjectDoesNotExist:
        cart_items = []
        
    tax = 0.13 * total
    grand_total = total + tax
    
    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'items': cart_items,
        'tax': tax,
        'grand_total': grand_total
    }
    
    return render(request, 'cart/cart.html', context)

# 🔄 UNIFIED CART MERGE FUNCTION (replaces 2 duplicate functions)
def merge_carts_on_login(request):
    """Unified cart merging when user logs in"""
    if not request.user.is_authenticated:
        return
        
    session_cart_id = request.session.session_key
    if not session_cart_id:
        return
        
    try:
        session_cart = Cart.objects.get(cart_id=session_cart_id)
        session_items = CartItem.objects.filter(cart=session_cart, is_active=True)
        
        if session_items.exists():
            user_cart, created = Cart.objects.get_or_create(user=request.user)
            
            for session_item in session_items:
                # Skip seller's own products
                if session_item.product.seller == request.user:
                    continue
                    
                # Try to find existing user cart item with same variations
                existing_item = None
                for user_item in CartItem.objects.filter(product=session_item.product, cart=user_cart):
                    if set(user_item.variations.all()) == set(session_item.variations.all()):
                        existing_item = user_item
                        break
                
                if existing_item:
                    existing_item.quantity += session_item.quantity
                    existing_item.save()
                else:
                    new_item = CartItem.objects.create(
                        product=session_item.product,
                        cart=user_cart,
                        quantity=session_item.quantity
                    )
                    if session_item.variations.exists():
                        new_item.variations.set(session_item.variations.all())
            
            session_items.delete()
            session_cart.delete()
            
    except Cart.DoesNotExist:
        pass

# 🔄 UNIFIED GUEST CART HANDLER (replaces multiple scattered functions)
def handle_guest_cart_transition(request, action='preserve'):
    """Handle guest cart during authentication transitions"""
    
    if action == 'preserve' and not request.user.is_authenticated:
        # Preserve cart before authentication
        try:
            session_cart = Cart.objects.get(cart_id=_cart_id(request))
            session_items = CartItem.objects.filter(cart=session_cart, is_active=True)
            
            if session_items.exists():
                cart_data = []
                for item in session_items:
                    variation_ids = list(item.variations.values_list('id', flat=True))
                    cart_data.append({
                        'product_id': item.product.id,
                        'quantity': item.quantity,
                        'variation_ids': variation_ids
                    })
                request.session['guest_cart_data'] = cart_data
                request.session['redirect_after_login'] = 'checkout'
        except Cart.DoesNotExist:
            pass
    
    elif action == 'restore' and request.user.is_authenticated:
        # Restore after authentication
        merge_carts_on_login(request)
        
        guest_cart_data = request.session.get('guest_cart_data')
        if guest_cart_data:
            user_cart, created = Cart.objects.get_or_create(user=request.user)
            
            for item_data in guest_cart_data:
                try:
                    product = Product.objects.get(id=item_data['product_id'])
                    
                    # Skip seller's own products
                    if product.seller == request.user:
                        continue
                    
                    # Get variations if any
                    variations = []
                    if item_data.get('variation_ids'):
                        variations = ProductVariation.objects.filter(
                            id__in=item_data['variation_ids']
                        )
                    
                    # Check if item already exists in user cart
                    existing_items = CartItem.objects.filter(
                        product=product, 
                        cart=user_cart, 
                        is_active=True
                    )
                    
                    # Find exact match including variations
                    existing_item = None
                    for existing in existing_items:
                        existing_variation_ids = set(existing.variations.values_list('id', flat=True))
                        new_variation_ids = set(item_data.get('variation_ids', []))
                        if existing_variation_ids == new_variation_ids:
                            existing_item = existing
                            break
                    
                    if existing_item:
                        # Add quantities
                        existing_item.quantity += item_data['quantity']
                        existing_item.save()
                    else:
                        # Create new cart item
                        new_item = CartItem.objects.create(
                            product=product,
                            cart=user_cart,
                            quantity=item_data['quantity']
                        )
                        if variations:
                            new_item.variations.set(variations)
                            
                except Product.DoesNotExist:
                    continue
            
            # Clear the preserved cart data
            del request.session['guest_cart_data']
            messages.success(request, 'Your cart has been restored!')

def checkout_redirect(request):
    """Redirect to orders checkout with guest cart preservation"""
    if not request.user.is_authenticated:
        # Preserve guest cart
        handle_guest_cart_transition(request, action='preserve')
        messages.info(request, 'Please login or register to continue with checkout. Your cart will be preserved!')
        return redirect('login')
    else:

        return redirect('checkout')  