from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile
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
from django.http import JsonResponse
from orders.views import send_order_confirmation_email


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

    # Add pending QR count for sidebar (NEW)
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
        
        # Add QR payment notifications to recent activities (NEW)
        if pending_qr_count > 0:
            recent_activities.append({
                'message': f'{pending_qr_count} QR payment(s) awaiting verification',
                'created_at': timezone.now(),  # Make sure to import timezone
                'icon': 'fa-qrcode',
                'badge_color': 'warning'
            })
    
    # Sort activities by date
    recent_activities.sort(key=lambda x: x['created_at'], reverse=True)
    recent_activities = recent_activities[:5]  # Keep only 5 most recent

    # Additional stats
    context = {
        'profile': profile,
        'orders_count': orders_count,
        'received_orders_count': received_orders_count,
        'user': request.user,
        'seller_stats': seller_stats,
        'recent_activities': recent_activities,
        'wishlist_count': 0,  # You can implement this later
        'unread_messages_count': 0,  # You can implement this later
        'pending_qr_count': pending_qr_count,  # ADD THIS
    }
    return render(request, 'users/dashboard.html', context)


@login_required
def received_orders(request):
    """QR Payment verification page for sellers"""
    profile = request.user.profile
    
    # Only approved sellers can access
    if profile.seller_status != 'approved':
        messages.error(request, 'You need to be an approved seller to access this page.')
        return redirect('dashboard')

    # Handle verification actions
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        action = request.POST.get('action')
        
        try:
            order = get_object_or_404(Order, 
                id=order_id, 
                items__seller=request.user,
                payment_method='QR Payment',
                payment_status='pending_verification'
            )
            
            if action == 'verify':
                order.payment_status = 'completed'
                order.status = 'Confirmed'
                order.order_status = 'confirmed'
                order.qr_payment_verified_by = request.user
                order.qr_payment_verified_at = timezone.now()
                order.save()
                
                # Send confirmation email
                send_order_confirmation_email(order)
                messages.success(request, f'✅ Payment verified for Order #{order.order_number}. Customer notified!')
                
            elif action == 'reject':
                order.payment_status = 'rejected'
                order.status = 'Payment Rejected'
                order.order_status = 'cancelled'
                order.save()
                messages.warning(request, f'❌ Payment rejected for Order #{order.order_number}')
                
        except Order.DoesNotExist:
            messages.error(request, 'Order not found or unauthorized access.')
        except Exception as e:
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
    return render(request, 'users/received_orders.html', context)


# NEW VIEW: For sellers to see orders they received from customers
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
    return render(request, 'users/received_orders.html', context)


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
    """Display seller's products - ONLY if approved seller"""
    profile = request.user.profile

    # Gate: Only approved sellers can access
    if profile.seller_status != 'approved':
        messages.error(request, 'You need to be an approved seller to access this page.')
        return redirect('dashboard')

    # Get seller's products (all statuses for seller to see)
    products = Product.objects.filter(seller=request.user).order_by('-created_at')

    context = {
        'products': products,
        'total_products': products.count(),
        'pending_products': products.filter(approval_status='pending').count(),
        'approved_products': products.filter(approval_status='approved').count(),
        'rejected_products': products.filter(approval_status='rejected').count(),
    }
    return render(request, 'users/my_selling_items.html', context)


@login_required
def received_orders(request):
    context = {}
    return render(request, 'users/received_orders.html', context)


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

            # NEW FIELDS FOR THRIFT/SALE
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
                # NEW FIELDS
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
            order = get_object_or_404(Order, 
                id=order_id, 
                items__seller=request.user,
                payment_method='QR Payment',
                payment_status='pending_verification'
            )
            
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
                
                if stock_reverted and email_sent:
                    messages.warning(request, f'❌ Payment rejected for Order #{order.order_number}. Stock reverted and customer notified via email.')
                elif stock_reverted:
                    messages.warning(request, f'❌ Payment rejected for Order #{order.order_number}. Stock reverted. (Email notification failed)')
                elif email_sent:
                    messages.warning(request, f'❌ Payment rejected for Order #{order.order_number}. Customer notified. (Stock reversion failed)')
                else:
                    messages.error(request, f'❌ Payment rejected for Order #{order.order_number}. WARNING: Stock reversion and email notification failed!')
                
        except Order.DoesNotExist:
            messages.error(request, 'Order not found or unauthorized access.')
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


@login_required
def chat_list(request):
    """Display all chat rooms for current user"""
    chat_rooms = ChatRoom.objects.filter(
        participants=request.user
    ).prefetch_related('participants', 'messages').order_by('-updated_at')
    
    context = {
        'chat_rooms': chat_rooms,
    }
    return render(request, 'users/chat_list.html', context)

@login_required
def chat_detail(request, chat_id):
    """Display specific chat room"""
    chat_room = get_object_or_404(ChatRoom, id=chat_id, participants=request.user)
    
    # Mark messages as read
    ChatMessage.objects.filter(
        chat_room=chat_room,
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)
    
    messages = chat_room.messages.all()
    other_participant = chat_room.get_other_participant(request.user)
    
    context = {
        'chat_room': chat_room,
        'messages': messages,
        'other_participant': other_participant,
    }
    return render(request, 'users/chat_detail.html', context)

@login_required
def start_chat_with_user(request, username):
    """Start or continue chat with specific user"""
    other_user = get_object_or_404(User, username=username)
    
    # Check if chat already exists
    chat_room = ChatRoom.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if not chat_room:
        # Create new chat room
        chat_room = ChatRoom.objects.create()
        chat_room.participants.add(request.user, other_user)
    
    return redirect('chat_detail', chat_id=chat_room.id)

@login_required
def send_message(request):
    """AJAX endpoint to send message"""
    if request.method == 'POST':
        chat_id = request.POST.get('chat_id')
        message_text = request.POST.get('message')
        
        if chat_id and message_text:
            chat_room = get_object_or_404(ChatRoom, id=chat_id, participants=request.user)
            
            message = ChatMessage.objects.create(
                chat_room=chat_room,
                sender=request.user,
                message=message_text
            )
            
            # Update chat room timestamp
            chat_room.updated_at = timezone.now()
            chat_room.save()
            
            return JsonResponse({
                'success': True,
                'message': {
                    'id': message.id,
                    'message': message.message,
                    'sender': message.sender.username,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M')
                }
            })
    
    return JsonResponse({'success': False})

@login_required
def update_product_stock(request, product_id):
    """AJAX endpoint to update product stock"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id, seller=request.user)
            data = json.loads(request.body)
            new_stock = int(data.get('stock', 0))
            
            product.stock = max(0, new_stock)
            product.save()
            
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

@login_required
def toggle_product_status(request, product_id):
    """AJAX endpoint to toggle product live/hidden status"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id, seller=request.user)
            data = json.loads(request.body)
            
            # Only allow status change for approved products
            if product.approval_status == 'approved':
                product.status = data.get('status', False)
                product.save()
                return JsonResponse({'success': True})
            
            return JsonResponse({'success': False})
        except:
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

@login_required
def delete_product(request, product_id):
    """AJAX endpoint to delete product"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id, seller=request.user)
            product.delete()
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

@login_required
def bulk_update_stock(request):
    """AJAX endpoint for bulk stock updates"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_ids = data.get('products', [])
            action = data.get('action')
            amount = int(data.get('amount', 0))
            
            products = Product.objects.filter(id__in=product_ids, seller=request.user)
            updated_count = 0
            
            for product in products:
                if action == 'set':
                    product.stock = amount
                elif action == 'add':
                    product.stock += amount
                elif action == 'subtract':
                    product.stock = max(0, product.stock - amount)
                
                product.save()
                updated_count += 1
            
            return JsonResponse({'success': True, 'updated_count': updated_count})
        except:
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})


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