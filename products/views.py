from django.shortcuts import render, get_object_or_404
from .models import ProductCategory, Product

def product(request):
    products = Product.objects.all()
    return render(request, 'products/products.html', {'products': products})

def productDetails(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, 'products/details.html', {'product': product})

def product_detail(request, category, product):
    product_obj = get_object_or_404(Product, category__name__iexact=category, slug__iexact=product)
    return render(request, 'products/details.html', {'product': product_obj, 'category': category})