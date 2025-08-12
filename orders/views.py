from django.shortcuts import render, get_object_or_404, redirect
from .models import Order, OrderItem
from cart.models import Cart, CartItem

def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})

def order_complete(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_complete.html', {'order': order})

def place_order(request):
    # latest order for the user
    order = Order.objects.filter(user=request.user).last()
    items = order.items.all() if order else []
    return render(request, 'orders/place_order.html', {'order': order, 'items': items})