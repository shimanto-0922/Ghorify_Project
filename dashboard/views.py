from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import Profile, User
from properties.models import Property


@login_required
def home(request):
    # Admins see the admin overview, everyone else sees their own dashboard
    if request.user.is_platform_admin:
        return admin_overview(request)
    return user_dashboard(request)


def user_dashboard(request):
    # One dashboard for everyone: homes you saved and homes you posted
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    my_listings = user.properties.all()

    stats = {
        'favourites': user.favourites.count(),
        'comparisons': user.comparisons.count(),
        'listings': my_listings.count(),
        'published': my_listings.filter(status='approved').count(),
    }
    favourites = user.favourites.select_related(
        'property', 'property__landlord__profile'
    ).prefetch_related('property__images', 'property__amenities').order_by('-created_at')[:3]
    latest_listings = my_listings.prefetch_related('images').annotate(
        fav_count=Count('favourited_by', distinct=True)
    ).order_by('-created_at')[:5]

    return render(
        request,
        'dashboard/user.html',
        {
            'profile': profile,
            'stats': stats,
            'favourites': favourites,
            'my_listings': latest_listings,
        }
    )


# ---------------------------------------------------------------------------
# Platform admin
# ---------------------------------------------------------------------------

@login_required
def admin_overview(request):
    if not request.user.is_platform_admin:
        messages.error(request, 'You do not have permission to open that page.')
        return redirect('dashboard:home')

    published = Property.objects.filter(status='approved')
    pending = Property.objects.filter(status='pending')
    stats = {
        'users': User.objects.count(),
        'posters': User.objects.filter(properties__isnull=False).distinct().count(),
        'published': published.count(),
        'pending_properties': pending.count(),
        'pending_profiles': Profile.objects.filter(status='pending').count(),
    }
    area_breakdown = published.values('location').annotate(n=Count('id')).order_by('-n')[:6]
    latest_pending = pending.select_related('landlord', 'landlord__profile').order_by('-created_at')[:5]

    return render(
        request,
        'dashboard/admin_overview.html',
        {
            'stats': stats,
            'area_breakdown': area_breakdown,
            'latest_pending': latest_pending,
        }
    )


@login_required
def moderation_list(request):
    if not request.user.is_platform_admin:
        messages.error(request, 'You do not have permission to open that page.')
        return redirect('dashboard:home')

    status = request.GET.get('status', 'pending')
    properties = Property.objects.select_related(
        'landlord', 'landlord__profile'
    ).prefetch_related('images').order_by('-created_at')
    if status in ['pending', 'approved', 'rejected']:
        properties = properties.filter(status=status)
    page = Paginator(properties, 12).get_page(request.GET.get('page'))

    return render(
        request,
        'dashboard/moderation.html',
        {
            'page': page,
            'status': status,
            'status_choices': Property.STATUS_CHOICES,
        }
    )


@login_required
def moderate_property(request, property_id):
    if not request.user.is_platform_admin:
        messages.error(request, 'You do not have permission to open that page.')
        return redirect('dashboard:home')

    prop = get_object_or_404(Property, id=property_id)
    back = request.POST.get('next') or 'dashboard:moderation_list'
    if request.method == 'POST':
        decision = request.POST.get('decision')
        note = request.POST.get('note', '').strip()[:255]
        if decision == 'approve':
            prop.status = 'approved'
            prop.moderation_note = ''
            prop.save()
            messages.success(request, f'"{prop.title}" is now live.')
        elif decision == 'reject':
            if not note:
                messages.error(request, 'Please write a short reason so the owner can fix the listing.')
                return redirect(back)
            prop.status = 'rejected'
            prop.moderation_note = note
            prop.save()
            messages.info(request, f'"{prop.title}" was rejected.')
    return redirect(back)


@login_required
def verification_list(request):
    if not request.user.is_platform_admin:
        messages.error(request, 'You do not have permission to open that page.')
        return redirect('dashboard:home')

    status = request.GET.get('status', 'pending')
    profiles = Profile.objects.select_related('user', 'verified_by').annotate(
        listings=Count('user__properties')
    )
    if status in ['unsubmitted', 'pending', 'verified', 'rejected']:
        profiles = profiles.filter(status=status)

    return render(
        request,
        'dashboard/verification.html',
        {
            'profiles': profiles,
            'status': status,
            'status_choices': Profile.STATUS_CHOICES,
        }
    )


@login_required
def verify_user(request, profile_id):
    if not request.user.is_platform_admin:
        messages.error(request, 'You do not have permission to open that page.')
        return redirect('dashboard:home')

    profile = get_object_or_404(Profile, id=profile_id)
    if request.method == 'POST':
        if request.POST.get('decision') == 'approve':
            if not profile.nid_document and not profile.birth_certificate:
                messages.error(request, 'This user has not uploaded an NID or Birth Certificate yet.')
            else:
                profile.status = 'verified'
                profile.verified_by = request.user
                profile.verified_at = timezone.now()
                profile.review_note = ''
                profile.save()
                messages.success(request, f'{profile.user} is now verified.')
        else:
            profile.status = 'rejected'
            profile.verified_by = request.user
            profile.verified_at = None
            profile.review_note = request.POST.get('note', '').strip()[:255]
            profile.save()
            messages.info(request, f'Verification for {profile.user} was rejected.')
    return redirect(request.POST.get('next') or 'dashboard:verification_list')


@login_required
def user_list(request):
    if not request.user.is_platform_admin:
        messages.error(request, 'You do not have permission to open that page.')
        return redirect('dashboard:home')

    role = request.GET.get('role', '')
    q = request.GET.get('q', '').strip()
    users = User.objects.annotate(listing_count=Count('properties')).order_by('-date_joined')
    if role in ['user', 'admin']:
        users = users.filter(role=role)
    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(email__icontains=q) |
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    page = Paginator(users, 15).get_page(request.GET.get('page'))

    return render(
        request,
        'dashboard/users.html',
        {
            'page': page,
            'role': role,
            'q': q,
            'roles': User.ROLE_CHOICES,
        }
    )


@login_required
def toggle_user(request, user_id):
    if not request.user.is_platform_admin:
        messages.error(request, 'You do not have permission to open that page.')
        return redirect('dashboard:home')

    target = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        if target == request.user or target.is_superuser:
            messages.error(request, 'You cannot deactivate this account.')
        else:
            target.is_active = not target.is_active
            target.save()
            if target.is_active:
                messages.success(request, f'{target} has been activated.')
            else:
                messages.success(request, f'{target} has been deactivated.')
    return redirect(request.POST.get('next') or 'dashboard:user_list')
