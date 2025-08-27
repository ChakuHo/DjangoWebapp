from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Order, OrderItem, Payment
from cart.models import Cart, CartItem
from cart.views import deduct_stock_after_checkout
from django.middleware.csrf import get_token
from .payment_utils import ESewaPayment, KhaltiPayment
import uuid, json, base64, hmac, hashlib, time, datetime
from django.db.models import F
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Teacher's helper functions
def _abs(request, name, *args, **kwargs):
    return request.build_absolute_uri(reverse(name, args=args, kwargs=kwargs))

def _order_amount(order):
    if hasattr(order, "grand_total") and order.grand_total:
        return int(round(float(order.grand_total)))
    return int(sum(item.price for item in order.items.all()))

def _make_signature(total_amount: int, transaction_uuid: str) -> str:
    msg = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={settings.ESEWA_PRODUCT_CODE}"
    mac = hmac.new(
        settings.ESEWA_SECRET_KEY.encode("utf-8"),
        msg=msg.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(mac).decode("utf-8")

def send_order_confirmation_email(order):
    """Send order confirmation email after successful payment"""
    print("🔄 EMAIL FUNCTION CALLED!")
    print(f"🔄 Order ID: {order.id}")
    print(f"🔄 User Email: {order.user.email}")
    
    try:
        order_items = order.items.all().prefetch_related('variations')
        
        if order.payment_method == 'Cash on Delivery':
            payment_status_text = "💰 Cash on Delivery"
            payment_note = "Payment will be collected when your order is delivered."
            subject = f'Order Confirmation #{order.id} - Cash on Delivery'
        else:
            payment_status_text = "✅ Payment Completed"
            payment_note = "Your payment has been successfully processed."
            subject = f'Order Confirmation #{order.id} - Payment Successful!'
        
        message = f"""
Dear {order.user.first_name or order.user.username},

🎉 Thank you for your order! Your order has been confirmed.

📋 ORDER DETAILS:
═══════════════════════════════════════
Order ID: #{order.id}
Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Payment Method: {order.payment_method}
Payment Status: {payment_status_text}
Order Status: {order.status}

📝 Note: {payment_note}

📦 ITEMS ORDERED:
═══════════════════════════════════════"""

        for item in order_items:
            variations_text = ""
            if item.variations.exists():
                variations_list = [f"{v.variation_type.display_name}: {v.variation_option.display_value}" 
                                 for v in item.variations.all()]
                variations_text = f" ({', '.join(variations_list)})"
            
            message += f"\n• {item.product.name}{variations_text}"
            message += f"\n  Quantity: {item.quantity} × Rs. {item.price/item.quantity:.2f} = Rs. {item.price:.2f}\n"

        message += f"""
💰 PAYMENT SUMMARY:
═══════════════════════════════════════
Subtotal: Rs. {order.total:.2f}
Tax (13%): Rs. {order.tax:.2f}
Total Amount: Rs. {order.grand_total:.2f}

📍 DELIVERY ADDRESS:
═══════════════════════════════════════
{order.address}
{order.city}, {order.country}
{order.zip if order.zip else ''}

🚚 WHAT'S NEXT?
═══════════════════════════════════════
✓ Your order is confirmed and being processed
✓ You'll receive shipping updates via email
✓ Estimated delivery: 3-5 business days

Thank you for choosing our marketplace!

Best regards,
Your Marketplace Team
        """
        
        print("🔄 SENDING EMAIL NOW...")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        
        print(f"✅ Order confirmation email sent to {order.user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        items = CartItem.objects.filter(cart=cart).prefetch_related('variations')
        
        if not items.exists():
            messages.error(request, 'Your cart is empty!')
            return redirect('cart')
        
        total = sum(item.sub_total() for item in items)
        tax = total * 0.13
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
        return redirect('cart')

def deduct_stock_after_checkout(cart_items):
    """Deduct stock from products after successful checkout"""
    for item in cart_items:
        product = item.product
        quantity = item.quantity
        
        if product.stock >= quantity:
            product.stock -= quantity
            product.save()
        
        for variation in item.variations.all():
            if variation.stock_quantity >= quantity:
                variation.stock_quantity -= quantity
                variation.save()

@login_required
def place_order(request):
    print("🚀 PLACE ORDER FUNCTION CALLED!")
    
    if request.method == 'POST':
        print("🚀 METHOD IS POST!")
        
        try:
            cart = Cart.objects.get(user=request.user)
            items = CartItem.objects.filter(cart=cart).prefetch_related('variations')
            
            if not items.exists():
                messages.error(request, 'Your cart is empty!')
                return redirect('checkout')
            
            total = sum(item.sub_total() for item in items)
            tax = total * 0.13
            grand_total = total + tax
            
            payment_method = request.POST.get('payment_method', 'eSewa')
            print(f"🚀 PAYMENT METHOD: {payment_method}")
            
            order = Order.objects.create(
                user=request.user,
                address=request.POST.get('address', ''),
                city=request.POST.get('city', ''),
                country=request.POST.get('country', ''),
                zip=request.POST.get('zip', ''),
                payment_method=payment_method,
                total=total,
                tax=tax,
                grand_total=grand_total,
                transaction_id=str(uuid.uuid4())[:16],
                payment_status='pending'
            )
            
            # Generate order number like teacher's
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date + str(order.id)
            order.order_number = order_number
            order.save()
            
            print(f"🚀 ORDER CREATED - ID: {order.id}, Number: {order_number}")
            
            # Create order items
            for cart_item in items:
                order_item = OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.get_final_price_per_unit() * cart_item.quantity,
                    seller=cart_item.product.seller 
                )
                if cart_item.variations.exists():
                    order_item.variations.set(cart_item.variations.all())
                    order_item.save()
            
            # Store order ID in session
            request.session['pending_order_id'] = order.id
            
            if payment_method == 'Cash on Delivery':
                print("🚀 PROCESSING COD...")
                
                # Complete COD order immediately
                deduct_stock_after_checkout(items)
                items.delete()
                order.payment_status = 'completed'
                order.status = 'Confirmed'
                order.is_ordered = True
                order.save()
                
                print(f"🔄 COD ORDER COMPLETED - ID: {order.id}")
                
                email_sent = send_order_confirmation_email(order)
                
                if email_sent:
                    messages.success(request, 'Order placed successfully! Confirmation email sent.')
                else:
                    messages.success(request, 'Order placed successfully! (Email notification failed)')
                
                return redirect('order_complete', order_id=order.id)
                
            elif payment_method == 'eSewa':
                print("🚀 PROCESSING ESEWA...")
                # Use teacher's approach - redirect to esewa_start
                return redirect('esewa_start', order_id=order.id)
                
            elif payment_method == 'Khalti':
                print("🚀 PROCESSING KHALTI...")
                
                khalti_config = KhaltiPayment.initiate_payment(order)
                
                if khalti_config is None:
                    messages.error(request, 'Khalti payment initialization failed. Please try again.')
                    return redirect('checkout')
                
                order.payment_status = 'initiated'
                order.save()
                
                context = {
                    'order': order,
                    'payment_method': 'Khalti',
                    'khalti_config': khalti_config['config'],
                    'amount': khalti_config['amount'],
                    'csrf_token': get_token(request)
                }
                return render(request, 'orders/payment_gateway.html', context)
            
        except Cart.DoesNotExist:
            print("❌ CART DOES NOT EXIST")
            messages.error(request, 'Your cart is empty!')
            return redirect('checkout')
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            logger.error(f"Place order error: {str(e)}")
            messages.error(request, f'Error processing order: {str(e)}')
            return redirect('checkout')
    
    print("🚀 NOT POST REQUEST - REDIRECTING")
    return redirect('checkout')

# TEACHER'S ESEWA FUNCTIONS - FIXED
@login_required
def esewa_start(request, order_id):
    """Teacher's eSewa start function"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    total_amount = int(round(float(order.grand_total or 0)))
    tax = int(round(float(order.tax or 0)))
    amount = total_amount - tax
    
    if amount < 0:
        amount = total_amount

    txn_uuid = f"{order.order_number or order.id}-{uuid.uuid4().hex[:8]}"

    form = {
        "amount": int(amount),
        "tax_amount": int(tax),
        "total_amount": int(total_amount),
        "transaction_uuid": txn_uuid,
        "product_code": settings.ESEWA_PRODUCT_CODE,
        "product_service_charge": 0,
        "product_delivery_charge": 0,
        "success_url": _abs(request, "esewa_return", order_id=order.id),
        "failure_url": _abs(request, "esewa_return", order_id=order.id),
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": _make_signature(total_amount, txn_uuid),
    }
    
    print(f"🔗 eSewa Form Data: {form}")
    
    context = {
        "ESEWA_FORM_URL": settings.ESEWA_FORM_URL,
        "form": form,
        "order": order,
    }
    return render(request, "orders/esewa_redirect.html", context)

@login_required
def esewa_return(request, order_id):
    """Teacher's eSewa return function - FIXED"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    encoded = request.GET.get("data") or request.POST.get("data") \
           or request.GET.get("response") or request.POST.get("response")

    payload, status, txn_code = {}, "", ""
    if encoded:
        try:
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
            status = str(payload.get("status", "")).upper()
            txn_code = payload.get("transaction_code", "")
            print(f"✅ eSewa Response Decoded: {payload}")
        except Exception as e:
            print(f"❌ Error decoding eSewa response: {e}")
            pass

    print(f"✅ eSewa Response: Status={status}, TxnCode={txn_code}")

    if status == "COMPLETE":
        # Create Payment
        amount_paid = _order_amount(order)
        payment, created = Payment.objects.get_or_create(
            user=order.user,
            payment_id=txn_code or f"esewa-{order.id}",
            defaults={
                "payment_method": "eSewa",
                "amount_paid": str(amount_paid),
                "status": "COMPLETED",
            },
        )
        
        print(f"✅ Payment created: {payment.payment_id}, Created: {created}")

        # FIXED: Get cart items correctly using cart relationship
        if not order.items.filter(ordered=True).exists():
            try:
                cart = Cart.objects.get(user=order.user)
                cart_items = CartItem.objects.filter(cart=cart).select_related("product")
                
                print(f"✅ Found {cart_items.count()} cart items to process")
                
                for item in cart_items:
                    # Find corresponding order item
                    order_item = order.items.filter(product=item.product).first()
                    if order_item:
                        order_item.payment = payment
                        order_item.ordered = True
                        order_item.save()
                        print(f"✅ Updated order item: {order_item.product.name}")
                    
                    # Decrease stock using F() to avoid race conditions
                    Product = item.product.__class__
                    Product.objects.filter(pk=item.product_id).update(stock=F("stock") - item.quantity)
                    print(f"✅ Decreased stock for: {item.product.name}")
                
                # Clear cart
                cart_items.delete()
                print("✅ Cart cleared")
                
            except Cart.DoesNotExist:
                print("❌ No cart found for user")
                pass

        # Send email
        email_sent = send_order_confirmation_email(order)
        print(f"✅ Email sent: {email_sent}")
        
        # Mark order completed
        order.payment = payment
        order.is_ordered = True
        order.payment_status = 'completed'
        order.status = "Confirmed"
        order.payment_reference = txn_code
        order.payment_gateway_response = json.dumps(payload)
        order.save()
        
        print(f"✅ Order completed: {order.id}")
        
        # Clear session
        if 'pending_order_id' in request.session:
            del request.session['pending_order_id']
        
        messages.success(request, 'eSewa payment successful! Order confirmed.')
        return redirect('order_complete', order_id=order.id)
    
    # Failure
    print(f"❌ eSewa payment failed: Status={status}")
    messages.error(request, "eSewa payment was not completed.")
    return redirect('checkout')

@login_required
def khalti_verify(request):
    print("💜 Khalti Verify Called")
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        data = json.loads(request.body)
        token = data.get('token')
        amount = data.get('amount')
        
        print(f"💜 Khalti Token: {token}")
        print(f"💜 Khalti Amount: {amount}")
        
        if not token or not amount:
            return JsonResponse({'success': False, 'error': 'Invalid data - missing token or amount'})
        
        verification_result = KhaltiPayment.verify_payment(token, amount)
        
        if verification_result['success']:
            order_id = request.session.get('pending_order_id')
            if not order_id:
                return JsonResponse({'success': False, 'error': 'No pending order found'})
            
            order = Order.objects.get(id=order_id, user=request.user)
            
            # Create Payment like teacher's
            payment = Payment.objects.create(
                user=order.user,
                payment_id=verification_result['data'].get('idx', f"khalti-{order.id}"),
                payment_method="Khalti",
                amount_paid=str(order.grand_total),
                status="COMPLETED",
            )
            
            print(f"💜 Khalti payment created: {payment.payment_id}")
            
            # Update order items
            for order_item in order.items.all():
                order_item.payment = payment
                order_item.ordered = True
                order_item.save()
            
            order.payment = payment
            order.payment_status = 'completed'
            order.status = 'Confirmed'
            order.is_ordered = True
            order.payment_reference = verification_result['data'].get('idx')
            order.payment_gateway_response = json.dumps(verification_result['data'])
            order.save()

            # FIXED: Complete the order using correct cart relationship
            try:
                cart = Cart.objects.get(user=request.user)
                items = CartItem.objects.filter(cart=cart)
                deduct_stock_after_checkout(items)
                items.delete()
                print("💜 Khalti: Cart cleared and stock deducted")
            except Cart.DoesNotExist:
                print("💜 Khalti: No cart found")
                pass
                
            if 'pending_order_id' in request.session:
                del request.session['pending_order_id']

            send_order_confirmation_email(order)
            
            return JsonResponse({
                'success': True, 
                'redirect_url': f'/orders/order-complete/{order.id}/'
            })
        else:
            error_msg = verification_result.get('error', 'Unknown error')
            print(f"❌ Khalti Verification Failed: {error_msg}")
            return JsonResponse({
                'success': False, 
                'error': error_msg
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        print(f"❌ Khalti Verify Error: {str(e)}")
        logger.error(f"Khalti verification error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})

@login_required
def order_complete(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order).prefetch_related('variations')
    
    context = {
        'order': order, 
        'order_items': order_items,
        'payment': order.payment,
    }
    return render(request, 'orders/order_complete.html', context)

# Fallback functions for old URLs
def esewa_success(request):
    messages.info(request, 'Please complete your order through the checkout process.')
    return redirect('checkout')

def esewa_failure(request):
    messages.error(request, 'Payment was cancelled or failed. Please try again.')
    return redirect('checkout')