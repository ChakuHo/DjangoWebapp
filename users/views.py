from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Profile

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username') or request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'users/login.html', {'error': 'Invalid credentials'})
    return render(request, 'users/login.html')

def register_view(request):
    if request.method == 'POST':
        # Get form data and create user
        # (You can use Django forms for better validation)
        username = request.POST.get('username') or request.POST.get('email')
        password = request.POST.get('password')
        email = request.POST.get('email')
        user = User.objects.create_user(username=username, password=password, email=email)
        Profile.objects.create(user=user)
        login(request, user)
        return redirect('dashboard')
    return render(request, 'users/register.html')

@login_required
def dashboard(request):
    profile = Profile.objects.get(user=request.user)
    return render(request, 'users/dashboard.html', {'profile': profile})

@login_required
def edit_profile(request):
    profile = Profile.objects.get(user=request.user)
    if request.method == 'POST':
        # Update profile fields here
        profile.phone_number = request.POST.get('phone_number')
        profile.address_line_1 = request.POST.get('address_line_1')
        profile.address_line_2 = request.POST.get('address_line_2')
        profile.city = request.POST.get('city')
        profile.state = request.POST.get('state')
        profile.country = request.POST.get('country')
        if request.FILES.get('profile_picture'):
            profile.profile_picture = request.FILES['profile_picture']
        profile.save()
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.save()
        return redirect('dashboard')
    return render(request, 'users/edit_profile.html', {'profile': profile})

@login_required
def change_password(request):
    if request.method == 'POST':
        current = request.POST.get('current_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')
        if not request.user.check_password(current):
            return render(request, 'users/change_password.html', {'error': 'Current password is incorrect'})
        if new != confirm:
            return render(request, 'users/change_password.html', {'error': 'Passwords do not match'})
        request.user.set_password(new)
        request.user.save()
        return redirect('login')
    return render(request, 'users/change_password.html')

def logout_view(request):
    logout(request)
    return redirect('login')