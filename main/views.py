# Core application imports and setup
from django.http import HttpResponse  # # For returning HTTP responses
from django.shortcuts import render, get_object_or_404, redirect  # # Core view utilities
from .models import Poll, Vote, Option, AudienceCategory, AudienceOption, UserAudienceOption  # # Poll with dynamic Options and per-user Vote
from django.contrib.auth import authenticate, login as auth_login, logout  # # Authentication handlers
from django.contrib.auth.models import User  # # User model for registration
from django.contrib import messages  # # For flash messages
from django.contrib.auth.decorators import login_required  # # Protects routes requiring auth


def _user_restriction_summary(user):
    """Return tuple (ids, summary_list) for the user's audience restrictions."""
    opts = (UserAudienceOption.objects
            .filter(user=user)
            .select_related('option__category')
           )
    ids = [uao.option_id for uao in opts]
    summary = [f"{uao.option.category.name}: {uao.option.name}" for uao in opts]
    return ids, summary


def _user_has_full_restrictions(user):
    """True if user selected exactly one option per category."""
    total_cats = AudienceCategory.objects.count()
    if total_cats == 0:
        return True  # nothing to choose
    # Count distinct categories user has options for
    from django.db.models import Count
    agg = (UserAudienceOption.objects
           .filter(user=user)
           .values('option__category')
           .annotate(c=Count('id')))
    # Must be exactly one per category
    if len(agg) != total_cats:
        return False
    return all(row['c'] == 1 for row in agg)


def home(request):
    base_qs = Poll.objects.filter(is_visible=True).prefetch_related('options', 'groups')
    selected_summary = []
    has_full = False
    restriction_categories = []
    if request.user.is_authenticated:
        has_full = _user_has_full_restrictions(request.user)
        if has_full:
            selected_ids, selected_summary = _user_restriction_summary(request.user)
            from django.db.models import Q
            polls = base_qs.filter(Q(groups__in=selected_ids) | Q(groups__isnull=True)).distinct()
        else:
            # Show all visible polls until restrictions are set; provide category placeholders
            polls = base_qs
            restriction_categories = list(AudienceCategory.objects.all())
    else:
        polls = base_qs

    context = {
        'polls': polls,
        'selected_groups_summary': selected_summary,
        'has_full_restrictions': has_full,
        'restriction_categories': restriction_categories,
    }
    return render(request, "main/home.html", context)  # # Render home template with polls

@login_required(login_url='login')
def vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    user = request.user
    # Enforce restrictions before voting
    if not user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(next=f"/main/vote/{poll_id}/")
    if not _user_has_full_restrictions(user):
        messages.info(request, 'Please set your restrictions before voting.')
        return redirect('restrictions')
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
        # Store details in session; complete user creation after restrictions are collected
        request.session['reg_email'] = email
        request.session['reg_username'] = username
        request.session['reg_password'] = password
        messages.info(request, 'Now choose your restrictions to complete registration.')
        return redirect('register_restrictions')

    return render(request, 'main/register_email.html')

def logout_view(request):
    logout(request)  # # Clear user session
    return redirect('home')  # # Redirect to home page after logout

def register_restrictions(request):
    categories = list(AudienceCategory.objects.prefetch_related('options').all())

    def parse_post():
        selections = {}
        errors = []
        for cat in categories:
            key = f"cat_{cat.id}"
            opt_id = request.POST.get(key)
            if not opt_id:
                errors.append(f"Please select one option for {cat.name}.")
                continue
            try:
                opt = AudienceOption.objects.get(pk=opt_id, category=cat)
            except AudienceOption.DoesNotExist:
                errors.append(f"Invalid option selected for {cat.name}.")
                continue
            selections[cat.id] = opt
        return selections, errors

    in_registration = all(k in request.session for k in ('reg_first_name','reg_last_name','reg_email','reg_username','reg_password'))

    if request.method == 'POST':
        selections, errors = parse_post()
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            if in_registration:
                # Create user, then persist restrictions
                first = request.session.pop('reg_first_name')
                last = request.session.pop('reg_last_name')
                email = request.session.pop('reg_email')
                username = request.session.pop('reg_username')
                password = request.session.pop('reg_password')
                user = User.objects.create_user(username=username, password=password, email=email, first_name=first, last_name=last)
                # Save restrictions
                bulk = [UserAudienceOption(user=user, option=opt) for opt in selections.values()]
                UserAudienceOption.objects.bulk_create(bulk)
                messages.success(request, 'Registration complete. Please log in.')
                return redirect('login')
            elif request.user.is_authenticated:
                user = request.user
                # Replace selections per category
                # Delete any existing for these categories then add new
                from django.db.models import Q
                cat_ids = list(selections.keys())
                UserAudienceOption.objects.filter(user=user, option__category_id__in=cat_ids).delete()
                bulk = [UserAudienceOption(user=user, option=opt) for opt in selections.values()]
                UserAudienceOption.objects.bulk_create(bulk)
                messages.success(request, 'Restrictions saved.')
                return redirect('home')
            else:
                messages.info(request, 'Please start registration to set restrictions.')
                return redirect('register_name')

    # GET: build context with preselected values
    selected_map = {}
    selected_summary = []
    selected_option_ids = []
    if request.user.is_authenticated and not in_registration:
        # Preselect from current user's restrictions
        ids, selected_summary = _user_restriction_summary(request.user)
        selected_option_ids = ids
        for oid in ids:
            try:
                opt = AudienceOption.objects.select_related('category').get(pk=oid)
            except AudienceOption.DoesNotExist:
                continue
            selected_map[opt.category_id] = oid

    context = {
        'categories': categories,
        'selected_map': selected_map,  # category_id -> option_id
        'selected_option_ids': selected_option_ids,
        'selected_groups_summary': selected_summary,
        'in_registration': in_registration,
    }
    return render(request, 'main/register_restrictions.html', context)