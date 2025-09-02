from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from products.models import Product
from blog.models import Blog
from pages.models import Page
from cart.models import Cart


def home(request):
    products = Product.objects.filter(
        status=True,
        admin_approved=True,
        approval_status='approved'
    )
    blogs = Blog.objects.all()[:3]
    pages = Page.objects.all()
    cart = Cart.objects.all()
    # banners= Banner.objects.all().filter(status = True) yo chai banner ko lagi
    # categories = Category.objects.all().filter(status=True)

    context = {
        'products':products,
        # 'banners': banners,
        # 'categories': categories
    }
    return render(request, 'home/home.html', context)
        # 'products':products,
        # 'blogs':blogs,
        # 'pages':pages,
        # 'banners':banners,

    


def about(request):
    return render(request, 'marketplace/about.html')  

