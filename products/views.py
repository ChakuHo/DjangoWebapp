from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .models import Category, Product, Review, VariationOption, VariationType
from django.http import Http404
from cart.models import CartItem
from cart.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from orders.models import Order
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


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
    if sort_by in ['name', '-name', 'price', '-price', '-created_at']:
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
    }
    return render(request, 'products/products.html', context)

def sale_products(request):
    """Display only discounted/sale products"""
    products = Product.objects.filter(
        status=True,
        admin_approved=True,
        approval_status='approved',
        is_on_sale=True
    ).order_by('-created_at')

    # Apply same filtering as main products view
    # ... (copy filtering logic from above)

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

    # Apply same filtering logic as main products view
    # ... (copy filtering logic from main product view)

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
        'page_title': 'Thrift Products' + (f' - {category.category_name}' if category else ''),
        'is_thrift_page': True,
    }
    return render(request, 'products/products.html', context)

def product_detail(request, category_slug, product_slug):
    """
    Display individual product details
    URL: /products/category/electronics/laptop-hp/
    """
    import json  
    
    try:
        product = Product.objects.get(
            category__slug=category_slug, 
            slug=product_slug,
            status=True,
            admin_approved=True,
            approval_status='approved'
        )

        if request.user.is_authenticated:
            in_cart = CartItem.objects.filter(cart__user=request.user, product=product).exists()
        else:
            in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=product).exists()
            
    except Product.DoesNotExist:
        raise Http404("Product Not Found")

    related_products = Product.objects.filter(
        category=product.category, 
        status=True,
        admin_approved=True,
        approval_status='approved'
    ).exclude(id=product.id)[:4]

    reviews = Review.objects.filter(product=product, status=True).order_by('-created_at')

    user_can_review = False
    user_has_reviewed = False

    if request.user.is_authenticated:
        user_can_review = user_can_review_product(request.user, product)
        user_has_reviewed = Review.objects.filter(user=request.user, product=product).exists()

    seller_product_count = 0
    if product.seller:
        seller_product_count = Product.objects.filter(
            seller=product.seller, 
            status=True, 
            admin_approved=True,
            approval_status='approved'
        ).count()

    variation_images = {}
    
    # Get all product variations for this product
    from .models import ProductVariation
    product_variations = ProductVariation.objects.filter(
        product=product, 
        is_active=True
    ).select_related('variation_option')
    
    for variation in product_variations:
        option_id = str(variation.variation_option.id)
        if option_id not in variation_images:
            variation_images[option_id] = []
        

        if variation.image1:
            variation_images[option_id].append(variation.image1.url)
        if variation.image2:
            variation_images[option_id].append(variation.image2.url)
        if variation.image3:
            variation_images[option_id].append(variation.image3.url)


    available_variations = product.get_available_variations()
    has_variations = product.has_variations()

    context = {
        'product': product,
        'in_cart': in_cart,
        'related_products': related_products,
        'reviews': reviews,
        'user_can_review': user_can_review,
        'user_has_reviewed': user_has_reviewed,
        'seller_product_count': seller_product_count,
        'variation_images_json': json.dumps(variation_images),
        # ⭐ ADD THESE LINES:
        'available_variations': available_variations,
        'has_variations': has_variations,
    }
    return render(request, 'products/details.html', context)
def search(request):
    """
    Enhanced search for products by keyword
    Searches in product name, description, brand, and category
    """
    products = Product.objects.none()
    keyword = ''

    if 'keyword' in request.GET:
        keyword = request.GET.get('keyword', '').strip()
        if keyword:
            # ENHANCED: Create comprehensive search variations
            search_terms = generate_search_variations(keyword)
            
            # Build comprehensive query
            query = Q()
            
            # 1. EXACT MATCHES (highest priority)
            for term in search_terms:
                query |= Q(name__iexact=term)  # Exact name match
                query |= Q(brand__iexact=term)  # Exact brand match
            
            # 2. STARTS WITH MATCHES (high priority)
            for term in search_terms:
                query |= Q(name__istartswith=term)  # Name starts with
                query |= Q(description__istartswith=term)  # Description starts with
                query |= Q(brand__istartswith=term)  # Brand starts with
            
            # 3. CONTAINS MATCHES (medium priority)
            for term in search_terms:
                query |= Q(name__icontains=term)  # Name contains
                query |= Q(description__icontains=term)  # Description contains
                query |= Q(brand__icontains=term)  # Brand contains
                query |= Q(spec__icontains=term)  # Specifications contain
            
            # 4. CATEGORY MATCHES
            for term in search_terms:
                query |= Q(category__category_name__icontains=term)  # Category name contains
            
            # 5. INDIVIDUAL WORD MATCHES (for multi-word searches)
            words = keyword.lower().split()
            if len(words) > 1:
                # First word priority
                first_word = words[0]
                first_word_variations = generate_search_variations(first_word)
                for variation in first_word_variations:
                    query |= Q(name__icontains=variation)
                    query |= Q(description__icontains=variation)
                
                # Other words
                for word in words[1:]:
                    word_variations = generate_search_variations(word)
                    for variation in word_variations:
                        query |= Q(name__icontains=variation)
                        query |= Q(description__icontains=variation)

            # Apply security filters
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
    
    # Add variations with different separators
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
    
    # Advanced variations for common cases
    advanced_variations = set()
    for var in variations:
        # Add single character separations (for cases like "tshirt" -> "t shirt")
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
    Alternative view for category products (if needed)
    This is just a wrapper around the main product view
    """
    return product(request, category_slug=slug)

def product_list(request):
    """
    Alternative view for all products (if needed)
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