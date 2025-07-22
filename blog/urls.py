from django.urls import path
from . import views

urlpatterns = [
    path('', views.blogs, name='blog'),
    path('<int:id>/', views.blog_details, name='blog_details'),
]
