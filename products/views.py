from django.shortcuts import render, get_object_or_404
from django.db.models import Q  
from .models import Category, Product
from django.http import Http404
from cart.models import CartItem
from cart.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

def product(request, category_slug=None):
    """
    Display products - all products or filtered by category
    This view handles both /products/ and /products/category/slug/
    """
    categories = None
    products = None

    if category_slug is not None:
        # Show products from specific category
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, status=True)
        paginator = Paginator(products, 6)  # Show 6 products per page
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()  # Get actual count, not just current page
    else:
        # Show all products
        products = Product.objects.all().filter(status=True).order_by('id')
        paginator = Paginator(products, 6)  # Show 6 products per page
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()  # Get actual count, not just current page

    # Get all categories for sidebar and navbar
    cats = Category.objects.filter(status=True)

    # Get products already in cart
    in_cart_ids = list(
        CartItem.objects.filter(cart__cart_id=_cart_id(request))
        .values_list('product_id', flat=True)
    )

    context = {
        'products': paged_products,
        'product_count': product_count,
        'categories': cats,           # For sidebar category lists
        'links': cats,               # For navbar categories dropdown
        'in_cart_ids': in_cart_ids,  # To show "In Cart" buttons
        'current_category': categories,  # Current selected category (if any)
    }
    return render(request, 'products/products.html', context)

def product_detail(request, category_slug, product_slug):
    """
    Display individual product details
    URL: /products/category/electronics/laptop-hp/
    """
    try:
        product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        

        if request.user.is_authenticated:
            # For authenticated users, check user-based cart
            in_cart = CartItem.objects.filter(cart__user=request.user, product=product).exists()
        else:
            # For anonymous users, check session-based cart
            in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=product).exists()
            
    except Product.DoesNotExist:
        raise Http404("Product Not Found")

    # Get related products from same category
    related_products = Product.objects.filter(
        category=product.category, 
        status=True
    ).exclude(id=product.id)[:4]

    context = {
        'product': product,
        'in_cart': in_cart,
        'related_products': related_products,
    }
    return render(request, 'products/details.html', context)

def search(request):
    """
    Search for products by keyword
    Searches in product name and description
    """
    products = Product.objects.none()  # Initialize with empty queryset
    keyword = ''
    
    if 'keyword' in request.GET:
        keyword = request.GET.get('keyword', '').strip()
        if keyword:
            # Make search more flexible by removing spaces and hyphens
            keyword_variations = [
                keyword,  # Original keyword
                keyword.replace(' ', ''),  # Remove spaces: "t shirt" -> "tshirt"
                keyword.replace('-', ''),  # Remove hyphens: "t-shirt" -> "tshirt"
                keyword.replace(' ', '-'),  # Replace spaces with hyphens: "t shirt" -> "t-shirt"
                keyword.replace('-', ' '),  # Replace hyphens with spaces: "t-shirt" -> "t shirt"
            ]
            
            # Build query for all variations
            query = Q()
            for variation in keyword_variations:
                query |= Q(description__icontains=variation) | Q(name__icontains=variation)
            
            products = Product.objects.filter(query, status=True).order_by('-created_at').distinct()
    
    # Get all categories for sidebar
    cats = Category.objects.filter(status=True)
    
    # Pagination for search results
    paginator = Paginator(products, 6)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    
    # Get products already in cart
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

# Additional helper views you might need

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