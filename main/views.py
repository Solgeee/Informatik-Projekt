#REQUEST RESPONSE LOGIC
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib import messages


def index(request):
    return render(request, "main/index.html")

def vote(request):
    return render(request, "main/vote.html")

def results(request):
    return render(request, "main/results.html")

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('index')  # Change to your main page url name
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'main/login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            User.objects.create_user(username=username, password=password)
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('login')
    return render(request, 'main/register.html')