from django.urls import path
from . import views

urlpatterns = [
    path('', views.pages, name='pages')
]