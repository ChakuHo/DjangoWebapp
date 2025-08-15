from django.shortcuts import render, redirect, get_object_or_404
from .models import Cart, CartItem
from products.models import Product
from django.core.exceptions import ObjectDoesNotExist



def _cart_id(request):
    cart = request.session.session_key

    if not cart:
        cart = request.session.create()
    return cart

def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
        cart.save()

    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        if cart_item.quantity < product.stock:  # FIX: hard cap at stock
            cart_item.quantity += 1
            cart_item.save()
    # else: already at max, do nothing
    except CartItem.DoesNotExist:  # FIX: correct exception
        if product.stock > 0:       # FIX: only add if stock available
            CartItem.objects.create(product=product, quantity=1, cart=cart)

    return redirect('cart')


def remove_cart(request, product_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    cart_item = CartItem.objects.get(product=product, cart=cart)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()

    else:
        cart_item.delete()
    return redirect('cart')
    
def remove_cart_item(request, product_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    cart_item = CartItem.objects.get(product=product, cart=cart)
    cart_item.delete()
    return redirect('cart')

def cart(request, total=0, quantity=0, cart_items = None):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
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









# def cart_view(request):
#     cart = request.session.get('cart', {})
#     items = []
#     total = 0
#     for product_id_str, quantity in cart.items():
#         product = get_object_or_404(Product, id=product_id_str)
#         item_total = product.price * quantity
#         total += item_total
#         items.append({
#             'product': product,
#             'quantity': quantity,
#             'item_total': item_total,
#         })
#     tax = total * 0.13
#     grand_total = total + tax
#     return render(request, 'cart/cart.html', {
#         'items': items,
#         'total': total,
#         'tax': tax,
#         'grand_total': grand_total,
#     })



# def add_to_cart(request, product_id):
#     print("add_to_cart called")
#     product = get_object_or_404(Product, id=product_id)
#     cart = request.session.get('cart', {})
#     product_id_str = str(product_id)
#     cart[product_id_str] = cart.get(product_id_str, 0) + 1
#     request.session['cart'] = cart
#     request.session.modified = True
#     return redirect('cart')


# def remove_from_cart(request, product_id):
#     cart = request.session.get('cart', {})
#     product_id_str = str(product_id)
#     if product_id_str in cart:
#         del cart[product_id_str]
#         request.session['cart'] = cart
#         request.session.modified = True
#     return redirect('cart')