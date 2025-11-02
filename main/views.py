# Core application imports and setup
from django.http import HttpResponse  # # For returning HTTP responses
from django.shortcuts import render, get_object_or_404, redirect  # # Core view utilities
from .models import Poll  # # Poll model for database operations
from django.contrib.auth import authenticate, login as auth_login, logout  # # Authentication handlers
from django.contrib.auth.models import User  # # User model for registration
from django.contrib import messages  # # For flash messages
from django.contrib.auth.decorators import login_required  # # Protects routes requiring auth


def home(request):
    polls = Poll.objects.all()  # # Get all polls from database - available to all users
    context = {
        'polls': polls  # # Pass polls to template for display
    }
    return render(request, "main/home.html", context)  # # Render home template with polls

@login_required(login_url='login')  # # Requires authentication, redirects to login if not authenticated
def vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)  # # Get poll or return 404 if not found
    
    if request.method == 'POST':  # # Handle vote submission
        selected_option = request.POST.get('poll_choice')  # # Get selected option from form
        if selected_option == 'option1':  # # Update appropriate counter
            poll.option_one_count += 1
        elif selected_option == 'option2':
            poll.option_two_count += 1
        elif selected_option == 'option3':
            poll.option_three_count += 1
        else:
            return HttpResponse(400, 'Invalid form option')  # # Handle invalid submissions
            
        poll.save()  # # Save updated vote counts
        return redirect('results', poll_id=poll_id)  # # Redirect to results page after successful vote
    
    context = {
        'poll': poll
    }
    return render(request, "main/vote.html", context)

def results(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)  # # Get poll or 404
    total = poll.total()  # # Calculate total votes for percentages
    counts = {  # # Store raw vote counts
        'one': poll.option_one_count,
        'two': poll.option_two_count,
        'three': poll.option_three_count,
    }
    if total > 0:  # # Calculate percentages if votes exist
        percentages = {
            'one': (counts['one'] / total) * 100,  # # Calculate percentage for option 1
            'two': (counts['two'] / total) * 100,  # # Calculate percentage for option 2
            'three': (counts['three'] / total) * 100,  # # Calculate percentage for option 3
        }
    else:  # # Handle case with no votes
        percentages = {'one': 0, 'two': 0, 'three': 0}

    context = {
        'poll': poll,
        'total': total,
        'counts': counts,
        'percentages': percentages,
    }
    return render(request, "main/results.html", context)

def login(request):
    if request.method == 'POST':  # # Handle login form submission
        username = request.POST['username']  # # Get credentials from form
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)  # # Verify user credentials
        if user is not None:  # # If credentials are valid
            auth_login(request, user)  # # Create user session
            return redirect('home')  # # Redirect to home page
        else:
            messages.error(request, 'Invalid username or password.')  # # Show error for invalid login
    return render(request, 'main/login.html')

def register(request):
    if request.method == 'POST':  # # Handle registration form
        username = request.POST['username']  # # Get form data
        password = request.POST['password']
        if User.objects.filter(username=username).exists():  # # Check if username is taken
            messages.error(request, 'Username already exists.')  # # Show error if username exists
        else:
            User.objects.create_user(username=username, password=password)  # # Create new user
            messages.success(request, 'Registration successful. Please log in.')  # # Show success message
            return redirect('login')  # # Redirect to login page
    return render(request, 'main/register.html')

def logout_view(request):
    logout(request)  # # Clear user session
    return redirect('home')  # # Redirect to home page after logout