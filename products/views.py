from django.shortcuts import render, get_object_or_404
from . models import Category, Product

# Create your views here.

def product(request):
    product = Product.objects.all()
    # return render(request, 'products/products.html')
    return render(request, 'products/products.html', {'products':product})

def productDetails(request, id):
    product = get_object_or_404(Product, id=id)
    # return render("request", 'products/details.html', {'product': product})
    return render(request, 'products/details.html', {'product': product})