from django.shortcuts import render, get_object_or_404
from django.db.models import Q  
from .models import Category, Product
from django.http import Http404
from cart.models import CartItem
from cart.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

def product(request, category_slug=None):
    categories = None
    products = None

    if category_slug is not None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, status=True)
        paginator = Paginator(products, 3)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = len(paged_products)
    else:
        products = Product.objects.all().filter(status=True).order_by('id')
        paginator = Paginator(products, 3)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = len(paged_products)

    cats = Category.objects.filter(status=True)

    in_cart_ids = list(
        CartItem.objects.filter(cart__cart_id=_cart_id(request))
        .values_list('product_id', flat=True)
    )

    context = {
        'products': paged_products,
        'product_count': product_count,
        'categories': cats,    # sidebar category lists
        'links': cats,          # navbar categories
        'in_cart_ids': in_cart_ids,  
    }
    return render(request, 'products/products.html', context)

def product_detail(request, category_slug, product_slug):
    try:
        product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=product).exists()
    except Product.DoesNotExist:
        raise Http404("Product Not Found")
    
    context = {
        'product': product,
        'in_cart': in_cart,
    }
    return render(request, 'products/details.html', context)

def search(request):
    products = Product.objects.none()  # Initialize with empty queryset
    
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
    
    context = {
        'products': products,
        'product_count': products.count()
    }

    return render(request, 'products/products.html', context)