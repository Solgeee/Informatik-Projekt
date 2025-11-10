# Core application imports and setup
from django.http import HttpResponse  # # For returning HTTP responses
from django.shortcuts import render, get_object_or_404, redirect  # # Core view utilities
from .models import Poll, Vote, Option  # # Poll with dynamic Options and per-user Vote
from django.contrib.auth import authenticate, login as auth_login, logout  # # Authentication handlers
from django.contrib.auth.models import User  # # User model for registration
from django.contrib import messages  # # For flash messages
from django.contrib.auth.decorators import login_required  # # Protects routes requiring auth


def home(request):
    # Prefetch options to avoid N+1 queries in template
    polls = Poll.objects.all().prefetch_related('options')  # # Get all polls and their options
    context = {
        'polls': polls  # # Pass polls to template for display
    }
    return render(request, "main/home.html", context)  # # Render home template with polls

@login_required(login_url='login')
def vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    user = request.user
    options = list(Option.objects.filter(poll=poll).order_by('order', 'id')[:10])

    # Auto-create dynamic options from legacy fields if none exist yet
    if not options:
        legacy = []
        if poll.option_one:
            legacy.append(poll.option_one)
        if poll.option_two:
            legacy.append(poll.option_two)
        if poll.option_three:
            legacy.append(poll.option_three)
        for idx, text in enumerate(legacy):
            Option.objects.create(poll=poll, text=text, order=idx, votes=getattr(poll, f'option_{['one','two','three'][idx]}_count'))
        options = list(Option.objects.filter(poll=poll).order_by('order', 'id')[:10])

    # If no dynamic options exist, show message guiding admin to add them
    if not options:
        messages.error(request, 'No options available for this poll. Please ask an admin to add options.')
        return render(request, "main/vote.html", { 'poll': poll, 'options': [], 'previous_option_id': None })

    previous_vote = Vote.objects.filter(user=user, poll=poll).select_related('option').first()

    if request.method == 'POST':
        opt_id = request.POST.get('option')
        if not opt_id:
            messages.error(request, 'Please select an option before submitting.')
            previous_option_id = previous_vote.option_id if previous_vote and previous_vote.option_id else None
            return render(request, "main/vote.html", { 'poll': poll, 'options': options, 'previous_option_id': previous_option_id })
        try:
            selected = next(o for o in options if str(o.id) == str(opt_id))
        except StopIteration:
            messages.error(request, 'Invalid option selected.')
            previous_option_id = previous_vote.option_id if previous_vote and previous_vote.option_id else None
            return render(request, "main/vote.html", { 'poll': poll, 'options': options, 'previous_option_id': previous_option_id })

        # Change vote handling: decrement old, increment new
        from django.db.models import F
        from django.db import transaction
        with transaction.atomic():
            if previous_vote and previous_vote.option_id == selected.id:
                return redirect('results', poll_id=poll_id)

            if previous_vote and previous_vote.option_id:
                Option.objects.filter(pk=previous_vote.option_id).update(votes=F('votes') - 1)
                previous_vote.option = selected
                previous_vote.choice = None  # legacy clear
                previous_vote.save(update_fields=['option', 'choice'])
            else:
                Vote.objects.create(user=user, poll=poll, option=selected)

            Option.objects.filter(pk=selected.id).update(votes=F('votes') + 1)

        return redirect('results', poll_id=poll_id)

    previous_option_id = previous_vote.option_id if previous_vote and previous_vote.option_id else None
    return render(request, "main/vote.html", { 'poll': poll, 'options': options, 'previous_option_id': previous_option_id })

def results(request, poll_id):
    from django.db.models import Sum
    poll = get_object_or_404(Poll, pk=poll_id)
    options = list(Option.objects.filter(poll=poll).order_by('order', 'id')[:10])
    if not options:
        # Same legacy bootstrap logic for direct navigation to results
        legacy = []
        if poll.option_one:
            legacy.append(poll.option_one)
        if poll.option_two:
            legacy.append(poll.option_two)
        if poll.option_three:
            legacy.append(poll.option_three)
        for idx, text in enumerate(legacy):
            Option.objects.create(poll=poll, text=text, order=idx, votes=getattr(poll, f'option_{['one','two','three'][idx]}_count'))
        options = list(Option.objects.filter(poll=poll).order_by('order', 'id')[:10])
    total = Option.objects.filter(poll=poll).aggregate(total=Sum('votes'))['total'] or 0
    items = []
    for idx, opt in enumerate(options, start=1):
        pct = (opt.votes / total * 100) if total else 0
        items.append({
            'index': idx,
            'id': opt.id,
            'text': opt.text,
            'votes': opt.votes,
            'percent': pct,
        })

    return render(request, "main/results.html", { 'poll': poll, 'items': items, 'total': total })

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