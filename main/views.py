#REQUEST RESPONSE LOGIC
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .models import Poll  # Add this import
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib import messages


def home(request):
    polls = Poll.objects.all()  # Get all polls from database
    context = {
        'polls': polls
    }
    return render(request, "main/home.html", context)

def vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    
    if request.method == 'POST':
        selected_option = request.POST.get('poll_choice')
        if selected_option == 'option1':
            poll.option_one_count += 1
        elif selected_option == 'option2':
            poll.option_two_count += 1
        elif selected_option == 'option3':
            poll.option_three_count += 1
        else:
            return HttpResponse(400, 'Invalid form option')
            
        poll.save()
        return redirect('results', poll_id=poll_id)  # Updated this line
    
    context = {
        'poll': poll
    }
    return render(request, "main/vote.html", context)

def results(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    total = poll.total()
    counts = {
        'one': poll.option_one_count,
        'two': poll.option_two_count,
        'three': poll.option_three_count,
    }
    if total > 0:
        percentages = {
            'one': (counts['one'] / total) * 100,
            'two': (counts['two'] / total) * 100,
            'three': (counts['three'] / total) * 100,
        }
    else:
        percentages = {'one': 0, 'two': 0, 'three': 0}

    context = {
        'poll': poll,
        'total': total,
        'counts': counts,
        'percentages': percentages,
    }
    return render(request, "main/results.html", context)

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('home')  # Change to your main page url name
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'main/login.html')

def register(request):
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