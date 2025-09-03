from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Case, When, IntegerField
from .models import Category, Product, Review, VariationOption, VariationType, ProductVariation
from django.http import Http404
from cart.models import CartItem, Cart
from cart.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from orders.models import Order, OrderItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from users.models import Wishlist
from users.views import track_product_view
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

def product(request, category_slug=None):
    """Display products with advanced filtering"""
    categories = None
    products = None

    # Base queryset
    if category_slug is not None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(
            category=categories, 
            status=True,
            admin_approved=True,
            approval_status='approved'
        )
    else:
        products = Product.objects.filter(
            status=True,
            admin_approved=True,
            approval_status='approved'
        )

    # Apply variation filters
    selected_variations = []
    variations_param = request.GET.get('variations')
    if variations_param:
        variation_ids = [int(x) for x in variations_param.split(',') if x.isdigit()]
        selected_variations = variation_ids
        
        if variation_ids:
            for var_id in variation_ids:
                products = products.filter(
                    variations__variation_option_id=var_id,
                    variations__is_active=True
                ).distinct()

    # Apply price filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        products = products.filter(price__gte=min_price)

    if max_price:
        products = products.filter(price__lte=max_price)

    # Apply product type filter
    product_type = request.GET.get('product_type')
    if product_type in ['new', 'thrift', 'refurbished']:
        products = products.filter(product_type=product_type)

    # Apply sale filter
    on_sale = request.GET.get('on_sale')
    if on_sale == 'true':
        products = products.filter(is_on_sale=True)

    # Apply condition filter (for thrift products)
    condition = request.GET.get('condition')
    if condition in ['excellent', 'good', 'fair', 'poor']:
        products = products.filter(condition=condition)

    # Apply sorting
    sort_by = request.GET.get('sort', '-created_at')
    
    if sort_by == 'refurbished_first':
        products = products.annotate(
            is_refurbished=Case(
                When(product_type='refurbished', then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('is_refurbished', '-created_at')
    elif sort_by == 'discounted_first':
        products = products.annotate(
            has_discount=Case(
                When(is_on_sale=True, then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('has_discount', '-created_at')
    elif sort_by in ['name', '-name', 'price', '-price', '-created_at']:
        products = products.order_by(sort_by)

    # Get variation types for filtering
    variation_types = VariationType.objects.filter(is_active=True).prefetch_related('options')

    # Get all categories for sidebar
    cats = Category.objects.filter(status=True)

    # Get cart items
    if request.user.is_authenticated:
        in_cart_ids = list(
            CartItem.objects.filter(cart__user=request.user)
            .values_list('product_id', flat=True)
        )
    else:
        in_cart_ids = list(
            CartItem.objects.filter(cart__cart_id=_cart_id(request))
            .values_list('product_id', flat=True)
        )

    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)

    context = {
        'products': paged_products,
        'product_count': products.count(),
        'categories': cats,
        'links': cats,
        'in_cart_ids': in_cart_ids,
        'current_category': categories,
        'variation_types': variation_types,
        'selected_variations': selected_variations,
        'user_wishlist_ids': list(request.user.wishlist_items.values_list('product_id', flat=True)) if request.user.is_authenticated else [],
    }
    return render(request, 'products/products.html', context)

def sale_products(request):
    """Display only discounted/sale products"""
    products = Product.objects.filter(
        status=True,
        admin_approved=True,
        approval_status='approved',
        is_on_sale=True
    )

    # Apply same filtering and sorting as main products view
    # Apply variation filters
    selected_variations = []
    variations_param = request.GET.get('variations')
    if variations_param:
        variation_ids = [int(x) for x in variations_param.split(',') if x.isdigit()]
        selected_variations = variation_ids
        
        if variation_ids:
            for var_id in variation_ids:
                products = products.filter(
                    variations__variation_option_id=var_id,
                    variations__is_active=True
                ).distinct()

    # Apply price filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        products = products.filter(price__gte=min_price)

    if max_price:
        products = products.filter(price__lte=max_price)

    # Apply condition filter
    condition = request.GET.get('condition')
    if condition in ['excellent', 'good', 'fair', 'poor']:
        products = products.filter(condition=condition)

    # Apply sorting
    sort_by = request.GET.get('sort', '-created_at')
    
    if sort_by == 'refurbished_first':
        products = products.annotate(
            is_refurbished=Case(
                When(product_type='refurbished', then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('is_refurbished', '-created_at')
    elif sort_by == 'discounted_first':
        products = products.annotate(
            has_discount=Case(
                When(is_on_sale=True, then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('has_discount', '-created_at')
    elif sort_by in ['name', '-name', 'price', '-price', '-created_at']:
        products = products.order_by(sort_by)

    cats = Category.objects.filter(status=True)
    variation_types = VariationType.objects.filter(is_active=True).prefetch_related('options')

    if request.user.is_authenticated:
        in_cart_ids = list(
            CartItem.objects.filter(cart__user=request.user)
            .values_list('product_id', flat=True)
        )
    else:
        in_cart_ids = list(
            CartItem.objects.filter(cart__cart_id=_cart_id(request))
            .values_list('product_id', flat=True)
        )

    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)

    context = {
        'products': paged_products,
        'product_count': products.count(),
        'categories': cats,
        'links': cats,
        'in_cart_ids': in_cart_ids,
        'variation_types': variation_types,
        'selected_variations': selected_variations,
        'page_title': 'Sale Products',
        'is_sale_page': True,
    }
    return render(request, 'products/products.html', context)

def thrift_products(request, category_slug=None):
    """Display only thrift/used products"""
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(
            category=category,
            status=True,
            admin_approved=True,
            approval_status='approved',
            product_type='thrift'
        )
    else:
        category = None
        products = Product.objects.filter(
            status=True,
            admin_approved=True,
            approval_status='approved',
            product_type='thrift'
        )

    # Apply same filtering and sorting as main products view
    # Apply variation filters
    selected_variations = []
    variations_param = request.GET.get('variations')
    if variations_param:
        variation_ids = [int(x) for x in variations_param.split(',') if x.isdigit()]
        selected_variations = variation_ids
        
        if variation_ids:
            for var_id in variation_ids:
                products = products.filter(
                    variations__variation_option_id=var_id,
                    variations__is_active=True
                ).distinct()

    # Apply price filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        products = products.filter(price__gte=min_price)

    if max_price:
        products = products.filter(price__lte=max_price)

    # Apply sale filter
    on_sale = request.GET.get('on_sale')
    if on_sale == 'true':
        products = products.filter(is_on_sale=True)

    # Apply condition filter
    condition = request.GET.get('condition')
    if condition in ['excellent', 'good', 'fair', 'poor']:
        products = products.filter(condition=condition)

    # Apply sorting
    sort_by = request.GET.get('sort', '-created_at')
    
    if sort_by == 'refurbished_first':
        products = products.annotate(
            is_refurbished=Case(
                When(product_type='refurbished', then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('is_refurbished', '-created_at')
    elif sort_by == 'discounted_first':
        products = products.annotate(
            has_discount=Case(
                When(is_on_sale=True, then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('has_discount', '-created_at')
    elif sort_by in ['name', '-name', 'price', '-price', '-created_at']:
        products = products.order_by(sort_by)

    cats = Category.objects.filter(status=True)
    variation_types = VariationType.objects.filter(is_active=True).prefetch_related('options')

    if request.user.is_authenticated:
        in_cart_ids = list(
            CartItem.objects.filter(cart__user=request.user)
            .values_list('product_id', flat=True)
        )
    else:
        in_cart_ids = list(
            CartItem.objects.filter(cart__cart_id=_cart_id(request))
            .values_list('product_id', flat=True)
        )

    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)

    context = {
        'products': paged_products,
        'product_count': products.count(),
        'categories': cats,
        'links': cats,
        'in_cart_ids': in_cart_ids,
        'current_category': category,
        'variation_types': variation_types,
        'selected_variations': selected_variations,
        'page_title': 'Thrift Products' + (f' - {category.category_name}' if category else ''),
        'is_thrift_page': True,
    }
    return render(request, 'products/products.html', context)

def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
    except Product.DoesNotExist:
        raise Http404("Product not found")

    # Check if product is in user's cart
    in_cart = False
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(product=single_product, cart=cart)
            in_cart = True
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            in_cart = False

    # Get user's wishlist product IDs
    user_wishlist_ids = []
    if request.user.is_authenticated:
        user_wishlist_ids = list(
            request.user.wishlist_items.values_list('product_id', flat=True)
        )

    reviews = Review.objects.filter(product=single_product, status=True).order_by('-created_at')

    # Check if user can review and has already reviewed
    user_can_review = False
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_can_review = OrderItem.objects.filter(
            order__user=request.user,
            product=single_product,
            order__status='Delivered'
        ).exists()
        
        user_has_reviewed = Review.objects.filter(
            user=request.user,
            product=single_product
        ).exists()

    # Build variation data for smart filtering
    variation_images_dict = {}
    variation_stock = {}
    available_combinations = {}
    
    if single_product.has_variations():
        # Get all active variations for this product
        product_variations = single_product.variations.filter(is_active=True)
        
        # Group variations by type to build combinations
        variations_by_type = {}
        for pv in product_variations:
            var_type = pv.variation_type.name
            if var_type not in variations_by_type:
                variations_by_type[var_type] = []
            
            variations_by_type[var_type].append({
                'option_id': pv.variation_option.id,
                'value': pv.variation_option.value,
                'stock': pv.stock_quantity,
                'price_adjustment': float(pv.price_adjustment),
                'variation_obj': pv
            })
            
            # Build individual stock data
            option_key = f"{var_type}:{pv.variation_option.id}"
            variation_stock[option_key] = {
                'stock': pv.stock_quantity,
                'price_adjustment': float(pv.price_adjustment),
                'type': var_type,
                'value': pv.variation_option.value
            }
            
            # Get variation images
            option_id = str(pv.variation_option.id)
            if option_id not in variation_images_dict:
                variation_images_dict[option_id] = []
            
            images = pv.get_all_images()
            for image in images:
                if hasattr(image, 'url'):
                    variation_images_dict[option_id].append(image.url)

        # Build actual combinations for smart filtering
        if len(variations_by_type) > 1:
            # Multi-variation product (e.g., Color + Size)
            variation_types = list(variations_by_type.keys())
            
            if len(variation_types) == 2:
                # Two variation types (most common case)
                type1, type2 = variation_types
                for var1 in variations_by_type[type1]:
                    for var2 in variations_by_type[type2]:
                        # Check if this combination actually exists and has stock
                        combination_stock = min(var1['stock'], var2['stock'])
                        if combination_stock > 0:
                            combination_key = f"{type1}:{var1['option_id']}|{type2}:{var2['option_id']}"
                            available_combinations[combination_key] = {
                                type1: str(var1['option_id']),
                                type2: str(var2['option_id']),
                                'stock': combination_stock,
                                'price_adjustment': var1['price_adjustment'] + var2['price_adjustment']
                            }
            
            # Handle 3+ variation types if needed
            elif len(variation_types) == 3:
                type1, type2, type3 = variation_types
                for var1 in variations_by_type[type1]:
                    for var2 in variations_by_type[type2]:
                        for var3 in variations_by_type[type3]:
                            combination_stock = min(var1['stock'], var2['stock'], var3['stock'])
                            if combination_stock > 0:
                                combination_key = f"{type1}:{var1['option_id']}|{type2}:{var2['option_id']}|{type3}:{var3['option_id']}"
                                available_combinations[combination_key] = {
                                    type1: str(var1['option_id']),
                                    type2: str(var2['option_id']),
                                    type3: str(var3['option_id']),
                                    'stock': combination_stock,
                                    'price_adjustment': var1['price_adjustment'] + var2['price_adjustment'] + var3['price_adjustment']
                                }
        else:
            # Single variation type (e.g., only Color or only Size)
            for var_type, variations in variations_by_type.items():
                for var in variations:
                    if var['stock'] > 0:
                        combination_key = f"{var_type}:{var['option_id']}"
                        available_combinations[combination_key] = {
                            var_type: str(var['option_id']),
                            'stock': var['stock'],
                            'price_adjustment': var['price_adjustment']
                        }

    # Seller information
    seller_product_count = 0
    if single_product.seller:
        seller_product_count = Product.objects.filter(
            seller=single_product.seller,
            status=True  
        ).count()

    context = {
        'single_product': single_product,
        'product': single_product,  
        'in_cart': in_cart,
        'user_wishlist_ids': user_wishlist_ids,
        'reviews': reviews,
        'user_can_review': user_can_review,
        'user_has_reviewed': user_has_reviewed,
        'variation_images_json': json.dumps(variation_images_dict),
        'variation_stock_json': json.dumps(variation_stock),
        'available_combinations_json': json.dumps(available_combinations),
        'seller_product_count': seller_product_count,
    }

    return render(request, 'products/details.html', context)

def generate_search_variations(keyword):
    """
    Generate all possible search variations for a keyword
    This handles spaces, hyphens, and common variations
    """
    if not keyword:
        return []

    keyword = keyword.lower().strip()
    variations = set([keyword]) 

    # Basic variations
    variations.add(keyword.replace(' ', ''))      # "t shirt" -> "tshirt"
    variations.add(keyword.replace('-', ''))      # "t-shirt" -> "tshirt"
    variations.add(keyword.replace('_', ''))      # "t_shirt" -> "tshirt"
    variations.add(keyword.replace(' ', '-'))     # "t shirt" -> "t-shirt"
    variations.add(keyword.replace(' ', '_'))     # "t shirt" -> "t_shirt"
    variations.add(keyword.replace('-', ' '))     # "t-shirt" -> "t shirt"
    variations.add(keyword.replace('_', ' '))     # "t_shirt" -> "t shirt"

    #  variations with different separators
    if ' ' in keyword:
        # If search has spaces, also try with hyphens and underscores
        variations.add(keyword.replace(' ', '-'))
        variations.add(keyword.replace(' ', '_'))

    if '-' in keyword:
        # If search has hyphens, also try with spaces and underscores
        variations.add(keyword.replace('-', ' '))
        variations.add(keyword.replace('-', '_'))

    if '_' in keyword:
        # If search has underscores, also try with spaces and hyphens
        variations.add(keyword.replace('_', ' '))
        variations.add(keyword.replace('_', '-'))

    # variations for common cases
    advanced_variations = set()
    for var in variations:
        #  single character separations (for cases like "tshirt" -> "t shirt")
        if len(var) > 1 and ' ' not in var and '-' not in var:
            # Try inserting space after first character: "tshirt" -> "t shirt"
            advanced_variations.add(var[0] + ' ' + var[1:])
            # Try inserting hyphen after first character: "tshirt" -> "t-shirt"
            advanced_variations.add(var[0] + '-' + var[1:])
            
            # Try inserting space after first two characters: "laptop" -> "lap top"
            if len(var) > 3:
                advanced_variations.add(var[:2] + ' ' + var[2:])
                advanced_variations.add(var[:2] + '-' + var[2:])

    variations.update(advanced_variations)

    # Remove empty strings
    variations = {v for v in variations if v.strip()}

    return list(variations)

def products_by_category(request, slug):
    """
    Alternative view for category products 
    This is just a wrapper around the main product view
    """
    return product(request, category_slug=slug)

def product_list(request):
    """
    Alternative view for all products 
    This is just a wrapper around the main product view
    """
    return product(request)

def user_can_review_product(user, product):
    """Check if user can review this product (must have completed order)"""
    if not user.is_authenticated:
        return False

    completed_orders = Order.objects.filter(
        user=user,
        items__product=product
    ).filter(
        Q(order_status__in=['completed', 'delivered']) |  
        Q(status__in=['completed', 'Completed', 'delivered', 'Delivered'])  
    )

    return completed_orders.exists()

def get_user_completed_order_for_product(user, product):
    """Get the completed order for this user and product (for linking review to order)"""

    return Order.objects.filter(
        user=user,
        items__product=product
    ).filter(
        Q(order_status__in=['completed', 'delivered']) |  
        Q(status__in=['completed', 'Completed', 'delivered', 'Delivered'])  
    ).order_by('-created_at').first()

def seller_products(request, seller_id):
    """Display all products from a specific seller"""
    seller = get_object_or_404(User, id=seller_id)

    products = Product.objects.filter(
        seller=seller, 
        status=True,
        admin_approved=True,
        approval_status='approved'  
    ).order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 9)  # Show 9 products per page
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)

    # Get all categories for sidebar
    cats = Category.objects.filter(status=True)

    # Get products already in cart
    if request.user.is_authenticated:
        in_cart_ids = list(
            CartItem.objects.filter(cart__user=request.user)
            .values_list('product_id', flat=True)
        )
    else:
        in_cart_ids = list(
            CartItem.objects.filter(cart__cart_id=_cart_id(request))
            .values_list('product_id', flat=True)
        )

    context = {
        'seller': seller,
        'products': paged_products,
        'product_count': products.count(),
        'categories': cats,
        'links': cats,
        'in_cart_ids': in_cart_ids,
        'page_title': f"Products by {seller.profile.business_name if seller.profile.business_name else seller.get_full_name() or seller.username}",
    }

    return render(request, 'products/seller_products.html', context)

@login_required
def submit_review(request, product_id):
    """Handle review submission"""
    product = get_object_or_404(Product, id=product_id)

    # CHECK PERMISSION
    if not user_can_review_product(request.user, product):
        messages.error(request, "You can only review products you have purchased and received.")
        return redirect('products:product_detail', product.category.slug, product.slug)

    # CHECK IF ALREADY REVIEWED
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.error(request, "You have already reviewed this product.")
        return redirect('products:product_detail', product.category.slug, product.slug)

    if request.method == 'POST':
        try:
            # Validate rating
            rating = request.POST.get('rating')
            if not rating or float(rating) < 1 or float(rating) > 5:
                messages.error(request, "Please provide a valid rating (1-5 stars).")
                return redirect('products:product_detail', product.category.slug, product.slug)
            
            completed_order = get_user_completed_order_for_product(request.user, product)
            
            review = Review.objects.create(
                product=product,
                user=request.user,
                subject=request.POST.get('subject', ''),
                review=request.POST.get('review', ''),
                rating=float(rating),
                ip=request.META.get('REMOTE_ADDR', ''),
                order=completed_order,  # Link to order
                verified_purchase=True if completed_order else False,  # Mark as verified if has order
            )
            
            messages.success(request, "Thank you for your review! It has been submitted successfully.")
            
        except (ValueError, TypeError):
            messages.error(request, "Please provide a valid rating (1-5 stars).")
        except Exception as e:
            messages.error(request, "There was an error submitting your review. Please try again.")

    return redirect('products:product_detail', product.category.slug, product.slug)

@require_http_methods(["GET"])
def get_variation_stock(request, product_id):
    """AJAX endpoint to get stock information for all variation combinations"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Get all variation combinations with stock
        stock_data = {}
        
        if hasattr(product, 'variations'):
            combinations = product.variations.filter(is_active=True) 
            
            for combination in combinations:
                #  ProductVariation has direct access to variation_type and variation_option
                combination_key = f"{combination.variation_type.name}:{combination.variation_option.id}"
                
                stock_data[combination_key] = {
                    'stock': combination.stock_quantity, 
                    'price': float(combination.price_adjustment),  
                    'available': combination.stock_quantity > 0  
                }
        
        return JsonResponse({
            'success': True,
            'stock_data': stock_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    
@require_http_methods(["POST"])
def check_variant_combination(request, product_id):
    """
    AJAX endpoint to check stock for specific variant combinations
    """
    try:
        import json
        
        product = get_object_or_404(Product, id=product_id)
        data = json.loads(request.body)
        selected_options = data.get('selected_options', [])
        
        if not selected_options:
            return JsonResponse({
                'success': True,
                'stock': product.stock,
                'price': float(product.price),
                'available': product.stock > 0,
                'message': 'Select variants to check availability'
            })
        
        # Get variations for selected options
        variations = ProductVariation.objects.filter(
            product=product,
            variation_option_id__in=selected_options,
            is_active=True
        )
        
        if not variations.exists():
            return JsonResponse({
                'success': True,
                'stock': 0,
                'price': float(product.price),
                'available': False,
                'message': 'This combination is not available'
            })
        
        # Calculate minimum stock and total price adjustment
        min_stock = min([v.stock_quantity for v in variations])
        total_price_adjustment = sum([float(v.price_adjustment) for v in variations])
        final_price = float(product.price) + total_price_adjustment
        
        # Check if all required variation types are selected
        required_types_count = product.get_category_variations().filter(is_required=True).count()
        selected_types_count = variations.values('variation_type').distinct().count()
        
        is_complete = selected_types_count >= required_types_count
        is_available = min_stock > 0 and is_complete
        
        # Generate appropriate message
        if not is_complete:
            message = 'Please select all required options'
        elif min_stock == 0:
            message = 'This combination is out of stock'
        elif min_stock <= 5:
            message = f'Only {min_stock} left in stock!'
        else:
            message = f'{min_stock} in stock'
        
        return JsonResponse({
            'success': True,
            'stock': min_stock,
            'price': final_price,
            'available': is_available,
            'message': message,
            'is_complete': is_complete
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    

def search(request):
    """search for products by keyword"""
    products = Product.objects.none()
    keyword = ''

    if 'keyword' in request.GET:
        keyword = request.GET.get('keyword', '').strip()
        if keyword:
            search_terms = generate_search_variations(keyword)
            
            query = Q()
            
            for term in search_terms:
                query |= Q(name__iexact=term)
                query |= Q(brand__iexact=term)
                query |= Q(name__istartswith=term)
                query |= Q(description__istartswith=term)
                query |= Q(brand__istartswith=term)
                query |= Q(name__icontains=term)
                query |= Q(description__icontains=term)
                query |= Q(brand__icontains=term)
                query |= Q(spec__icontains=term)
                query |= Q(category__category_name__icontains=term)

            products = Product.objects.filter(
                query,
                status=True,
                admin_approved=True,
                approval_status='approved'
            ).order_by('-created_at').distinct()

    cats = Category.objects.filter(status=True)
    paginator = Paginator(products, 6)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)

    if request.user.is_authenticated:
        in_cart_ids = list(
            CartItem.objects.filter(cart__user=request.user)
            .values_list('product_id', flat=True)
        )
    else:
        in_cart_ids = list(
            CartItem.objects.filter(cart__cart_id=_cart_id(request))
            .values_list('product_id', flat=True)
        )

    context = {
        'products': paged_products,
        'product_count': products.count(),
        'categories': cats,
        'links': cats,
        'keyword': keyword,
        'in_cart_ids': in_cart_ids,
    }

    return render(request, 'products/products.html', context)