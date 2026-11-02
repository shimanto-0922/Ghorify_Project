from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Profile, User
from . import forms


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = forms.RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # No separate username: the phone number is used inside Django
            user.username = user.phone
            # NULL instead of '' so many users can sign up without email
            user.email = form.cleaned_data.get('email') or None
            user.set_password(form.cleaned_data['password1'])
            user.save()
            Profile.objects.create(user=user)
            login(request, user)
            messages.success(
                request,
                f'Welcome to Ghorify, {user.first_name}! '
                'You can look for a home or post your own property.'
            )
            return redirect('dashboard:home')
    else:
        form = forms.RegisterForm()
    return render(
        request,
        'accounts/register.html',
        {'form': form}
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    next_url = request.POST.get('next') or request.GET.get('next', '')
    username = ''
    error = False
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        # People log in with their phone number (or email),
        # so we find the username Django keeps for that account
        typed = username.strip()
        phone = forms.normalize_phone(typed)
        account = None
        if '@' in typed:
            account = User.objects.filter(email__iexact=typed).first()
        elif phone:
            account = User.objects.filter(phone=phone).first()
        if account:
            typed = account.username

        user = authenticate(request, username=typed, password=password)
        if user is not None:
            login(request, user)
            # Only go back to a page on our own site
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('dashboard:home')
        error = True
    return render(
        request,
        'accounts/login.html',
        {'next': next_url, 'username': username, 'error': error}
    )


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('properties:home')


@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Keep the user logged in after the password changes
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed.')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(
        request,
        'accounts/password_change.html',
        {'form': form}
    )


@login_required
def profile(request):
    user = request.user
    profile = None
    if not user.is_platform_admin:
        profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = forms.UserUpdateForm(request.POST, request.FILES, instance=user)
        profile_form = None
        if profile:
            profile_form = forms.ProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            user = user_form.save(commit=False)
            user.email = user_form.cleaned_data.get('email') or None
            user.save()
            if profile_form:
                profile = profile_form.save(commit=False)
                # A new document is sent to the admin for verification
                changed = profile_form.changed_data
                new_document = 'nid_document' in changed or 'birth_certificate' in changed
                has_document = profile.nid_document or profile.birth_certificate
                if new_document and has_document and profile.status != 'verified':
                    profile.status = 'pending'
                    profile.review_note = ''
                    messages.info(request, 'Documents submitted. An admin will verify your account shortly.')
                profile.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('accounts:profile')
        messages.error(request, 'Please fix the errors below.')
    else:
        user_form = forms.UserUpdateForm(instance=user)
        profile_form = None
        if profile:
            profile_form = forms.ProfileForm(instance=profile)

    return render(
        request,
        'accounts/profile.html',
        {'user_form': user_form, 'profile_form': profile_form}
    )
