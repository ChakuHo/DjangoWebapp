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

    context = {
        'profile': profile,
        'orders_count': orders_count,
        'user': request.user,
        'seller_stats': seller_stats,
    }
    return render(request, 'users/dashboard.html', context)


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
    """Apply to become a seller"""
    profile = request.user.profile

    # Check if already a seller or applied
    if profile.seller_status in ['approved', 'pending']:
        messages.info(request, f'Your seller application is {profile.seller_status}.')
        return redirect('dashboard')

    if request.method == 'POST':
        business_name = request.POST.get('business_name', '').strip()
        business_description = request.POST.get('business_description', '').strip()

        if not business_name:
            messages.error(request, 'Business name is required.')
            return render(request, 'users/become_seller.html')


        profile.business_name = business_name
        profile.business_description = business_description
        profile.seller_status = 'pending'
        profile.seller_application_date = timezone.now()
        profile.save()

        messages.success(request, 'Seller application submitted! We will review and get back to you.')
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