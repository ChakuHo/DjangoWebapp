from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Order, OrderItem
from cart.models import Cart, CartItem
import uuid

@login_required
def checkout(request):
    """Display checkout page with cart items and forms"""
    try:
        cart = Cart.objects.get(user=request.user)
        items = CartItem.objects.filter(cart=cart)
        
        if not items.exists():
            messages.error(request, 'Your cart is empty!')
            return redirect('cart_detail')  # Redirect to cart page
        
        # Calculate totals
        total = sum(item.product.price * item.quantity for item in items)
        tax = total * 0.1  # 10% tax
        grand_total = total + tax
        
        context = {
            'items': items,
            'total': total,
            'tax': tax,
            'grand_total': grand_total,
        }
        return render(request, 'orders/checkout.html', context)
    
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty!')
        return redirect('cart_detail')

@login_required
def place_order(request):
    """Process order creation from checkout form"""
    if request.method == 'POST':
        try:
            cart = Cart.objects.get(user=request.user)
            items = CartItem.objects.filter(cart=cart)
            
            if not items.exists():
                messages.error(request, 'Your cart is empty!')
                return redirect('checkout')
            
            # Calculate totals
            total = sum(item.product.price * item.quantity for item in items)
            tax = total * 0.1  # 10% tax
            grand_total = total + tax
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                address=request.POST.get('address', ''),
                city=request.POST.get('city', ''),
                country=request.POST.get('country', ''),
                zip=request.POST.get('zip', ''),
                payment_method=request.POST.get('payment_method', 'PayPal'),
                total=total,
                tax=tax,
                grand_total=grand_total,
                transaction_id=str(uuid.uuid4())[:16]  # Generate transaction ID
            )
            
            # Create order items
            for cart_item in items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price * cart_item.quantity
                )
            
            # Clear the cart
            items.delete()
            
            messages.success(request, 'Order placed successfully!')
            return redirect('order_complete', order_id=order.id)
            
        except Cart.DoesNotExist:
            messages.error(request, 'Your cart is empty!')
            return redirect('checkout')
    
    else:
        # GET request - show the place order confirmation page
        try:
            cart = Cart.objects.get(user=request.user)
            items = CartItem.objects.filter(cart=cart)
            
            if not items.exists():
                messages.error(request, 'Your cart is empty!')
                return redirect('checkout')
            
            # For GET request, create a temporary order object for display
            total = sum(item.product.price * item.quantity for item in items)
            tax = total * 0.1
            grand_total = total + tax
            
            # Create a temporary order object (not saved to database)
            temp_order = Order(
                user=request.user,
                total=total,
                tax=tax,
                grand_total=grand_total,
                payment_method='PayPal'  # Default
            )
            
            context = {
                'order': temp_order,
                'items': items,
            }
            return render(request, 'orders/place_order.html', context)
            
        except Cart.DoesNotExist:
            messages.error(request, 'Your cart is empty!')
            return redirect('checkout')

def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})

def order_complete(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_complete.html', {'order': order})