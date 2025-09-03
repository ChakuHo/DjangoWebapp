from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Order, OrderItem, Payment
from cart.models import Cart, CartItem
from django.middleware.csrf import get_token
from .payment_utils import ESewaPayment
import uuid, json, base64, hmac, hashlib, time, datetime
from django.db.models import F
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
import logging
from django.utils import timezone
from django.db.models import Q, F

logger = logging.getLogger(__name__)

#  helper functions
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
    print(f"🔄 Payment Method: {order.payment_method}")
    print(f"🔄 Payment Status: {order.payment_status}")
    
    try:
        order_items = order.items.all().prefetch_related('variations')
        
        # Determine email content based on payment method and status
        if order.payment_method == 'Cash on Delivery':
            payment_status_text = " Cash on Delivery"
            payment_note = "Payment will be collected when your order is delivered."
            subject = f'Order Confirmation #{order.id} - Cash on Delivery'
            order_status = "Confirmed"
            
        elif order.payment_method == 'QR Payment' and order.payment_status == 'pending_verification':
            payment_status_text = "🔍 QR Payment Under Verification"
            payment_note = f"Your payment is being verified. Transaction ID: {getattr(order, 'qr_payment_transaction_id', 'N/A')}. You'll receive confirmation within 24 hours."
            subject = f'Order Received #{order.id} - Payment Under Verification'
            order_status = "Payment Under Verification"
            
        elif order.payment_method == 'QR Payment' and order.payment_status == 'completed':
            payment_status_text = " QR Payment Verified & Completed"
            payment_note = f"Your QR payment has been verified and confirmed. Transaction ID: {getattr(order, 'qr_payment_transaction_id', 'N/A')}"
            subject = f'Order Confirmed #{order.id} - QR Payment Verified!'
            order_status = "Confirmed"
            
        else:
            payment_status_text = " Payment Completed"
            payment_note = "Your payment has been successfully processed."
            subject = f'Order Confirmation #{order.id} - Payment Successful!'
            order_status = "Confirmed"
        
        # Create email message
        message = f"""
Dear {order.user.first_name or order.user.username},

 Thank you for your order!

 ORDER DETAILS:
═══════════════════════════════════════
Order ID: #{order.id}
Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Payment Method: {order.payment_method}
Payment Status: {payment_status_text}
Order Status: {order_status}

 Note: {payment_note}
"""

        # Add QR payment specific details
        if order.payment_method == 'QR Payment':
            message += f"""
 QR PAYMENT DETAILS:
═══════════════════════════════════════
Payment Reference: {getattr(order, 'payment_reference', 'N/A')}
Transaction ID: {getattr(order, 'qr_payment_transaction_id', 'Not provided')}
"""
            if order.payment_status == 'pending_verification':
                message += """
 VERIFICATION PROCESS:
═══════════════════════════════════════
• Your payment details are being verified
• This usually takes 2-24 hours
• You'll receive another email once verified
• Contact support if you have questions
"""
            elif order.payment_status == 'completed':
                message += """
 VERIFICATION COMPLETED:
═══════════════════════════════════════
• Your payment has been successfully verified
• Your order is now confirmed and being processed
• You'll receive shipping updates soon
"""

        message += """
 ITEMS ORDERED:
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
 PAYMENT SUMMARY:
═══════════════════════════════════════
Subtotal: Rs. {order.total:.2f}
Tax (13%): Rs. {order.tax:.2f}
Total Amount: Rs. {order.grand_total:.2f}

 DELIVERY ADDRESS:
═══════════════════════════════════════
{order.address}
{order.city}, {order.country}
{getattr(order, 'zip', '') or ''}
"""

        # Add different next steps based on payment status
        if order.payment_method == 'QR Payment' and order.payment_status == 'pending_verification':
            message += f"""
 WHAT'S NEXT?
═══════════════════════════════════════
✓ We're verifying your payment details
✓ You'll receive confirmation within 24 hours
✓ Check your email for verification updates
✓ Contact support if you need assistance

 NEED HELP?
═══════════════════════════════════════
If you have questions about your payment verification,
please contact our support team with your:
• Order ID: #{order.id}
• Transaction ID: {getattr(order, 'qr_payment_transaction_id', 'N/A')}
• Payment Reference: {getattr(order, 'payment_reference', 'N/A')}
"""
        else:
            message += """
 WHAT'S NEXT?
═══════════════════════════════════════
✓ Your order is confirmed and being processed
✓ You'll receive shipping updates via email
✓ Estimated delivery: 3-5 business days
✓ Track your order anytime from your account
"""

        message += """
Thank you for choosing our marketplace!

Best regards,
Islington Marketplace Team
        """
        
        print("🔄 SENDING EMAIL NOW...")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        
        print(f" Order confirmation email sent to {order.user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_order_rejection_email(order):
    """Send email when QR payment is rejected"""
    print("🔄 REJECTION EMAIL FUNCTION CALLED!")
    print(f"🔄 Order ID: {order.id}")
    print(f"🔄 User Email: {order.user.email}")
    
    try:
        subject = f'Payment Rejected - Order #{order.order_number}'
        
        message = f"""
Dear {order.user.first_name or order.user.username},

❌ Unfortunately, we were unable to verify your QR payment for the following order:

 ORDER DETAILS:
═══════════════════════════════════════
Order ID: #{order.id}
Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Payment Method: QR Payment
Payment Reference: {getattr(order, 'payment_reference', 'N/A')}
Transaction ID: {getattr(order, 'qr_payment_transaction_id', 'Not provided')}
Amount: Rs. {order.grand_total:.2f}

 REJECTION REASON:
═══════════════════════════════════════
Your QR payment could not be verified by the seller. This could be due to:
• Transaction ID not found in seller's payment history
• Payment amount mismatch
• Invalid or unclear payment screenshot
• Payment not received by seller

 WHAT YOU CAN DO:
═══════════════════════════════════════
1. Double-check your payment was successful in your digital wallet
2. Contact the seller directly to resolve the issue
3. Place a new order if the payment issue cannot be resolved
4. Contact our support team for assistance

 NEED HELP?
═══════════════════════════════════════
If you believe this rejection is an error, please contact:
• Seller: Contact them through our messaging system
• Support: {settings.DEFAULT_FROM_EMAIL}
• Include: Order #{order.id} and Transaction ID: {getattr(order, 'qr_payment_transaction_id', 'N/A')}

We apologize for any inconvenience caused.

Best regards,
Islington Marketplace Team
        """
        
        print("🔄 SENDING REJECTION EMAIL NOW...")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        
        print(f" Order rejection email sent to {order.user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Rejection email sending failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def revert_stock_after_rejection(order):
    """Revert stock back when order is rejected"""
    print(f"🔄 REVERTING STOCK for Order #{order.id}")
    
    try:
        order_items = order.items.all()
        
        for item in order_items:
            product = item.product
            quantity = item.quantity
            
            # Add stock back to main product
            product.stock += quantity
            product.save()
            print(f" Reverted {quantity} stock to {product.name} (New stock: {product.stock})")
            
            # Add stock back to variations if any
            for variation in item.variations.all():
                variation.stock_quantity += quantity
                variation.save()
                print(f" Reverted {quantity} stock to variation {variation.variation_option.value}")
        
        print(f" Stock reverted successfully for Order #{order.id}")
        return True
        
    except Exception as e:
        print(f"❌ Stock reversion failed for Order #{order.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
def send_order_shipped_email(order):
    """Send email when order is shipped"""
    print(" SHIPPING EMAIL FUNCTION CALLED!")
    print(f" Order ID: {order.id}")
    print(f" User Email: {order.user.email}")
    
    try:
        order_items = order.items.all().prefetch_related('variations')
        
        subject = f'Your Order #{order.order_number} Has Been Shipped! '
        
        # Get shipping details if available
        tracking_number = getattr(order, 'tracking_number', 'Not provided')
        shipping_date = getattr(order, 'shipping_date', order.updated_at)
        shipping_notes = getattr(order, 'shipping_notes', '')
        
        message = f"""
Dear {order.user.first_name or order.user.username},

 Great news! Your order has been shipped!

 ORDER DETAILS:
═══════════════════════════════════════
Order ID: #{order.id}
Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Payment Method: {order.payment_method}
Order Status:  Shipped

SHIPPING INFORMATION:
═══════════════════════════════════════
Shipping Date: {shipping_date.strftime('%B %d, %Y at %I:%M %p') if shipping_date else 'Today'}
Tracking Number: {tracking_number}
Estimated Delivery: 3-5 business days
"""

        if shipping_notes:
            message += f"Shipping Notes: {shipping_notes}\n"

        message += """
 ITEMS SHIPPED:
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
 ORDER TOTAL: Rs. {order.grand_total:.2f}

 DELIVERY ADDRESS:
═══════════════════════════════════════
{order.address}
{order.city}, {order.country}
{getattr(order, 'zip', '') or ''}

 TRACK YOUR ORDER:
═══════════════════════════════════════"""

        if tracking_number and tracking_number != 'Not provided':
            message += f"""
Your tracking number: {tracking_number}
You can track your package using this number with the shipping company.
"""
        else:
            message += """
Tracking number will be provided by the seller soon.
You can check your order status anytime from your account.
"""

        message += f"""
 WHAT'S NEXT?
═══════════════════════════════════════
✓ Your package is on its way!
✓ Expected delivery in 3-5 business days
✓ You'll receive a delivery confirmation email
✓ Contact seller if you have any questions

 NEED HELP?
═══════════════════════════════════════
If you have questions about your shipment:
• Order ID: #{order.id}
• Tracking: {tracking_number}
• Contact our support team

Thank you for shopping with us!

Best regards,
Islington Marketplace Team
        """
        
        print(" SENDING SHIPPING EMAIL NOW...")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        
        print(f" Order shipped email sent to {order.user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Shipping email sending failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_order_delivered_email(order):
    """Send email when order is delivered"""
    print(" DELIVERY EMAIL FUNCTION CALLED!")
    print(f" Order ID: {order.id}")
    print(f" User Email: {order.user.email}")
    
    try:
        order_items = order.items.all().prefetch_related('variations')
        
        subject = f'Order #{order.order_number} Delivered Successfully! '
        
        # Get delivery details if available
        delivery_date = getattr(order, 'delivery_date', order.updated_at)
        delivery_notes = getattr(order, 'delivery_notes', '')
        tracking_number = getattr(order, 'tracking_number', 'N/A')
        
        message = f"""
Dear {order.user.first_name or order.user.username},

 Congratulations! Your order has been successfully delivered!

 ORDER DETAILS:
═══════════════════════════════════════
Order ID: #{order.id}
Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Payment Method: {order.payment_method}
Order Status:  Delivered

 DELIVERY INFORMATION:
═══════════════════════════════════════
Delivery Date: {delivery_date.strftime('%B %d, %Y at %I:%M %p') if delivery_date else 'Today'}
Tracking Number: {tracking_number}
"""

        if delivery_notes:
            message += f"Delivery Notes: {delivery_notes}\n"

        message += """
 DELIVERED ITEMS:
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
 ORDER TOTAL: Rs. {order.grand_total:.2f}

 DELIVERED TO:
═══════════════════════════════════════
{order.address}
{order.city}, {order.country}
{getattr(order, 'zip', '') or ''}

 HOW WAS YOUR EXPERIENCE?
═══════════════════════════════════════
We hope you love your purchase! If you're satisfied with your order:
• Consider leaving a review for the products
• Rate your shopping experience
• Share with friends and family

 ISSUES WITH YOUR ORDER?
═══════════════════════════════════════
If there are any issues with your delivered items:
• Contact the seller through our messaging system
• Report problems within 7 days of delivery
• Our support team is here to help

 NEED SUPPORT?
═══════════════════════════════════════
Order ID: #{order.id}
Delivery Date: {delivery_date.strftime('%B %d, %Y') if delivery_date else 'Today'}
Support Email: {settings.DEFAULT_FROM_EMAIL}

Thank you for choosing Islington Marketplace!
We appreciate your business and hope to serve you again soon.

Best regards,
Islington Marketplace Team
        """
        
        print(" SENDING DELIVERY EMAIL NOW...")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        
        print(f" Order delivered email sent to {order.user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Delivery email sending failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def checkout(request):
    """checkout with guest handling """
    if not request.user.is_authenticated:
        # Preserve cart before redirecting to login
        try:
            from cart.views import _cart_id
            cart_id = _cart_id(request)
            session_cart = Cart.objects.get(cart_id=cart_id)
            session_items = CartItem.objects.filter(cart=session_cart, is_active=True)
            
            if session_items.exists():
                # Store cart data in session for preservation
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
                
                messages.info(request, 'Please login or register to continue with checkout. Your cart will be preserved!')
            else:
                messages.warning(request, 'Your cart is empty!')
                return redirect('cart')
        except Cart.DoesNotExist:
            messages.warning(request, 'Your cart is empty!')
            return redirect('cart')
        
        return redirect('login')
    
    # User is authenticated - proceed with existing checkout logic
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
            
            # Generate order number
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
                order.payment_status = 'cod_pending'
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
                return redirect('esewa_start', order_id=order.id)
                
            elif payment_method == 'QR Payment':
                print("🚀 PROCESSING QR PAYMENT...")
                
                # Generate QR Payment Reference ID
                qr_reference = f"QR{order_number}{str(uuid.uuid4().hex[:6]).upper()}"
                order.payment_reference = qr_reference
                order.payment_status = 'pending_qr_confirmation'
                order.save()
                
                print(f"🚀 QR REFERENCE GENERATED: {qr_reference}")
                
                # Get all sellers from cart items and their QR codes
                sellers_data = []
                seller_totals = {}
                
                # Calculate amount per seller
                for item in items:
                    seller = item.product.seller
                    seller_profile = seller.profile
                    
                    # Check if seller has QR code
                    if not seller_profile.has_payment_qr():
                        messages.error(request, f'Seller "{seller_profile.business_name or seller.username}" has not set up QR payment. Please contact support.')
                        return redirect('checkout')
                    
                    # Calculate amount for this seller
                    item_total = item.sub_total()
                    
                    if seller.id in seller_totals:
                        seller_totals[seller.id] += item_total
                    else:
                        seller_totals[seller.id] = item_total
                        sellers_data.append({
                            'seller_id': seller.id,
                            'seller': seller,
                            'business_name': seller_profile.business_name or seller.username,
                            'qr_code': seller_profile.payment_qr_code,
                            'qr_payment_method': seller_profile.qr_payment_method,
                            'qr_payment_info': seller_profile.qr_payment_info,
                            'get_qr_display_name': seller_profile.get_qr_display_name(),
                            'amount': 0  # Will be updated below
                        })
                
                # Update amounts in sellers_data
                for seller_data in sellers_data:
                    seller_data['amount'] = seller_totals[seller_data['seller_id']]
                
                context = {
                    'order': order,
                    'seller_qr_codes': sellers_data,
                    'total_amount': grand_total,
                    'qr_reference': qr_reference,
                    'tax_amount': tax,
                    'subtotal': total
                }
                
                return render(request, 'orders/qr_payment.html', context)
            
            else:
                # Invalid payment method
                messages.error(request, 'Invalid payment method selected.')
                return redirect('checkout')
            
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

#  ESEWA FUNCTIONS
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
    """FIXED eSewa return function - NO ANALYTICS HERE (prevents double counting)"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    encoded = request.GET.get("data") or request.POST.get("data") \
           or request.GET.get("response") or request.POST.get("response")

    payload, status, txn_code = {}, "", ""
    if encoded:
        try:
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
            status = str(payload.get("status", "")).upper()
            txn_code = payload.get("transaction_code", "")
            print(f" eSewa Response Decoded: {payload}")
        except Exception as e:
            print(f"❌ Error decoding eSewa response: {e}")
            pass

    print(f" eSewa Response: Status={status}, TxnCode={txn_code}")

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
        
        print(f" Payment created: {payment.payment_id}, Created: {created}")

        # Get cart items correctly using cart relationship
        if not order.items.filter(ordered=True).exists():
            try:
                cart = Cart.objects.get(user=order.user)
                cart_items = CartItem.objects.filter(cart=cart).select_related("product")
                
                print(f" Found {cart_items.count()} cart items to process")
                
                for item in cart_items:
                    # Find corresponding order item
                    order_item = order.items.filter(product=item.product).first()
                    if order_item:
                        order_item.payment = payment
                        order_item.ordered = True
                        order_item.save()
                        print(f" Updated order item: {order_item.product.name}")
                    
                    # Decrease stock using F() to avoid race conditions
                    Product = item.product.__class__
                    Product.objects.filter(pk=item.product_id).update(stock=F("stock") - item.quantity)
                    print(f" Decreased stock for: {item.product.name}")
                
                # Clear cart
                cart_items.delete()
                print(" Cart cleared")
                
            except Cart.DoesNotExist:
                print("❌ No cart found for user")
                pass

        # Send email
        email_sent = send_order_confirmation_email(order)
        print(f" Email sent: {email_sent}")
        
        # Mark order completed
        order.payment = payment
        order.is_ordered = True
        order.payment_status = 'completed'
        order.status = "Confirmed"
        order.payment_reference = txn_code
        order.payment_gateway_response = json.dumps(payload)
        order.save()
        
        print(f" Order completed: {order.id}")
        
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
def confirm_qr_payment(request, order_id):
    """Confirm QR payment completion with transaction ID verification"""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id, user=request.user)
        qr_reference = request.POST.get('qr_reference', '')
        transaction_id = request.POST.get('transaction_id', '').strip()
        payment_screenshot = request.FILES.get('payment_screenshot')
        
        try:
            # Verify the reference matches
            if getattr(order, 'payment_reference', '') != qr_reference:
                messages.error(request, 'Invalid payment reference. Please try again.')
                return redirect('checkout')
            
            # Validate transaction ID
            if not transaction_id or len(transaction_id) < 5:
                messages.error(request, 'Please provide a valid transaction ID (minimum 5 characters).')
                # Re-render QR payment page with error
                context = {
                    'order': order,
                    'qr_reference': qr_reference,
                    'seller_qr_codes': [],  
                    'total_amount': order.grand_total,
                    'error': 'Transaction ID is required'
                }
                return render(request, 'orders/qr_payment.html', context)
            
            # Get cart items for stock deduction
            cart = Cart.objects.get(user=request.user)
            items = CartItem.objects.filter(cart=cart)
            
            # Create a QR payment record with transaction details
            payment = Payment.objects.create(
                user=order.user,
                payment_id=f"{qr_reference}-{transaction_id}",
                payment_method="QR Payment",
                amount_paid=str(order.grand_total),
                status="PENDING_VERIFICATION",
            )
            
            # Update order items
            for order_item in order.items.all():
                order_item.payment = payment
                order_item.ordered = True
                order_item.save()
            
            # Complete the order but mark as pending verification
            order.payment = payment
            order.payment_status = 'pending_verification'
            order.status = 'Payment Under Verification'
            order.is_ordered = True
            order.qr_payment_confirmed_at = timezone.now()
            order.qr_payment_transaction_id = transaction_id
            order.qr_payment_notes = f"QR Payment submitted with Transaction ID: {transaction_id}"
            
            # Handle screenshot if uploaded
            if payment_screenshot:
                order.qr_payment_screenshot = payment_screenshot
                order.qr_payment_notes += f" | Screenshot uploaded: {payment_screenshot.name}"
            
            order.save()
            
            print(f"🚀 QR PAYMENT SUBMITTED - Order: {order.id}, TxnID: {transaction_id}")
            
            # Deduct stock and clear cart
            deduct_stock_after_checkout(items)
            items.delete()
            
            # Clear session
            if 'pending_order_id' in request.session:
                del request.session['pending_order_id']
            
            # Send confirmation email
            send_order_confirmation_email(order)
            
            messages.success(request, 
                f'Payment proof submitted successfully! '
                f'Transaction ID: {transaction_id}. '
                f'Your order will be verified and confirmed within 24 hours.')
            return redirect('order_complete', order_id=order.id)
            
        except Cart.DoesNotExist:
            messages.error(request, 'Cart not found. Please try again.')
            return redirect('checkout')
        except Exception as e:
            print(f"❌ QR Payment Confirmation Error: {str(e)}")
            messages.error(request, 'Error confirming payment. Please contact support with your transaction details.')
            return redirect('checkout')
    
    return redirect('checkout')

@login_required
def my_orders(request):
    """Show orders with filtering options"""
    
    # Get filter parameter
    filter_type = request.GET.get('filter', 'active')
    
    if filter_type == 'delivered':
        # Delivered orders
        orders = Order.objects.filter(
            user=request.user,
            status__in=['Delivered', 'delivered', 'Completed', 'completed']
        ).order_by('-created_at')
        
    elif filter_type == 'cancelled':
        # Cancelled/Rejected orders
        orders = Order.objects.filter(
            user=request.user
        ).filter(
            Q(status__in=['cancelled', 'Cancelled']) | 
            Q(payment_status='rejected')
        ).order_by('-created_at')
        
    elif filter_type == 'all':
        # All orders except initial pending
        orders = Order.objects.filter(
            user=request.user
        ).exclude(
            payment_status='pending'  # Exclude incomplete checkouts
        ).order_by('-created_at')
        
    else:  # 'active' (default)
        # Active orders (not delivered, not cancelled)
        orders = Order.objects.filter(
            user=request.user,
            payment_status__in=['completed', 'pending_verification', 'cod_pending']
        ).exclude(
            status__in=['Delivered', 'delivered', 'Completed', 'completed', 'cancelled', 'Cancelled']
        ).order_by('-created_at')
    
    # Count different order types for tabs
    order_counts = {
        'active': Order.objects.filter(
            user=request.user,
            payment_status__in=['completed', 'pending_verification', 'cod_pending']
        ).exclude(
            status__in=['Delivered', 'delivered', 'Completed', 'completed', 'cancelled', 'Cancelled']
        ).count(),
        
        'delivered': Order.objects.filter(
            user=request.user,
            status__in=['Delivered', 'delivered', 'Completed', 'completed']
        ).count(),
        
        'cancelled': Order.objects.filter(
            user=request.user
        ).filter(
            Q(status__in=['cancelled', 'Cancelled']) | 
            Q(payment_status='rejected')
        ).count(),
        
        'all': Order.objects.filter(
            user=request.user
        ).exclude(payment_status='pending').count()
    }
    
    context = {
        'orders': orders,
        'filter_type': filter_type,
        'order_counts': order_counts,
    }
    return render(request, 'orders/my_orders.html', context)

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

# When an order is completed, update product analytics
def complete_order(order):
    """Update product analytics when order is completed"""
    for item in order.items.all():
        # Refresh analytics for each product
        item.product.get_analytics_data()


# Fallback functions for old URLs
def esewa_success(request):
    messages.info(request, 'Please complete your order through the checkout process.')
    return redirect('checkout')

def esewa_failure(request):
    messages.error(request, 'Payment was cancelled or failed. Please try again.')
    return redirect('checkout')