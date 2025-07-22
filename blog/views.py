from django.shortcuts import render, get_object_or_404
from .models import Blog
# Create your views here.

# def blog (request):
#     blogs = Blog.objects.filter(status=True).order_by('-created_at') #only showing active blogs
#     # return render(request, 'blog/blog.html', {'blogs':blogs})
#     return render(request, 'extending/blog.html', {'blogs':blogs})


def blogs(request):
    all_blogs = Blog.objects.filter(status=True).order_by('-created_at')
    return render(request, 'blog/blog.html', {'blogs': all_blogs})

def blog_details(request, id):
    blog = get_object_or_404(Blog, id=id)
    return render(request, 'blog/blog_details.html', {'blog': blog})