# Core application imports and setup
from django.http import HttpResponse  # # For returning HTTP responses
from django.shortcuts import render, get_object_or_404, redirect  # # Core view utilities
from .models import Poll, Vote  # # Poll and Vote models for tracking counts and per-user votes
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
    user = request.user

    # Check if the user has already voted on this poll
    try:
        previous_vote = Vote.objects.get(user=user, poll=poll)
    except Vote.DoesNotExist:
        previous_vote = None

    if request.method == 'POST':  # # Handle vote submission
        selected_option = request.POST.get('poll_choice')  # # Get selected option from form

        if selected_option not in ('option1', 'option2', 'option3'):
            return HttpResponse(400, 'Invalid form option')  # # Handle invalid submissions

        # If the user already voted, decrement previous choice count first
        if previous_vote:
            # If they selected the same option again, do nothing (no double-count)
            if selected_option == previous_vote.choice:
                return redirect('results', poll_id=poll_id)

            # decrement the old counter (guard against negative counts)
            if previous_vote.choice == 'option1' and poll.option_one_count > 0:
                poll.option_one_count -= 1
            elif previous_vote.choice == 'option2' and poll.option_two_count > 0:
                poll.option_two_count -= 1
            elif previous_vote.choice == 'option3' and poll.option_three_count > 0:
                poll.option_three_count -= 1

            # increment new counter
            if selected_option == 'option1':
                poll.option_one_count += 1
            elif selected_option == 'option2':
                poll.option_two_count += 1
            elif selected_option == 'option3':
                poll.option_three_count += 1

            # update saved vote
            previous_vote.choice = selected_option
            previous_vote.save()
            poll.save()
            return redirect('results', poll_id=poll_id)

        # No previous vote: create a vote record and increment the selected counter
        if selected_option == 'option1':
            poll.option_one_count += 1
        elif selected_option == 'option2':
            poll.option_two_count += 1
        elif selected_option == 'option3':
            poll.option_three_count += 1

        poll.save()
        Vote.objects.create(user=user, poll=poll, choice=selected_option)
        return redirect('results', poll_id=poll_id)

    context = {
        'poll': poll,
        'previous_choice': previous_vote.choice if previous_vote else None,  # for pre-selecting radios
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