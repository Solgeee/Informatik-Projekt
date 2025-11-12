# Core application imports and setup
from django.http import HttpResponse  # # For returning HTTP responses
from django.shortcuts import render, get_object_or_404, redirect  # # Core view utilities
from .models import Poll, Vote, Option  # # Poll with dynamic Options and per-user Vote
from django.contrib.auth import authenticate, login as auth_login, logout  # # Authentication handlers
from django.contrib.auth.models import User  # # User model for registration
from django.contrib import messages  # # For flash messages
from django.contrib.auth.decorators import login_required  # # Protects routes requiring auth


def home(request):
    # Prefetch options to avoid N+1 queries in template; show only visible polls
    polls = Poll.objects.filter(is_visible=True).prefetch_related('options')
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
        username = request.POST['username']  # # Get credentials from form (email or username)
        password = request.POST['password']
        # Try standard username login first
        user = authenticate(request, username=username, password=password)  # # Verify user credentials
        if user is None:
            # Try email lookup then authenticate via the found username
            try:
                lookup = User.objects.get(email__iexact=username)
                user = authenticate(request, username=lookup.username, password=password)
            except User.DoesNotExist:
                user = None
        if user is not None:  # # If credentials are valid
            auth_login(request, user)  # # Create user session
            return redirect('home')  # # Redirect to home page
        else:
            messages.error(request, 'Invalid username or password.')  # # Show error for invalid login
    return render(request, 'main/login.html')

def register(request):
    # Keep legacy direct registration for backward compatibility; redirect to first step.
    return redirect('register_name')

def register_name(request):
    if request.method == 'POST':
        first = request.POST.get('first_name', '').strip()
        last = request.POST.get('last_name', '').strip()
        if not first or not last:
            messages.error(request, 'Please enter both first and last name.')
        else:
            request.session['reg_first_name'] = first
            request.session['reg_last_name'] = last
            return redirect('register_email')
    return render(request, 'main/register_name.html')

def register_email(request):
    if 'reg_first_name' not in request.session or 'reg_last_name' not in request.session:
        messages.error(request, 'Please start registration with your name.')
        return redirect('register_name')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()  # optional custom username
        password = request.POST.get('password', '').strip()

        # Basic email format validation
        if '@' not in email or '.' not in email.split('@')[-1]:
            messages.error(request, 'Please provide a valid email address.')
            return render(request, 'main/register_email.html')
        if not username:
            username = email.split('@')[0]
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Choose another.')
            return render(request, 'main/register_email.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered. Use another or login.')
            return render(request, 'main/register_email.html')
        if len(password) < 4:
            messages.error(request, 'Password must be at least 4 characters.')
            return render(request, 'main/register_email.html')

        first = request.session.pop('reg_first_name')
        last = request.session.pop('reg_last_name')
        user = User.objects.create_user(username=username, password=password, email=email, first_name=first, last_name=last)
        messages.success(request, 'Registration successful. Please log in.')
        return redirect('login')

    return render(request, 'main/register_email.html')

def logout_view(request):
    logout(request)  # # Clear user session
    return redirect('home')  # # Redirect to home page after logout

def welcome(request):
    return render(request, 'main/welcome.html')  # # Render welcome page