from django.shortcuts import render, redirect, get_object_or_404
from .models import Cart, CartItem
from products.models import Product

def cart_view(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0
    for product_id_str, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id_str)
        item_total = product.price * quantity
        total += item_total
        items.append({
            'product': product,
            'quantity': quantity,
            'item_total': item_total,
        })
    tax = total * 0.13
    grand_total = total + tax
    return render(request, 'cart/cart.html', {
        'items': items,
        'total': total,
        'tax': tax,
        'grand_total': grand_total,
    })



def add_to_cart(request, product_id):
    print("add_to_cart called")
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    cart[product_id_str] = cart.get(product_id_str, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')


def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        request.session.modified = True
    return redirect('cart')