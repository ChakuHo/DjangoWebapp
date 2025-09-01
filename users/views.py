from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile, Notification
from orders.models import Order
from django.utils import timezone
from products.models import Product, Category, CategoryVariation, VariationType, VariationOption, ProductVariation
import json
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Q
from datetime import datetime, timedelta
from orders.models import OrderItem
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import ChatRoom, ChatMessage
from orders.views import send_order_confirmation_email
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import TypingIndicator
from .notification_utils import get_recent_notifications, get_unread_notification_count, create_notification
from .models import Wishlist
from products.models import Product
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.core.files.storage import default_storage
import os



def send_registration_confirmation_email(user):
    """Send welcome/registration confirmation email to new users"""
    print(f"🔄 REGISTRATION EMAIL FUNCTION CALLED for {user.email}")
    
    try:
        subject = '🎉 Welcome to ISLINGTON MARKETPLACE!'
        
        message = f"""
Dear {user.first_name or user.username},

🎉 Welcome to ISLINGTON MARKETPLACE! 

Your account has been successfully created and you're now part of our community.

👤 ACCOUNT DETAILS:
═══════════════════════════════════════
Name: {user.first_name} {user.last_name}
Username: {user.username}
Email: {user.email}
Registration Date: {user.date_joined.strftime('%B %d, %Y at %I:%M %p')}

🚀 WHAT'S NEXT?
═══════════════════════════════════════
✓ Browse thousands of products
✓ Add items to your cart and checkout
✓ Track your orders in real-time
✓ Apply to become a seller and start your business
✓ Manage your profile and preferences

🛍️ READY TO SHOP?
═══════════════════════════════════════
Start exploring our marketplace and discover amazing products from verified sellers.

💼 INTERESTED IN SELLING?
═══════════════════════════════════════
Apply to become a seller from your dashboard and start your entrepreneurial journey with us!

Thank you for joining ISLINGTON MARKETPLACE. We're excited to have you aboard!

Best regards,
The ISLINGTON MARKETPLACE Team

---
Need help? Contact us at {settings.DEFAULT_FROM_EMAIL}
        """
        
        print("🔄 SENDING REGISTRATION EMAIL NOW...")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        print(f"✅ Registration confirmation email sent to {user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Registration email sending failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if not user:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if user:
            login(request, user)
            
            try:
                from cart.views import merge_session_cart_to_user
                merge_session_cart_to_user(request)
            except ImportError:
                try:
                    from cart.views import merge_cart_on_login
                    merge_cart_on_login(request)
                except ImportError:
                    pass  # Cart merge function not available
            
            messages.success(request, 'Logged in successfully!')
            return redirect('dashboard')
        else:
            return render(request, 'users/login.html', {'error': 'Invalid credentials'})
    return render(request, 'users/login.html')

def register_view(request):
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')  # Now separate from email
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone = request.POST.get('phone')  # New field
        city = request.POST.get('city')
        country = request.POST.get('country')
        zip_code = request.POST.get('zip')  # New field

        # Enhanced validation
        if not username:
            return render(request, 'users/register.html', {'error': 'Username is required'})
            
        if not phone:
            return render(request, 'users/register.html', {'error': 'Phone number is required'})

        if password != confirm_password:
            return render(request, 'users/register.html', {'error': 'Passwords do not match'})

        if len(password) < 8:
            return render(request, 'users/register.html', {'error': 'Password must be at least 8 characters'})

        if User.objects.filter(username=username).exists():
            return render(request, 'users/register.html', {'error': 'Username already exists'})

        if User.objects.filter(email=email).exists():
            return render(request, 'users/register.html', {'error': 'Email already registered'})

        try:
            # Creating user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # Updating the profile with additional info
            profile = user.profile
            profile.phone_number = phone  # New field
            profile.city = city
            profile.country = country
            profile.save()
            
            # 🎉 CREATE WELCOME NOTIFICATION
            create_notification(
                user=user,
                notification_type='system',
                title='Welcome to ISLINGTON MARKETPLACE!',
                message='Welcome! Start exploring products or apply to become a seller.',
                icon='fa-hand-wave',
                color='success',
                url='/dashboard/'
            )
            
            email_sent = send_registration_confirmation_email(user)
            if email_sent:
                messages.success(request, 'Account created successfully! Welcome email sent to your inbox.')
            else:
                messages.success(request, 'Account created successfully! (Welcome email notification failed)')

            login(request, user)
            return redirect('dashboard')

        except Exception as e:
            return render(request, 'users/register.html', {'error': 'Error creating account'})
    return render(request, 'users/register.html')

@login_required
def dashboard(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    # Calculate orders count
    orders_count = Order.objects.filter(user=request.user).count()
    
    # Calculate received orders count (for sellers)
    received_orders_count = 0
    if profile.seller_status == 'approved':
        received_orders_count = OrderItem.objects.filter(seller=request.user).count()

    # Real unread messages count
    unread_messages_count = profile.get_unread_messages_count()
    
    # Wishlist count
    wishlist_count = Wishlist.get_wishlist_count(request.user)

    # Add pending QR count for sidebar
    pending_qr_count = 0
    if profile.seller_status == 'approved':
        pending_qr_count = Order.objects.filter(
            items__seller=request.user,
            payment_method='QR Payment',
            payment_status='pending_verification'
        ).distinct().count()

    # Add seller stats if they're a seller
    seller_stats = {}
    if profile.seller_status == 'approved':
        seller_products = Product.objects.filter(seller=request.user)
        seller_stats = {
            'total_products': seller_products.count(),
            'pending_products': seller_products.filter(approval_status='pending').count(),
            'approved_products': seller_products.filter(approval_status='approved', status=True).count(),
            'rejected_products': seller_products.filter(approval_status='rejected').count(),
        }

    #  NOTIFICATION SYSTEM - Get real notifications 
    notifications = get_recent_notifications(request.user, limit=10)
    total_notifications = get_unread_notification_count(request.user)

    # Generate recent activities
    recent_activities = []
    
    # Recent orders
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:3]
    for order in recent_orders:
        recent_activities.append({
            'message': f'Order #{order.id} placed successfully',
            'created_at': order.created_at,
            'icon': 'fa-shopping-cart',
            'badge_color': 'primary'
        })
    
    # Recent wishlist additions
    recent_wishlist = Wishlist.objects.filter(user=request.user).order_by('-added_at')[:2]
    for item in recent_wishlist:
        recent_activities.append({
            'message': f'Added "{item.product.name}" to wishlist',
            'created_at': item.added_at,
            'icon': 'fa-heart',
            'badge_color': 'danger'
        })
    
    # Recent chat messages 
    recent_chat_messages = ChatMessage.objects.filter(
        chat_room__participants=request.user
    ).exclude(sender=request.user).order_by('-timestamp')[:2]
    
    for msg in recent_chat_messages:
        recent_activities.append({
            'message': f'New message from {msg.sender.get_full_name() or msg.sender.username}',
            'created_at': msg.timestamp,
            'icon': 'fa-comments',
            'badge_color': 'info'
        })
    # seller analytics summary

    if profile.seller_status == 'approved':
        seller_products = Product.objects.filter(seller=request.user, approval_status='approved')
    
    total_views = sum(p.view_count for p in seller_products)
    total_orders = sum(p.order_count for p in seller_products)
    total_revenue = sum(p.total_revenue for p in seller_products)
    
    seller_stats = {
        'total_products': seller_products.count(),
        'total_views': total_views,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'avg_conversion': (total_orders / total_views * 100) if total_views > 0 else 0,
    }

    # Recent seller activities (if seller)
    if profile.seller_status == 'approved':
        # Recent products
        recent_products = Product.objects.filter(seller=request.user).order_by('-created_at')[:2]
        for product in recent_products:
            recent_activities.append({
                'message': f'Product "{product.name}" added for review',
                'created_at': product.created_at,
                'icon': 'fa-plus',
                'badge_color': 'success'
            })
        
        # Recent received orders
        recent_received = OrderItem.objects.filter(seller=request.user).order_by('-order__created_at')[:2]
        for item in recent_received:
            recent_activities.append({
                'message': f'New order received for "{item.product.name}"',
                'created_at': item.order.created_at,
                'icon': 'fa-bell',
                'badge_color': 'warning'
            })
        
        # Add QR payment notifications to recent activities
        if pending_qr_count > 0:
            recent_activities.append({
                'message': f'{pending_qr_count} QR payment(s) awaiting verification',
                'created_at': timezone.now(),
                'icon': 'fa-qrcode',
                'badge_color': 'warning'
            })
    
    # Sort activities by date
    recent_activities.sort(key=lambda x: x['created_at'], reverse=True)
    recent_activities = recent_activities[:5]

    # Additional stats
    context = {
        'profile': profile,
        'orders_count': orders_count,
        'received_orders_count': received_orders_count,
        'user': request.user,
        'seller_stats': seller_stats,
        'recent_activities': recent_activities,
        'wishlist_count': wishlist_count,  # Updated with real count
        'unread_messages_count': unread_messages_count, 
        'pending_qr_count': pending_qr_count,
        'notifications': notifications,
        'total_notifications': total_notifications,
    }
    return render(request, 'users/dashboard.html', context)

@login_required
def received_orders(request):
    """Display items that the customer has received (delivered orders) - FOR CUSTOMERS"""
    try:
        # Get all order items for orders that are delivered/completed for this user
        received_items = OrderItem.objects.filter(
            order__user=request.user,
            ordered=True,
            order__order_status__in=['delivered', 'completed']
        ).select_related(
            'product', 'order', 'seller', 'order__user', 'product__category'
        ).prefetch_related(
            'variations__variation_type',
            'variations__variation_option'
        ).order_by('-order__delivered_date', '-order__created_at')
        
        # Get unique orders count
        unique_orders = received_items.values('order').distinct()
        unique_orders_count = unique_orders.count()
        
        # Get reviewed product IDs to show "Reviewed" status
        reviewed_product_ids = []
        try:
            from products.models import Review
            reviews = Review.objects.filter(user=request.user).values_list('product_id', flat=True)
            reviewed_product_ids = list(reviews)
        except (ImportError, AttributeError):
            reviewed_product_ids = []
        
        # Count items pending review
        pending_reviews_count = received_items.exclude(product_id__in=reviewed_product_ids).count()
        
        context = {
            'received_items': received_items,
            'unique_orders_count': unique_orders_count,
            'pending_reviews_count': pending_reviews_count,
            'reviewed_product_ids': reviewed_product_ids,
        }
        return render(request, 'users/received_orders.html', context)  # Use existing template!
        
    except Exception as e:
        print(f"Error in received_orders view: {e}")
        messages.error(request, 'Error loading received orders.')
        return redirect('dashboard')

@login_required
def seller_received_orders(request):
    """Display orders received by seller from customers - FOR SELLERS"""
    profile = request.user.profile

    # Gate: Only approved sellers can access
    if profile.seller_status != 'approved':
        messages.error(request, 'You need to be an approved seller to access this page.')
        return redirect('dashboard')

    # Get ORDER ITEMS where this user is the seller
    seller_received_orders = OrderItem.objects.filter(
        seller=request.user,
        ordered=True
    ).select_related('order', 'product', 'order__user').order_by('-order__created_at')

    # Calculate status counts
    pending_orders_count = seller_received_orders.filter(order__order_status='pending').count()
    processing_orders_count = seller_received_orders.filter(order__order_status='processing').count()
    shipped_orders_count = seller_received_orders.filter(order__order_status='shipped').count()
    completed_orders_count = seller_received_orders.filter(order__order_status='completed').count()

    context = {
        'received_orders': seller_received_orders,
        'pending_orders_count': pending_orders_count,
        'processing_orders_count': processing_orders_count,
        'shipped_orders_count': shipped_orders_count,
        'completed_orders_count': completed_orders_count,
        'today': timezone.now(),
    }
    return render(request, 'users/seller_received_orders.html', context)

@login_required
def edit_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        # Update user fields
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()

        # Update profile fields
        profile.phone_number = request.POST.get('phone_number', '')
        profile.address_line_1 = request.POST.get('address_line_1', '')
        profile.address_line_2 = request.POST.get('address_line_2', '')
        profile.city = request.POST.get('city', '')
        profile.state = request.POST.get('state', '')
        profile.country = request.POST.get('country', '')

        if request.FILES.get('profile_picture'):
            profile.profile_picture = request.FILES['profile_picture']

        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('dashboard')
    return render(request, 'users/edit_profile.html', {'profile': profile})

@login_required
def change_password(request):
    if request.method == 'POST':
        current = request.POST.get('current_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')

        if not request.user.check_password(current):
            return render(request, 'users/change_password.html', {'error': 'Current password is incorrect'})

        if new != confirm:
            return render(request, 'users/change_password.html', {'error': 'Passwords do not match'})

        if len(new) < 8:
            return render(request, 'users/change_password.html', {'error': 'Password must be at least 8 characters'})

        request.user.set_password(new)
        request.user.save()
        messages.success(request, 'Password changed successfully! Please login again.')
        return redirect('login')
    return render(request, 'users/change_password.html')

def logout_view(request):
    # Store cart items before logout
    cart_items_to_preserve = []

    if request.user.is_authenticated:
        try:
            from cart.models import Cart, CartItem
            user_cart = Cart.objects.get(user=request.user)
            user_cart_items = CartItem.objects.filter(cart=user_cart, is_active=True)

            # Store the items we want to preserve i.e. products_id and quantity
            for item in user_cart_items:
                cart_items_to_preserve.append({
                    'product_id': item.product.id,
                    'quantity': item.quantity
                })
        except Cart.DoesNotExist:
            pass
    
    logout(request)

    # Recreate cart items in new session
    if cart_items_to_preserve:
        from cart.models import Cart, CartItem
        from products.models import Product

        # Ensure session exists after logout
        if not request.session.session_key:
            request.session.create()

        # Get cart_id - use session key directly to avoid None
        cart_id = request.session.session_key

        # Making sure cart_id is not None before creating
        if cart_id:
            session_cart = Cart.objects.create(cart_id=cart_id)
            
            # Adding preserved items to session cart
            for item_data in cart_items_to_preserve:
                try:
                    product = Product.objects.get(id=item_data['product_id'])
                    CartItem.objects.create(
                        product=product,
                        cart=session_cart,
                        quantity=item_data['quantity']
                    )
                except Product.DoesNotExist:
                    pass
    
    messages.success(request, 'Logged out successfully!')
    return redirect('home')

@login_required
def my_selling_items(request):
    """Display seller's products with real analytics"""
    profile = request.user.profile

    # Gate: Only approved sellers can access
    if profile.seller_status != 'approved':
        messages.error(request, 'You need to be an approved seller to access this page.')
        return redirect('dashboard')

    # Get seller's products with analytics
    products = Product.objects.filter(seller=request.user).order_by('-created_at')
    
    # Calculate analytics for each product
    for product in products:
        if product.approval_status == 'approved':
            # Get fresh analytics data
            analytics = product.get_analytics_data()
            # analytics to product object for template access
            product.analytics = analytics

    context = {
        'products': products,
        'total_products': products.count(),
        'pending_products': products.filter(approval_status='pending').count(),
        'approved_products': products.filter(approval_status='approved').count(),
        'rejected_products': products.filter(approval_status='rejected').count(),
    }
    return render(request, 'users/my_selling_items.html', context)

@login_required
def become_seller(request):
    """Apply to become a seller with QR code upload"""
    profile = request.user.profile

    # Check if already a seller or applied
    if profile.seller_status in ['approved', 'pending']:
        messages.info(request, f'Your seller application is {profile.seller_status}.')
        return redirect('dashboard')

    if request.method == 'POST':
        business_name = request.POST.get('business_name', '').strip()
        business_description = request.POST.get('business_description', '').strip()
        qr_payment_method = request.POST.get('qr_payment_method', '').strip()
        qr_payment_info = request.POST.get('qr_payment_info', '').strip()
        payment_qr_code = request.FILES.get('payment_qr_code')

        # Validation
        if not business_name:
            messages.error(request, 'Business name is required.')
            return render(request, 'users/become_seller.html')
        
        if not qr_payment_method:
            messages.error(request, 'Please select a payment method for your QR code.')
            return render(request, 'users/become_seller.html')
            
        if not qr_payment_info:
            messages.error(request, 'Please provide payment information (phone number, account name, etc.).')
            return render(request, 'users/become_seller.html')
            
        if not payment_qr_code:
            messages.error(request, 'Please upload your payment QR code.')
            return render(request, 'users/become_seller.html')

        # Validate QR code file
        if payment_qr_code.size > 5 * 1024 * 1024:  # 5MB limit
            messages.error(request, 'QR code image must be less than 5MB.')
            return render(request, 'users/become_seller.html')

        # Update profile
        profile.business_name = business_name
        profile.business_description = business_description
        profile.qr_payment_method = qr_payment_method
        profile.qr_payment_info = qr_payment_info
        profile.payment_qr_code = payment_qr_code
        profile.seller_status = 'pending'
        profile.seller_application_date = timezone.now()
        profile.save()

        # Create notification for seller application
        create_notification(
            user=request.user,
            notification_type='system',
            title='Seller Application Submitted!',
            message='Your seller application is under review. We will notify you once it\'s processed.',
            icon='fa-store',
            color='warning',
            url='/dashboard/'
        )

        messages.success(request, 'Seller application submitted with QR code! We will review and get back to you.')
        return redirect('dashboard')
    
    return render(request, 'users/become_seller.html')

@login_required
def add_product(request):
    """Add new product - ONLY for approved sellers"""
    profile = request.user.profile

    # Gate: Only approved sellers can add products
    if profile.seller_status != 'approved':
        messages.error(request, 'You need to be an approved seller to add products.')
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            # Get basic product data
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            price = request.POST.get('price')
            stock = request.POST.get('stock')
            category_id = request.POST.get('category')
            brand = request.POST.get('brand', '').strip()
            spec = request.POST.get('spec', '').strip()

            # FIELDS FOR THRIFT/SALE
            product_type = request.POST.get('product_type', 'new')
            condition = request.POST.get('condition', '')
            years_used = request.POST.get('years_used', '')

            # Sale fields
            is_on_sale = request.POST.get('is_on_sale') == 'on'
            original_price = request.POST.get('original_price', '')
            discount_percentage = request.POST.get('discount_percentage', '')
            sale_start_date = request.POST.get('sale_start_date', '')
            sale_end_date = request.POST.get('sale_end_date', '')

            # Validation
            if not all([name, description, price, stock, category_id]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'users/add_product.html', get_add_product_context())
            
            category = Category.objects.get(id=category_id, status=True)
            
            # Get selected variation types
            selected_variation_types = request.POST.getlist('enabled_variation_types')
            
            # Create main product with all fields
            product = Product.objects.create(
                name=name,
                description=description,
                price=float(price),
                stock=int(stock),
                category=category,
                brand=brand,
                spec=spec,
                seller=request.user,
                status=False,
                admin_approved=False,
                approval_status='pending',
                submitted_for_approval=timezone.now(),
                # FIELDS
                product_type=product_type,
                condition=condition if condition else None,
                years_used=int(years_used) if years_used else None,
                is_on_sale=is_on_sale,
                original_price=float(original_price) if original_price else None,
                discount_percentage=int(discount_percentage) if discount_percentage else 0,
                sale_start_date=sale_start_date if sale_start_date else None,
                sale_end_date=sale_end_date if sale_end_date else None,
            )
            
            # Handle main product image
            if request.FILES.get('image'):
                product.image = request.FILES['image']
                product.save()
            
            # Handle variations if any
            variation_data = {}
            for key in request.POST.keys():
                if key.startswith('variation_'):
                    parts = key.split('_')
                    if len(parts) >= 3:  # variation_type_option_field
                        var_type_id = parts[1]
                        option_id = parts[2]
                        field = '_'.join(parts[3:]) if len(parts) > 3 else 'selected'
                        
                        if var_type_id not in variation_data:
                            variation_data[var_type_id] = {}
                        if option_id not in variation_data[var_type_id]:
                            variation_data[var_type_id][option_id] = {}
                        
                        variation_data[var_type_id][option_id][field] = request.POST[key]
            
            # Process variation files
            variation_files = {}
            for key in request.FILES.keys():
                if key.startswith('variation_'):
                    parts = key.split('_')
                    if len(parts) >= 4:  # variation_type_option_image1
                        var_type_id = parts[1]
                        option_id = parts[2]
                        field = '_'.join(parts[3:])
                        
                        if var_type_id not in variation_files:
                            variation_files[var_type_id] = {}
                        if option_id not in variation_files[var_type_id]:
                            variation_files[var_type_id][option_id] = {}
                        
                        variation_files[var_type_id][option_id][field] = request.FILES[key]
            
            for var_type_id, options in variation_data.items():
                try:
                    variation_type = VariationType.objects.get(id=var_type_id)
                    
                    # Only create variations for enabled types
                    if str(variation_type.id) not in selected_variation_types:
                        continue
                    
                    for option_id, data in options.items():
                        # Check if checkbox was actually selected
                        checkbox_name = f'variation_{var_type_id}_{option_id}_selected'
                        if checkbox_name in request.POST and request.POST[checkbox_name]:
                            try:
                                variation_option = VariationOption.objects.get(id=option_id)
                                
                                # Create the variation
                                product_variation = ProductVariation.objects.create(
                                    product=product,
                                    variation_type=variation_type,
                                    variation_option=variation_option,
                                    price_adjustment=float(data.get('price_adjustment', 0)),
                                    stock_quantity=int(data.get('stock', 0)),
                                    sku=data.get('sku', ''),
                                    is_active=True
                                )
                                
                                # Add images if uploaded
                                files = variation_files.get(var_type_id, {}).get(option_id, {})
                                if 'image1' in files:
                                    product_variation.image1 = files['image1']
                                if 'image2' in files:
                                    product_variation.image2 = files['image2']
                                if 'image3' in files:
                                    product_variation.image3 = files['image3']
                                
                                product_variation.save()
                                
                                print(f"✅ Created variation: {variation_type.name} - {variation_option.value} for {product.name}")
                                
                            except VariationOption.DoesNotExist:
                                continue
                except VariationType.DoesNotExist:
                    continue
            
            # Create notification for product submission
            create_notification(
                user=request.user,
                notification_type='system',
                title='Product Submitted for Review!',
                message=f'Your product "{name}" has been submitted and is awaiting approval.',
                icon='fa-box',
                color='info',
                url='/my-selling-items/'
            )
            
            messages.success(request, f'Product "{name}" submitted for review!')
            return redirect('my_selling_items')
            
        except Category.DoesNotExist:
            messages.error(request, 'Invalid category selected.')
        except (ValueError, TypeError):
            messages.error(request, 'Please enter valid price and stock numbers.')
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
    
    # GET request - show form
    return render(request, 'users/add_product.html', get_add_product_context())

def get_add_product_context():
    """Get context data for add_product view"""
    categories = Category.objects.filter(status=True)
    variation_types = VariationType.objects.filter(is_active=True).prefetch_related('options')

    # Get available variations for each category
    category_variations = {}
    for category in categories:
        variations = CategoryVariation.objects.filter(
            category=category,
            variation_type__is_active=True
        ).select_related('variation_type').prefetch_related('variation_type__options')

        category_data = []
        for cat_var in variations:
            var_type = cat_var.variation_type
            options_data = []
            for option in var_type.options.filter(is_active=True):
                options_data.append({
                    'id': option.id,
                    'value': option.value,
                    'get_display_value': option.get_display_value(),
                    'color_code': option.color_code
                })
            
            category_data.append({
                'variation_type': {
                    'id': var_type.id,
                    'name': var_type.name,
                    'display_name': var_type.display_name,
                    'options': options_data
                },
                'is_required': cat_var.is_required
            })

        category_variations[category.id] = category_data
    
    return {
        'categories': categories,
        'variation_types': variation_types,
        'category_variations': json.dumps(category_variations)
    }

@login_required
def verify_qr_payments(request):
    """Allow sellers to verify QR payments they received"""
    profile = request.user.profile
    
    # Gate: Only approved sellers can access
    if profile.seller_status != 'approved':
        messages.error(request, 'You need to be an approved seller to access this page.')
        return redirect('dashboard')

    # Handle verification actions
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        action = request.POST.get('action')
        
        try:
            order = Order.objects.filter(
                id=order_id, 
                items__seller=request.user,
                payment_method='QR Payment',
                payment_status='pending_verification'
            ).distinct().first()
            
            # Check if order exists
            if not order:
                messages.error(request, 'Order not found or unauthorized access.')
                return redirect('verify_qr_payments')
            
            if action == 'verify':
                order.payment_status = 'completed'
                order.status = 'Confirmed'
                order.order_status = 'confirmed'
                order.qr_payment_verified_by = request.user
                order.qr_payment_verified_at = timezone.now()
                order.save()
                
                # Send confirmation email
                from orders.views import send_order_confirmation_email
                send_order_confirmation_email(order)
                
                # Create notification for payment verification
                create_notification(
                    user=order.user,
                    notification_type='order',
                    title='Payment Verified!',
                    message=f'Your payment for Order #{order.order_number} has been verified and confirmed.',
                    icon='fa-check-circle',
                    color='success',
                    url='/orders/my-orders/'
                )
                
                messages.success(request, f'✅ Payment verified for Order #{order.order_number}. Customer notified!')
                
            elif action == 'reject':
                print(f"🚫 REJECTING ORDER #{order.order_number}")
                
                # Import the functions
                from orders.views import send_order_rejection_email, revert_stock_after_rejection
                
                # Revert stock first
                stock_reverted = revert_stock_after_rejection(order)
                
                # Update order status
                order.payment_status = 'rejected'
                order.status = 'Payment Rejected'
                order.order_status = 'cancelled'
                order.save()
                
                # Send rejection email
                email_sent = send_order_rejection_email(order)
                
                # Create notification for payment rejection
                create_notification(
                    user=order.user,
                    notification_type='order',
                    title='Payment Rejected',
                    message=f'Your payment for Order #{order.order_number} could not be verified and has been rejected.',
                    icon='fa-times-circle',
                    color='danger',
                    url='/orders/my-orders/'
                )
                
                if stock_reverted and email_sent:
                    messages.warning(request, f'❌ Payment rejected for Order #{order.order_number}. Stock reverted and customer notified via email.')
                elif stock_reverted:
                    messages.warning(request, f'❌ Payment rejected for Order #{order.order_number}. Stock reverted. (Email notification failed)')
                elif email_sent:
                    messages.warning(request, f'❌ Payment rejected for Order #{order.order_number}. Customer notified. (Stock reversion failed)')
                else:
                    messages.error(request, f'❌ Payment rejected for Order #{order.order_number}. WARNING: Stock reversion and email notification failed!')
                
        except Exception as e:
            print(f"❌ Error in verification: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error: {str(e)}')

    # Get pending orders for this seller 
    pending_orders = Order.objects.filter(
        items__seller=request.user,
        payment_method='QR Payment',
        payment_status='pending_verification'
    ).distinct().order_by('-created_at')
    
    # Get recently verified orders 
    verified_orders = Order.objects.filter(
        items__seller=request.user,
        payment_method='QR Payment',
        payment_status='completed',
        qr_payment_verified_by=request.user
    ).distinct().order_by('-qr_payment_verified_at')[:10]
    
    # Calculate total pending amount
    total_pending_amount = sum(order.grand_total for order in pending_orders)
    
    context = {
        'pending_orders': pending_orders,
        'verified_orders': verified_orders,
        'total_pending_amount': total_pending_amount,
    }
    return render(request, 'users/verify_qr_payments.html', context)

# CHAT SYSTEM

@login_required
def chat_list(request):
    """Display all chat rooms for current user with last messages - Enhanced"""
    try:
        # Clear any stale typing indicators first
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(minutes=5)
        TypingIndicator.objects.filter(created_at__lt=cutoff_time).delete()
        
        # Get chat rooms with proper error handling
        chat_rooms = ChatRoom.objects.filter(
            participants=request.user,
            is_active=True  # Only show active chats
        ).prefetch_related(
            'participants', 
            'messages__sender',
            'product'
        ).order_by('-updated_at')
        
        # Add unread count and last message for each chat
        chat_data = []
        for chat in chat_rooms:
            try:
                other_participant = chat.get_other_participant(request.user)
                
                # Skip chats where we can't find the other participant
                if not other_participant:
                    continue
                    
                unread_count = ChatMessage.objects.filter(
                    chat_room=chat,
                    is_read=False
                ).exclude(sender=request.user).count()
                
                last_message = chat.get_last_message()
                
                chat_data.append({
                    'chat': chat,
                    'other_participant': other_participant,
                    'unread_count': unread_count,
                    'last_message': last_message,
                })
            except Exception as e:
                print(f"Error processing chat {chat.id}: {e}")
                continue
        
        context = {
            'chat_data': chat_data,
        }
        return render(request, 'users/chat_list.html', context)
        
    except Exception as e:
        print(f"Error in chat_list view: {e}")
        messages.error(request, 'Error loading chats. Please try again.')
        return redirect('dashboard')

@login_required
def chat_detail(request, chat_id):
    """Display specific chat room with messages"""
    chat_room = get_object_or_404(ChatRoom, id=chat_id, participants=request.user)
    
    # Get other participant safely
    other_participant = chat_room.get_other_participant(request.user)
    if not other_participant:
        messages.error(request, 'Chat participant not found.')
        return redirect('chat_list')
    
    # Mark messages as read when user views chat
    unread_messages = ChatMessage.objects.filter(
        chat_room=chat_room,
        is_read=False
    ).exclude(sender=request.user)
    
    for msg in unread_messages:
        msg.mark_as_read(by_user=request.user)
    
    # Update user's last seen
    request.user.profile.update_last_seen()
    
    messages_list = chat_room.messages.select_related('sender').order_by('timestamp')
    
    context = {
        'chat_room': chat_room,
        'messages': messages_list,
        'other_participant': other_participant,
    }
    return render(request, 'users/chat_detail.html', context)

@login_required
def start_chat_with_user(request, username):
    """Start or continue chat with specific user"""
    other_user = get_object_or_404(User, username=username)
    
    if other_user == request.user:
        messages.error(request, "You cannot chat with yourself!")
        return redirect('chat_list')
    
    # Check if chat already exists between these two users
    chat_room = None
    
    # Find existing chat room between exactly these two users
    for room in ChatRoom.objects.filter(participants=request.user):
        if room.participants.count() == 2 and other_user in room.participants.all():
            chat_room = room
            break
    
    if not chat_room:
        # Create new chat room
        chat_room = ChatRoom.objects.create()
        chat_room.participants.add(request.user, other_user)
        
        # Add a welcome message
        ChatMessage.objects.create(
            chat_room=chat_room,
            sender=request.user,
            message=f"Hi {other_user.first_name or other_user.username}! 👋"
        )
    
    return redirect('chat_detail', chat_id=chat_room.id)

@login_required 
def start_chat_about_product(request, product_id):
    """Start chat with seller about specific product"""
    from products.models import Product
    product = get_object_or_404(Product, id=product_id)
    seller = product.seller
    
    if seller == request.user:
        messages.error(request, "You cannot chat about your own product!")
        return redirect('products:product_detail', product.category.slug, product.slug)
    
    # Check if chat already exists for this product between these users
    chat_room = ChatRoom.objects.filter(
        participants=request.user,
        product=product
    ).filter(
        participants=seller
    ).first()
    
    if not chat_room:
        # Create new product-specific chat
        chat_room = ChatRoom.objects.create(product=product)
        chat_room.participants.add(request.user, seller)
        
        # Add initial message about the product
        ChatMessage.objects.create(
            chat_room=chat_room,
            sender=request.user,
            message=f"Hi! I'm interested in your product: {product.name}"
        )
    
    return redirect('chat_detail', chat_id=chat_room.id)

@login_required
def send_message(request):
    """AJAX endpoint to send message with enhanced status"""
    if request.method == 'POST':
        chat_id = request.POST.get('chat_id')
        message_text = request.POST.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        if chat_id and message_text:
            try:
                chat_room = get_object_or_404(ChatRoom, id=chat_id, participants=request.user)
                
                message = ChatMessage.objects.create(
                    chat_room=chat_room,
                    sender=request.user,
                    message=message_text,
                    status='sent'  #  Set initial status
                )
                
                # Update chat room timestamp
                chat_room.updated_at = timezone.now()
                chat_room.save()
                
                # Clear typing indicator
                TypingIndicator.objects.filter(
                    chat_room=chat_room,
                    user=request.user
                ).delete()
                
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': message.id,
                        'message': message.message,
                        'sender': message.sender.username,
                        'sender_name': message.sender.get_full_name() or message.sender.username,
                        'timestamp': message.get_time_display(),  #  Human-readable time
                        'status_icon': message.get_status_icon(),  #  Status icon
                        'is_mine': True
                    }
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def set_typing(request, chat_id):
    """Set typing indicator"""
    if request.method == 'POST':
        try:
            chat_room = get_object_or_404(ChatRoom, id=chat_id, participants=request.user)
            
            # Create or update typing indicator
            typing_indicator, created = TypingIndicator.objects.get_or_create(
                chat_room=chat_room,
                user=request.user
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def clear_typing(request, chat_id):
    """Clear typing indicator"""
    if request.method == 'POST':
        try:
            chat_room = get_object_or_404(ChatRoom, id=chat_id, participants=request.user)
            
            TypingIndicator.objects.filter(
                chat_room=chat_room,
                user=request.user
            ).delete()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def get_typing_users(request, chat_id):
    """Get users currently typing"""
    try:
        chat_room = get_object_or_404(ChatRoom, id=chat_id, participants=request.user)
        
        # Clean up old typing indicators (older than 10 seconds)
        cutoff_time = timezone.now() - timedelta(seconds=10)
        TypingIndicator.objects.filter(
            chat_room=chat_room,
            created_at__lt=cutoff_time
        ).delete()
        
        # Get current typing users (excluding current user)
        typing_users = TypingIndicator.objects.filter(
            chat_room=chat_room
        ).exclude(user=request.user).select_related('user')
        
        users_data = []
        for indicator in typing_users:
            users_data.append({
                'username': indicator.user.username,
                'full_name': indicator.user.get_full_name() or indicator.user.username
            })
        
        return JsonResponse({
            'success': True,
            'typing_users': users_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_new_messages(request, chat_id):
    """AJAX endpoint to get new messages with enhanced data"""
    chat_room = get_object_or_404(ChatRoom, id=chat_id, participants=request.user)
    last_message_id = request.GET.get('last_id', 0)
    
    new_messages = ChatMessage.objects.filter(
        chat_room=chat_room,
        id__gt=last_message_id
    ).exclude(sender=request.user).select_related('sender')
    
    # Mark new messages as read
    for msg in new_messages:
        msg.mark_as_read(by_user=request.user)
    
    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'message': msg.message,
            'sender': msg.sender.username,
            'sender_name': msg.sender.get_full_name() or msg.sender.username,
            'timestamp': msg.get_time_display(),  #  Human-readable time
            'status_icon': msg.get_status_icon(),  # Status icon
            'is_mine': False
        })
    
    return JsonResponse({
        'success': True,
        'messages': messages_data
    })

# PRODUCT MANAGEMENT

@login_required
def update_product_stock(request, product_id):
    """AJAX endpoint to update product stock - ONLY for approved products"""
    if request.method == 'POST':
        try:
            # Get product with seller and approval checks
            product = get_object_or_404(Product, id=product_id, seller=request.user)
            
            # PERMISSION CHECK: Only approved products can be edited
            if product.approval_status != 'approved':
                return JsonResponse({
                    'success': False, 
                    'message': 'Only approved products can have stock updated',
                    'original_stock': product.stock
                })
            
            data = json.loads(request.body)
            new_stock = int(data.get('stock', 0))
            
            # Validate stock value
            if new_stock < 0:
                return JsonResponse({
                    'success': False, 
                    'message': 'Stock cannot be negative',
                    'original_stock': product.stock
                })
            
            old_stock = product.stock
            product.stock = new_stock
            product.save()
            
            # Create notification for significant stock changes
            if old_stock == 0 and new_stock > 0:
                create_notification(
                    user=request.user,
                    notification_type='system',
                    title='Product Back in Stock!',
                    message=f'"{product.name}" is now back in stock with {new_stock} units.',
                    icon='fa-box',
                    color='success',
                    url='/my-selling-items/'
                )
            
            return JsonResponse({
                'success': True,
                'message': f'Stock updated to {new_stock}',
                'new_stock': new_stock
            })
            
        except ValueError:
            return JsonResponse({
                'success': False, 
                'message': 'Please enter a valid number'
            })
        except Exception as e:
            print(f"Error updating stock: {e}")
            return JsonResponse({
                'success': False, 
                'message': 'Error updating stock'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def toggle_product_status(request, product_id):
    """AJAX endpoint to toggle product live/hidden status - ONLY for approved products"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id, seller=request.user)
            
            # PERMISSION CHECK: Only approved products can have visibility toggled
            if product.approval_status != 'approved':
                return JsonResponse({
                    'success': False, 
                    'message': 'Only approved products can have visibility changed'
                })
            
            data = json.loads(request.body)
            new_status = data.get('status', False)
            
            product.status = new_status
            product.save()
            
            # Create notification for visibility change
            status_text = 'live' if new_status else 'hidden'
            create_notification(
                user=request.user,
                notification_type='system',
                title=f'Product {status_text.title()}!',
                message=f'"{product.name}" is now {status_text} on the marketplace.',
                icon='fa-eye' if new_status else 'fa-eye-slash',
                color='success' if new_status else 'warning',
                url='/my-selling-items/'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Product is now {status_text}',
                'status': new_status
            })
            
        except Exception as e:
            print(f"Error toggling product status: {e}")
            return JsonResponse({
                'success': False, 
                'message': 'Error updating product visibility'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def delete_product(request, product_id):
    """AJAX endpoint to delete product - Enhanced with proper cleanup"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id, seller=request.user)
            product_name = product.name
            
            # Store product info before deletion
            was_approved = product.approval_status == 'approved'
            
            # Delete the product (this will also delete related variations, images, etc.)
            product.delete()
            
            # Create notification
            create_notification(
                user=request.user,
                notification_type='system',
                title='Product Deleted!',
                message=f'"{product_name}" has been removed from your products.',
                icon='fa-trash',
                color='info',
                url='/my-selling-items/'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'"{product_name}" deleted successfully'
            })
            
        except Exception as e:
            print(f"Error deleting product: {e}")
            return JsonResponse({
                'success': False, 
                'message': 'Error deleting product'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def duplicate_product(request, product_id):
    """AJAX endpoint to duplicate product - ONLY for approved products"""
    if request.method == 'POST':
        try:
            original_product = get_object_or_404(Product, id=product_id, seller=request.user)
            
            # PERMISSION CHECK: Only approved products can be duplicated
            if original_product.approval_status != 'approved':
                return JsonResponse({
                    'success': False, 
                    'message': 'Only approved products can be duplicated'
                })
            
            with transaction.atomic():
                # Create duplicate product
                duplicate_product = Product.objects.create(
                    name=f"{original_product.name} (Copy)",
                    description=original_product.description,
                    price=original_product.price,
                    stock=original_product.stock,
                    category=original_product.category,
                    brand=original_product.brand,
                    spec=original_product.spec,
                    seller=request.user,
                    status=False,  # Start as hidden
                    admin_approved=False,  # Needs approval again
                    approval_status='pending',  # Needs approval
                    submitted_for_approval=timezone.now(),
                    # Copy other fields
                    product_type=original_product.product_type,
                    condition=original_product.condition,
                    years_used=original_product.years_used,
                    is_on_sale=original_product.is_on_sale,
                    original_price=original_product.original_price,
                    discount_percentage=original_product.discount_percentage,
                    sale_start_date=original_product.sale_start_date,
                    sale_end_date=original_product.sale_end_date,
                )
                
                # Copy main product image if exists
                if original_product.image:
                    try:
                        # Copy the image file
                        original_image_path = original_product.image.path
                        if os.path.exists(original_image_path):
                            # Generate new filename
                            import uuid
                            file_extension = os.path.splitext(original_product.image.name)[1]
                            new_filename = f"products/{uuid.uuid4()}{file_extension}"
                            
                            # Copy file content
                            with open(original_image_path, 'rb') as original_file:
                                duplicate_product.image.save(
                                    new_filename,
                                    original_file,
                                    save=True
                                )
                    except Exception as e:
                        print(f"Error copying product image: {e}")
                
                # Copy variations if any exist
                original_variations = ProductVariation.objects.filter(product=original_product)
                for variation in original_variations:
                    ProductVariation.objects.create(
                        product=duplicate_product,
                        variation_type=variation.variation_type,
                        variation_option=variation.variation_option,
                        price_adjustment=variation.price_adjustment,
                        stock_quantity=variation.stock_quantity,
                        sku=f"{variation.sku}_copy" if variation.sku else "",
                        is_active=variation.is_active,
                        # Note: Images are not copied for variations to avoid complexity
                    )
            
            # Create notification
            create_notification(
                user=request.user,
                notification_type='system',
                title='Product Duplicated!',
                message=f'A copy of "{original_product.name}" has been created and submitted for approval.',
                icon='fa-copy',
                color='info',
                url='/my-selling-items/'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Product duplicated successfully! The copy is now pending approval.',
                'duplicate_id': duplicate_product.id
            })
            
        except Exception as e:
            print(f"Error duplicating product: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False, 
                'message': 'Error duplicating product'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def edit_product(request, product_id):
    """Load product edit form in modal - ONLY for approved products"""
    try:
        product = get_object_or_404(Product, id=product_id, seller=request.user)
        
        # PERMISSION CHECK: Only approved products can be edited
        if product.approval_status != 'approved':
            return render(request, 'users/partials/edit_product_denied.html', {
                'product': product,
                'message': 'Only approved products can be edited'
            })
        
        if request.method == 'POST':
            # Handle form submission
            try:
                # Update basic fields
                product.name = request.POST.get('name', product.name).strip()
                product.description = request.POST.get('description', product.description).strip()
                product.price = float(request.POST.get('price', product.price))
                product.stock = int(request.POST.get('stock', product.stock))
                product.brand = request.POST.get('brand', product.brand).strip()
                product.spec = request.POST.get('spec', product.spec).strip()
                
                # Update sale fields
                product.is_on_sale = request.POST.get('is_on_sale') == 'on'
                if product.is_on_sale:
                    product.original_price = float(request.POST.get('original_price', 0)) or None
                    product.discount_percentage = int(request.POST.get('discount_percentage', 0))
                    product.sale_start_date = request.POST.get('sale_start_date') or None
                    product.sale_end_date = request.POST.get('sale_end_date') or None
                else:
                    product.original_price = None
                    product.discount_percentage = 0
                    product.sale_start_date = None
                    product.sale_end_date = None
                
                # Handle new main image if uploaded
                if request.FILES.get('image'):
                    product.image = request.FILES['image']
                
                product.save()
                
                # Create notification
                create_notification(
                    user=request.user,
                    notification_type='system',
                    title='Product Updated!',
                    message=f'"{product.name}" has been updated successfully.',
                    icon='fa-edit',
                    color='success',
                    url='/my-selling-items/'
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Product updated successfully!'
                })
                
            except (ValueError, TypeError) as e:
                return JsonResponse({
                    'success': False,
                    'message': 'Please enter valid values for price and stock'
                })
            except Exception as e:
                print(f"Error updating product: {e}")
                return JsonResponse({
                    'success': False,
                    'message': 'Error updating product'
                })
        
        # GET request - return form HTML
        context = {
            'product': product,
            'categories': Category.objects.filter(status=True),
        }
        return render(request, 'users/partials/edit_product_form.html', context)
        
    except Exception as e:
        print(f"Error in edit_product: {e}")
        return render(request, 'users/partials/edit_product_error.html', {
            'error': 'Error loading product details'
        })

@login_required
def bulk_update_stock(request):
    """AJAX endpoint for bulk stock updates - ONLY for approved products"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_ids = data.get('products', [])
            action = data.get('action')
            amount = int(data.get('amount', 0))
            
            if amount < 0:
                return JsonResponse({
                    'success': False, 
                    'message': 'Amount cannot be negative'
                })
            
            # Get products with permission check
            products = Product.objects.filter(
                id__in=product_ids, 
                seller=request.user,
                approval_status='approved'  # ONLY approved products
            )
            
            if not products.exists():
                return JsonResponse({
                    'success': False, 
                    'message': 'No approved products found to update'
                })
            
            updated_count = 0
            with transaction.atomic():
                for product in products:
                    old_stock = product.stock
                    
                    if action == 'set':
                        product.stock = amount
                    elif action == 'add':
                        product.stock += amount
                    elif action == 'subtract':
                        product.stock = max(0, product.stock - amount)
                    
                    product.save()
                    updated_count += 1
            
            # Create notification
            create_notification(
                user=request.user,
                notification_type='system',
                title='Bulk Stock Update Complete!',
                message=f'Stock updated for {updated_count} approved products.',
                icon='fa-boxes',
                color='success',
                url='/my-selling-items/'
            )
            
            return JsonResponse({
                'success': True, 
                'updated_count': updated_count,
                'message': f'Stock updated for {updated_count} products'
            })
            
        except ValueError:
            return JsonResponse({
                'success': False, 
                'message': 'Please enter a valid amount'
            })
        except Exception as e:
            print(f"Error in bulk stock update: {e}")
            return JsonResponse({
                'success': False, 
                'message': 'Error updating stock'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def bulk_toggle_visibility(request):
    """AJAX endpoint for bulk visibility toggle - ONLY for approved products"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_ids = data.get('products', [])
            action = data.get('action', 'toggle')
            
            # Get products with permission check
            products = Product.objects.filter(
                id__in=product_ids, 
                seller=request.user,
                approval_status='approved'  # ONLY approved products
            )
            
            if not products.exists():
                return JsonResponse({
                    'success': False, 
                    'message': 'No approved products found to update'
                })
            
            updated_count = 0
            show_count = 0
            hide_count = 0
            
            with transaction.atomic():
                for product in products:
                    if action == 'show':
                        product.status = True
                        show_count += 1
                    elif action == 'hide':
                        product.status = False
                        hide_count += 1
                    elif action == 'toggle':
                        product.status = not product.status
                        if product.status:
                            show_count += 1
                        else:
                            hide_count += 1
                    
                    product.save()
                    updated_count += 1
            
            # Create notification
            if action == 'show':
                message = f'{show_count} products made live'
            elif action == 'hide':
                message = f'{hide_count} products hidden'
            else:
                message = f'{show_count} products made live, {hide_count} products hidden'
            
            create_notification(
                user=request.user,
                notification_type='system',
                title='Bulk Visibility Update!',
                message=f'Visibility updated: {message}.',
                icon='fa-eye',
                color='info',
                url='/my-selling-items/'
            )
            
            return JsonResponse({
                'success': True, 
                'updated_count': updated_count,
                'show_count': show_count,
                'hide_count': hide_count,
                'message': f'Visibility updated for {updated_count} products'
            })
            
        except Exception as e:
            print(f"Error in bulk visibility update: {e}")
            return JsonResponse({
                'success': False, 
                'message': 'Error updating visibility'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def bulk_delete_products(request):
    """AJAX endpoint for bulk product deletion"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_ids = data.get('products', [])
            
            # Get products belonging to current user
            products = Product.objects.filter(id__in=product_ids, seller=request.user)
            
            if not products.exists():
                return JsonResponse({
                    'success': False, 
                    'message': 'No products found to delete'
                })
            
            deleted_count = products.count()
            product_names = [p.name for p in products[:3]]  # Get first 3 names
            
            # Delete the products
            with transaction.atomic():
                products.delete()
            
            # Create notification
            if deleted_count == 1:
                message = f'"{product_names[0]}" has been deleted'
            elif deleted_count <= 3:
                message = f'{", ".join(product_names)} have been deleted'
            else:
                message = f'{deleted_count} products have been deleted'
            
            create_notification(
                user=request.user,
                notification_type='system',
                title='Products Deleted!',
                message=message,
                icon='fa-trash',
                color='info',
                url='/my-selling-items/'
            )
            
            return JsonResponse({
                'success': True, 
                'deleted_count': deleted_count,
                'message': f'{deleted_count} products deleted successfully'
            })
            
        except Exception as e:
            print(f"Error in bulk delete: {e}")
            return JsonResponse({
                'success': False, 
                'message': 'Error deleting products'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# QR PAYMENT MANAGEMENT

@login_required
def update_qr(request):
    """Update QR payment code - for sellers and pending sellers"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    # Allow access for approved sellers and pending sellers who want to update their QR
    if profile.seller_status not in ['approved', 'pending']:
        messages.error(request, 'You need to apply as a seller first to manage QR codes.')
        return redirect('become_seller')

    if request.method == 'POST':
        qr_payment_method = request.POST.get('qr_payment_method', '').strip()
        qr_payment_info = request.POST.get('qr_payment_info', '').strip()
        payment_qr_code = request.FILES.get('payment_qr_code')

        # Validation
        if not qr_payment_method:
            messages.error(request, 'Please select a payment method for your QR code.')
            return render(request, 'users/update_qr.html', {'profile': profile})
            
        if not qr_payment_info:
            messages.error(request, 'Please provide payment information (phone number, account name, etc.).')
            return render(request, 'users/update_qr.html', {'profile': profile})

        # Update profile fields
        profile.qr_payment_method = qr_payment_method
        profile.qr_payment_info = qr_payment_info

        # Only update QR code if new file uploaded
        if payment_qr_code:
            # Validate QR code file
            if payment_qr_code.size > 5 * 1024 * 1024:  # 5MB limit
                messages.error(request, 'QR code image must be less than 5MB.')
                return render(request, 'users/update_qr.html', {'profile': profile})
            
            profile.payment_qr_code = payment_qr_code

        profile.save()

        messages.success(request, 'QR payment information updated successfully!')
        return redirect('dashboard')
    
    return render(request, 'users/update_qr.html', {'profile': profile})

@login_required
def remove_qr(request):
    """Remove QR payment code - for sellers who want to disable QR payments"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        messages.error(request, 'Profile not found.')
        return redirect('dashboard')

    # Only allow sellers to remove QR codes
    if profile.seller_status not in ['approved', 'pending']:
        messages.error(request, 'You need to be a seller to manage QR codes.')
        return redirect('dashboard')

    if request.method == 'POST':
        # Remove QR code but keep other seller info
        if profile.payment_qr_code:
            profile.payment_qr_code.delete()  # Delete the file
            profile.payment_qr_code = None
            profile.save()
            messages.success(request, '🗑️ QR code removed successfully! QR payments are now disabled.')
        else:
            messages.info(request, 'No QR code found to remove.')
        
        return redirect('update_qr')
    
    # If not POST, redirect back to update_qr page
    return redirect('update_qr')

# NOTIFICATION SYSTEM - FIXED AND CLEANED

@require_POST
@login_required
def clear_messages(request):
    """🛡️ BULLETPROOF: Clear notifications ONLY - NEVER touch chat data"""
    try:
        print(f"🔄 Clear messages called by {request.user.username}")
        
        # 1. Clear Django flash messages safely
        storage = messages.get_messages(request)
        list(storage)  # Consume all messages safely
        print("✅ Django flash messages cleared")
        
        # 2. Clear ONLY notifications - with explicit chat protection
        notifications_cleared = 0
        try:
            notifications_cleared = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            print(f"✅ Marked {notifications_cleared} notifications as read")
        except Exception as e:
            print(f"⚠️ Error clearing notifications: {e}")
        
        # 3. 🛡️ VERIFY chat data is untouched
        chat_rooms_count = ChatRoom.objects.filter(participants=request.user).count()
        chat_messages_count = ChatMessage.objects.filter(chat_room__participants=request.user).count()
        print(f"🛡️ Chat protection verified: {chat_rooms_count} rooms, {chat_messages_count} messages")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Cleared {notifications_cleared} notifications',
            'notifications_cleared': notifications_cleared,
            'chat_preserved': {
                'rooms': chat_rooms_count,
                'messages': chat_messages_count
            }
        })
        
    except Exception as e:
        print(f"❌ Clear messages error: {e}")
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        })


@login_required
def mark_notification_read(request, notification_id):
    """Mark single notification as read via AJAX"""
    if request.method == 'POST':
        try:
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
            notification.mark_as_read()
            
            return JsonResponse({
                'success': True,
                'message': 'Notification marked as read'
            })
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            return JsonResponse({
                'success': False, 
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False, 
        'error': 'Invalid request method'
    })

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read via AJAX"""
    if request.method == 'POST':
        try:
            updated_count = Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
            
            return JsonResponse({
                'success': True, 
                'message': f'Marked {updated_count} notifications as read',
                'updated_count': updated_count
            })
        except Exception as e:
            print(f"Error marking all notifications as read: {e}")
            return JsonResponse({
                'success': False, 
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False, 
        'error': 'Invalid request method'
    })

@login_required
def get_notifications_ajax(request):
    """Get notifications via AJAX for real-time updates"""
    try:
        notifications = get_recent_notifications(request.user, limit=10)
        total_notifications = get_unread_notification_count(request.user)
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'icon': notification.icon,
                'color': notification.color,
                'url': notification.url,
                'is_read': notification.is_read,
                'created_at': notification.get_time_display(),
            })
        
        return JsonResponse({
            'notifications': notifications_data,
            'total_count': total_notifications,
            'success': True
        })
    except Exception as e:
        print(f"Error getting notifications: {e}")
        return JsonResponse({
            'notifications': [],
            'total_count': 0,
            'success': False,
            'error': str(e)
        })

@require_POST
@login_required
def clear_notifications_only(request):
    """Clear ONLY database notifications"""
    try:
        updated_count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({
            'status': 'success', 
            'message': f'Cleared {updated_count} notifications',
            'notifications_cleared': updated_count
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@require_POST
@login_required  
def clear_django_messages_only(request):
    """Clear ONLY Django flash messages, not notifications"""
    try:
        # Get the Django messages framework storage
        storage = messages.get_messages(request)
        
        # Only clear Django flash messages, not chat messages or notifications
        list(storage)  # This consumes the Django flash messages safely
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Flash messages cleared',
            'action': 'django_messages_only'
        })
    
    except Exception as e:
        print(f"Error clearing Django messages: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})
    

@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist via AJAX"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            
            # Check if already in wishlist
            wishlist_item, created = Wishlist.objects.get_or_create(
                user=request.user,
                product=product
            )
            
            if created:
                # Create notification for adding to wishlist
                create_notification(
                    user=request.user,
                    notification_type='system',
                    title='Added to Wishlist!',
                    message=f'"{product.name}" has been added to your wishlist.',
                    icon='fa-heart',
                    color='info',
                    url='/wishlist/'
                )
                
                return JsonResponse({
                    'success': True,
                    'added': True,
                    'message': 'Added to wishlist!',
                    'wishlist_count': Wishlist.get_wishlist_count(request.user)
                })
            else:
                return JsonResponse({
                    'success': True,
                    'added': False,
                    'message': 'Already in wishlist!'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist via AJAX"""
    if request.method == 'POST':
        try:
            wishlist_item = get_object_or_404(
                Wishlist, 
                user=request.user, 
                product_id=product_id
            )
            product_name = wishlist_item.product.name
            wishlist_item.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'"{product_name}" removed from wishlist!',
                'wishlist_count': Wishlist.get_wishlist_count(request.user)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def wishlist_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product__category', 'product__seller')
    wishlist_count = wishlist_items.count()
    
    # Get user's cart items to check what's already in cart
    user_cart_items = {}
    if request.user.is_authenticated:
        try:
            from cart.models import Cart, CartItem  # Adjust import based on your app structure
            cart = Cart.objects.get(user=request.user)
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            user_cart_items = {item.product.id: item.quantity for item in cart_items}
        except Cart.DoesNotExist:
            user_cart_items = {}
    
    # Prepare wishlist items with additional context
    enriched_wishlist_items = []
    for item in wishlist_items:
        product = item.product
        
        # Check if already in cart
        in_cart = product.id in user_cart_items
        cart_quantity = user_cart_items.get(product.id, 0)
        
        # Check stock status
        is_out_of_stock = product.stock <= 0
        is_low_stock = 0 < product.stock <= 5
        
        # Check if user owns this product
        is_own_product = product.seller == request.user
        
        enriched_item = {
            'wishlist_item': item,
            'product': product,
            'in_cart': in_cart,
            'cart_quantity': cart_quantity,
            'is_out_of_stock': is_out_of_stock,
            'is_low_stock': is_low_stock,
            'is_own_product': is_own_product,
            'available_stock': product.stock,
        }
        enriched_wishlist_items.append(enriched_item)
    
    context = {
        'wishlist_items': enriched_wishlist_items,
        'wishlist_count': wishlist_count,
    }
    
    return render(request, 'users/wishlist.html', context)

@login_required
def toggle_wishlist(request, product_id):
    """Toggle product in wishlist (add if not exists, remove if exists)"""
    if request.method == 'POST':
        try:
            from products.models import Product
            product = get_object_or_404(Product, id=product_id)
            
            wishlist_item = Wishlist.objects.filter(
                user=request.user,
                product=product
            ).first()
            
            if wishlist_item:
                # Remove from wishlist
                product_name = wishlist_item.product.name
                wishlist_item.delete()
                in_wishlist = False
                message = f'"{product_name}" removed from wishlist!'
            else:
                # Add to wishlist
                Wishlist.objects.create(user=request.user, product=product)
                in_wishlist = True
                message = f'"{product.name}" added to wishlist!'
                
                # Create notification
                create_notification(
                    user=request.user,
                    notification_type='system',
                    title='Added to Wishlist!',
                    message=f'"{product.name}" has been added to your wishlist.',
                    icon='fa-heart',
                    color='info',
                    url='/wishlist/'
                )
            
            return JsonResponse({
                'success': True,
                'in_wishlist': in_wishlist,
                'message': message,
                'wishlist_count': Wishlist.get_wishlist_count(request.user)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
@require_POST
def clear_all_wishlist(request):
    """Clear all items from user's wishlist"""
    try:
        # Get user's wishlist items
        wishlist_items = Wishlist.objects.filter(user=request.user)
        items_count = wishlist_items.count()
        
        if items_count > 0:
            # Delete all wishlist items
            wishlist_items.delete()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully cleared {items_count} items from your wishlist!',
                    'wishlist_count': 0
                })
            else:
                messages.success(request, f'Successfully cleared {items_count} items from your wishlist!')
                return redirect('users:wishlist')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Your wishlist is already empty!'
                })
            else:
                messages.info(request, 'Your wishlist is already empty!')
                return redirect('users:wishlist')
                
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'An error occurred while clearing your wishlist.'
            }, status=500)
        else:
            messages.error(request, 'An error occurred while clearing your wishlist.')
            return redirect('users:wishlist')
        

# for customer received orders from seller
@login_required
def customer_received_orders(request):
    """Display items that the customer has received (delivered orders) - FOR CUSTOMERS"""
    try:
        # Get all order items for orders that are delivered/completed for this user
        from orders.models import OrderItem
        
        received_items = OrderItem.objects.filter(
            order__user=request.user,
            ordered=True,
            order__order_status__in=['delivered', 'completed']
        ).select_related(
            'product', 'order', 'seller', 'order__user', 'product__category'
        ).prefetch_related(
            'variations__variation_type',
            'variations__variation_option'
        ).order_by('-order__delivered_date', '-order__created_at')
        
        # Get unique orders count
        unique_orders = received_items.values('order').distinct()
        unique_orders_count = unique_orders.count()
        
        # Get reviewed product IDs to show "Reviewed" status
        reviewed_product_ids = []
        try:
            # Check if you have a Review model
            from products.models import Review
            reviews = Review.objects.filter(user=request.user).values_list('product_id', flat=True)
            reviewed_product_ids = list(reviews)
        except (ImportError, AttributeError):
            # If no review model, we'll skip this for now
            reviewed_product_ids = []
        
        # Count items pending review
        pending_reviews_count = received_items.exclude(product_id__in=reviewed_product_ids).count()
        
        context = {
            'received_items': received_items,
            'unique_orders_count': unique_orders_count,
            'pending_reviews_count': pending_reviews_count,
            'reviewed_product_ids': reviewed_product_ids,
        }
        return render(request, 'users/customer_received_orders.html', context)
        
    except Exception as e:
        print(f"Error in customer_received_orders view: {e}")
        messages.error(request, 'Error loading received orders.')
        return redirect('dashboard')
    

# for seller to update order status
@login_required
def update_order_status(request, order_id):
    """AJAX endpoint for sellers to update order status - FIXED"""
    print(f"🔄 Order status update - Order ID: {order_id}, User: {request.user.username}")
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            print(f"📝 Requested status: {new_status}")
            
            # FIX: Use .distinct() to avoid duplicate results
            try:
                order = Order.objects.filter(
                    id=order_id,
                    items__seller=request.user
                ).distinct().first()
                
                if not order:
                    return JsonResponse({
                        'success': False,
                        'message': 'Order not found or access denied'
                    })
                    
                print(f"✅ Order found: #{order.id}, Current status: {order.order_status}")
                
            except Exception as e:
                print(f"❌ Error finding order: {e}")
                return JsonResponse({
                    'success': False,
                    'message': 'Error finding order'
                })
            
            # Verify seller permission
            profile = request.user.profile
            if profile.seller_status != 'approved':
                return JsonResponse({
                    'success': False,
                    'message': 'Only approved sellers can update order status'
                })
            
            # FIX: Correct status transitions
            valid_transitions = {
                'pending': ['confirmed'],           # Can only go to confirmed
                'confirmed': ['processing'],        # Can only go to processing  
                'processing': ['shipped'],          # Can only go to shipped
                'shipped': ['delivered'],           # Can only go to delivered
                'delivered': ['completed'],         # Can only go to completed
                'completed': [],                    # Final status
                'cancelled': []                     # Final status
            }
            
            current_status = order.order_status
            allowed_transitions = valid_transitions.get(current_status, [])
            
            print(f"🔄 Status check: {current_status} → {new_status}")
            print(f"✅ Allowed transitions: {allowed_transitions}")
            
            if new_status not in allowed_transitions:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot change from {current_status} to {new_status}. Next allowed status: {allowed_transitions}'
                })
            
            # Update order status
            old_status = order.order_status
            order.order_status = new_status
            order.status = new_status.title()
            
            # Set timestamps
            if new_status == 'confirmed':
                order.confirmed_at = timezone.now()
            elif new_status == 'processing':
                order.processing_at = timezone.now()
            elif new_status == 'delivered':
                order.delivered_date = timezone.now()
            elif new_status == 'completed':
                order.completed_date = timezone.now()
            
            order.save()
            print(f"✅ Order updated: {old_status} → {new_status}")
            
            # Create notification for customer
            try:
                status_messages = {
                    'confirmed': 'Your order has been confirmed by the seller.',
                    'processing': 'Your order is now being prepared for shipping.',
                    'shipped': 'Your order has been shipped!',
                    'delivered': 'Your order has been delivered.',
                    'completed': 'Your order is complete. Thank you!'
                }
                
                create_notification(
                    user=order.user,
                    notification_type='order',
                    title=f'Order {new_status.title()}!',
                    message=status_messages.get(new_status, f'Order status updated to {new_status}'),
                    icon='fa-box',
                    color='success',
                    url='/orders/my-orders/'
                )
            except Exception as e:
                print(f"⚠️ Notification failed: {e}")
            
            return JsonResponse({
                'success': True,
                'message': f'Order status updated to {new_status.title()}',
                'new_status': new_status
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error updating status: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def mark_as_shipped(request, order_id):
    """AJAX endpoint for sellers to mark order as shipped with tracking"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tracking_number = data.get('tracking_number', '').strip()
            shipping_date = data.get('shipping_date')
            notes = data.get('notes', '').strip()
            
            # Get order where current user is the seller
            order = get_object_or_404(Order, 
                id=order_id, 
                items__seller=request.user,
                order_status='processing'  # Only processing orders can be shipped
            )
            
            # Verify seller permission
            profile = request.user.profile
            if profile.seller_status != 'approved':
                return JsonResponse({
                    'success': False,
                    'message': 'Only approved sellers can update shipping'
                })
            
            if not tracking_number:
                return JsonResponse({
                    'success': False,
                    'message': 'Tracking number is required'
                })
            
            # Update order with shipping info (using your existing fields)
            order.order_status = 'shipped'
            order.status = 'Shipped'
            order.tracking_number = tracking_number
            order.shipped_date = timezone.now() if not shipping_date else shipping_date
            order.shipping_notes = notes  # This is the new field we added
            order.save()
            
            # Create notification for customer
            create_notification(
                user=order.user,
                notification_type='order',
                title='Order Shipped! 🚚',
                message=f'Order #{order.order_number} has been shipped! Tracking: {tracking_number}',
                icon='fa-truck',
                color='info',
                url='/orders/my-orders/'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Order marked as shipped with tracking: {tracking_number}',
                'tracking_number': tracking_number
            })
            
        except Exception as e:
            print(f"Error marking as shipped: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Error updating shipping status'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def order_details_modal(request, order_id):
    """Load order details in modal for sellers"""
    try:
        # Get order where current user is the seller
        order = get_object_or_404(Order, 
            id=order_id, 
            items__seller=request.user
        )
        
        # Get order items for this seller only
        order_items = OrderItem.objects.filter(
            order=order,
            seller=request.user,
            ordered=True
        ).select_related('product').prefetch_related('variations')
        
        context = {
            'order': order,
            'order_items': order_items,
        }
        return render(request, 'users/order_details_modal.html', context)
        
    except Exception as e:
        print(f"Error loading order details: {e}")
        # Create a simple error response instead of trying to render non-existent template
        return JsonResponse({
            'error': True,
            'message': 'Error loading order details'
        })


def user_logout(request):
    """Enhanced logout"""
    # Clear all Django flash messages before logout
    storage = messages.get_messages(request)
    list(storage)  # Clear messages safely
    
    # Logout user
    logout(request)
    
    messages.success(request, 'You have been logged out successfully.')
    
    return redirect('home')