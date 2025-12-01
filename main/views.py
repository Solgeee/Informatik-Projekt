# Core application imports and setup
from django.http import HttpResponse  # # For returning HTTP responses
from django.shortcuts import render, get_object_or_404, redirect  # # Core view utilities
from .models import Poll, Vote, Option, AudienceCategory, AudienceOption, UserAudienceOption, BerlinPostalCode, UserProfile  # # Poll with dynamic Options and per-user Vote
from django.contrib.auth import authenticate, login as auth_login, logout  # # Authentication handlers
from django.contrib.auth.models import User  # # User model for registration
from django.contrib import messages  # # For flash messages
from django.contrib.auth.decorators import login_required  # # Protects routes requiring auth
import re
from django.utils.translation import gettext as _
from django.utils import translation
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
from .models import EmailVerification


def _user_restriction_summary(user):
    """Return tuple (ids, summary_list) for the user's audience restrictions."""
    opts = (UserAudienceOption.objects
            .filter(user=user)
            .select_related('option__category')
           )
    ids = [uao.option_id for uao in opts]
    summary = [f"{uao.option.category.name}: {uao.option.name}" for uao in opts]
    return ids, summary


def _required_category_ids():
    """Categories that are actually used to restrict polls (appear in Poll.groups)."""
    return set(AudienceCategory.objects.filter(options__polls__isnull=False).distinct().values_list('id', flat=True))


def _user_has_full_restrictions(user):
    """True if user selected exactly one option for each required category (those used by polls)."""
    required = _required_category_ids()
    if not required:
        return True
    from django.db.models import Count
    rows = (UserAudienceOption.objects
            .filter(user=user, option__category_id__in=required)
            .values('option__category')
            .annotate(c=Count('id')))
    user_cats = {r['option__category'] for r in rows}
    if user_cats != required:
        return False
    return all(r['c'] == 1 for r in rows)


def _assign_restrictions_from_postal(user, postal_code: str):
    """Assign the Berlin Bezirk restriction based on a postal code if mapped.

    Ensures AudienceCategory 'Berlin Bezirk' exists and contains the matching Bezirk option.
    """
    code = re.sub(r'\D', '', (postal_code or ''))
    if not code:
        return False
    mapping = BerlinPostalCode.objects.select_related('bezirk__category').filter(code=code).first()
    if not mapping:
        return False
    bezirk_option = mapping.bezirk
    # Ensure it's under the correct category name
    if bezirk_option.category.name != 'Berlin Bezirk':
        # If data inconsistency, attempt to move or recreate under correct category
        cat, _created = AudienceCategory.objects.get_or_create(name='Berlin Bezirk')
        if bezirk_option.category_id != cat.id:
            # Create/get proper option under Berlin Bezirk
            bezirk_option, _created = AudienceOption.objects.get_or_create(category=cat, name=mapping.bezirk.name)
    # Upsert user's selection for this category
    from django.db.models import Q
    UserAudienceOption.objects.filter(user=user, option__category=bezirk_option.category).delete()
    UserAudienceOption.objects.create(user=user, option=bezirk_option)
    return True


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
        messages.info(request, _('Please set your restrictions before voting.'))
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
        messages.error(request, _('No options available for this poll. Please ask an admin to add options.'))
        return render(request, "main/vote.html", { 'poll': poll, 'options': [], 'previous_option_id': None })

    previous_vote = Vote.objects.filter(user=user, poll=poll).select_related('option').first()

    if request.method == 'POST':
        opt_id = request.POST.get('option')
        if not opt_id:
            messages.error(request, _('Please select an option before submitting.'))
            previous_option_id = previous_vote.option_id if previous_vote and previous_vote.option_id else None
            return render(request, "main/vote.html", { 'poll': poll, 'options': options, 'previous_option_id': previous_option_id })
        try:
            selected = next(o for o in options if str(o.id) == str(opt_id))
        except StopIteration:
            messages.error(request, _('Invalid option selected.'))
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
            messages.error(request, _('Invalid username or password.'))  # # Show error for invalid login
    return render(request, 'main/login.html')

def register(request):
    # Keep legacy direct registration for backward compatibility; redirect to first step.
    return redirect('register_name')

def register_name(request):
    if request.method == 'POST':
        first = request.POST.get('first_name', '').strip()
        last = request.POST.get('last_name', '').strip()
        if not first or not last:
            messages.error(request, _('Please enter both first and last name.'))
        else:
            request.session['reg_first_name'] = first
            request.session['reg_last_name'] = last
            # proceed to email verification step
            return redirect('request_verification')
    return render(request, 'main/register_name.html')

def register_email(request):
    if 'reg_first_name' not in request.session or 'reg_last_name' not in request.session:
        messages.error(request, _('Please start registration with your name.'))
        return redirect('register_name')

    if request.method == 'POST':
        # require that the email was previously verified
        if not request.session.get('email_verified'):
            messages.error(request, _('Please verify your email before continuing.'))
            return redirect('request_verification')

        # Always use the email that was verified and stored in session.
        # Do not trust a POSTed email value here — it must match the previously verified one.
        email = request.session.get('reg_email', '').strip()
        # Defensive: if for some reason email_verified is True but reg_email is missing, fall back to POST.
        if not email:
            email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()  # optional custom username
        password = request.POST.get('password', '').strip()
        postal = request.POST.get('postal_code', '').strip()

        # Basic email format validation
        if '@' not in email or '.' not in email.split('@')[-1]:
            messages.error(request, _('Please provide a valid email address.'))
            return render(request, 'main/register_email.html')
        if not username:
            username = email.split('@')[0]
        if User.objects.filter(username=username).exists():
            messages.error(request, _('Username already exists. Choose another.'))
            return render(request, 'main/register_email.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, _('Email already registered. Use another or login.'))
            return render(request, 'main/register_email.html')
        if len(password) < 4:
            messages.error(request, _('Password must be at least 4 characters.'))
            return render(request, 'main/register_email.html')
        # Create the user immediately and assign postal-based restrictions
        first = request.session.pop('reg_first_name')
        last = request.session.pop('reg_last_name')
        # keep reg_email and email_verified in session until registration completes
        user = User.objects.create_user(username=username, password=password, email=email, first_name=first, last_name=last)
        # Persist postal in profile and map restrictions
        if postal:
            profile, _created = UserProfile.objects.get_or_create(user=user)
            profile.postal_code = postal
            profile.save()
            _assign_restrictions_from_postal(user, postal)
        # Log user in to allow editing remaining restrictions seamlessly
        authed_user = authenticate(request, username=user.username, password=password)
        if authed_user:
            auth_login(request, authed_user)
            current_user = authed_user
        else:
            current_user = user
        # If all required categories satisfied, finish; otherwise go to restrictions page prefilled
        if _user_has_full_restrictions(current_user):
            messages.success(request, _('Registration complete. Restrictions assigned based on postal code.'))
            # cleanup verification session flags
            request.session.pop('email_verified', None)
            request.session.pop('reg_email', None)
            return redirect('home')
        else:
            messages.info(request, _('We assigned what we could from your postal code. Please confirm remaining restrictions to finish.'))
            return redirect('register_restrictions')

    return render(request, 'main/register_email.html')


def request_verification(request):
    """Step where user submits an email to receive a verification code."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email or '@' not in email:
            messages.error(request, _('Please provide a valid email address.'))
            return render(request, 'main/request_verification.html')
        # Don't allow requesting verification for an email that's already registered
        try:
            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, _('Email already registered. Please log in or use a different email.'))
                return render(request, 'main/request_verification.html')
        except Exception:
            # If User model isn't available for some reason, continue with verification flow
            pass
        # create a 6-digit numeric code
        code = f"{random.randint(0, 999999):06d}"
        expires = timezone.now() + timedelta(minutes=15)
        EmailVerification.objects.create(email=email, code=code, expires_at=expires)
        # Send email (uses settings.EMAIL_BACKEND)
        subject = _('Your verification code')
        message = _('Your verification code is: ') + code
        try:
            send_mail(subject, message, None, [email])
            messages.success(request, _('Verification code sent. Check your email.'))
        except Exception:
            messages.error(request, _('Failed to send verification email.'))
        # Store the email in session for later registration steps
        request.session['reg_email'] = email
        return redirect('verify_code')
    return render(request, 'main/request_verification.html')


def verify_code(request):
    """Enter the code received by email to confirm ownership."""
    email = request.session.get('reg_email')
    if not email:
        messages.info(request, _('Please enter your email first.'))
        return redirect('request_verification')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        now = timezone.now()
        # If the email is already registered, disallow verification and prompt to login
        try:
            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, _('This email is already registered. Please log in.'))
                return redirect('login')
        except Exception:
            # If User lookup fails for any reason, continue to verification attempt
            pass
        ev = EmailVerification.objects.filter(email__iexact=email, code=code, used=False, expires_at__gte=now).order_by('-created').first()
        if ev:
            ev.used = True
            ev.save(update_fields=['used'])
            # Mark verified in session
            request.session['email_verified'] = True
            messages.success(request, _('Email verified. Continue registration.'))
            return redirect('register_email')
        else:
            messages.error(request, _('Invalid or expired verification code.'))

    return render(request, 'main/verify_code.html', { 'email': email })

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
        if in_registration:
            # Create user regardless of manual selections; apply postal-based restriction if provided
            first = request.session.pop('reg_first_name')
            last = request.session.pop('reg_last_name')
            email = request.session.pop('reg_email')
            username = request.session.pop('reg_username')
            password = request.session.pop('reg_password')
            postal = request.session.pop('reg_postal', '')
            auto_restrictions = []
            user = User.objects.create_user(username=username, password=password, email=email, first_name=first, last_name=last)
            # Apply postal code mapping (Berlin Bezirk) if possible
            if postal:
                profile, _created = UserProfile.objects.get_or_create(user=user)
                profile.postal_code = postal
                profile.save()
                _assign_restrictions_from_postal(user, postal)
            # Save any manually selected restrictions
            if selections:
                bulk = [UserAudienceOption(user=user, option=opt) for opt in selections.values()]
                UserAudienceOption.objects.bulk_create(bulk)
            # Ensure auto_restrictions (preselected) are persisted if no manual submission happened for them
            for oid in auto_restrictions:
                if not UserAudienceOption.objects.filter(user=user, option_id=oid).exists():
                    try:
                        opt = AudienceOption.objects.get(pk=oid)
                        UserAudienceOption.objects.create(user=user, option=opt)
                    except AudienceOption.DoesNotExist:
                        pass
            messages.success(request, _('Registration complete. Please log in.'))
            return redirect('login')
        elif request.user.is_authenticated:
            user = request.user
            # Replace selections per category
            from django.db.models import Q
            cat_ids = list(selections.keys())
            UserAudienceOption.objects.filter(user=user, option__category_id__in=cat_ids).delete()
            if selections:
                bulk = [UserAudienceOption(user=user, option=opt) for opt in selections.values()]
                UserAudienceOption.objects.bulk_create(bulk)
            messages.success(request, _('Restrictions saved.'))
            return redirect('home')
        else:
            messages.info(request, _('Please start registration to set restrictions.'))
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
    elif in_registration:
        # Use any auto mapped restrictions from postal code
        auto_ids = request.session.get('auto_restrictions', [])
        for oid in auto_ids:
            try:
                opt = AudienceOption.objects.select_related('category').get(pk=oid)
                selected_map[opt.category_id] = oid
            except AudienceOption.DoesNotExist:
                continue

    context = {
        'categories': categories,
        'selected_map': selected_map,  # category_id -> option_id
        'selected_option_ids': selected_option_ids,
        'selected_groups_summary': selected_summary,
        'in_registration': in_registration,
    }
    return render(request, 'main/register_restrictions.html', context)

def toggle_language(request):
    from django.conf import settings as dj_settings
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'
    current = translation.get_language() or dj_settings.LANGUAGE_CODE
    new = 'de' if (current or '').startswith('en') else 'en'
    translation.activate(new)
    try:
        request.session[translation.LANGUAGE_SESSION_KEY] = new  # type: ignore[attr-defined]
    except Exception:
        request.session['django_language'] = new
    response = redirect(next_url)
    cookie_name = getattr(dj_settings, 'LANGUAGE_COOKIE_NAME', 'django_language')
    response.set_cookie(cookie_name, new)
    return response

def welcome(request):
    return render(request, 'main/welcome.html')  # # Render welcome page