from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from products.models import Product
from blog.models import Blog
from pages.models import Page

def home(request):
    products = Product.objects.all()
    # return render(request, 'home/home.html' , {'products': products})
    blogs = Blog.objects.all()[:3]
    pages = Page.objects.all()
    return render(request, 'home/home.html', {
        'products':products,
        'blogs':blogs,
        'pages':pages,
    })

