from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from properties.models import Property
from .models import Comparison, ComparisonItem, Favourite


# ---------------------------------------------------------------------------
# Favourites
# ---------------------------------------------------------------------------

@login_required
def favourite_toggle(request, property_id):
    if request.user.is_platform_admin:
        messages.error(request, 'This page is for user accounts.')
        return redirect('dashboard:home')

    prop = get_object_or_404(Property, id=property_id, status='approved')
    if request.method == 'POST':
        favourite = Favourite.objects.filter(tenant=request.user, property=prop).first()
        if favourite:
            favourite.delete()
            messages.info(request, f'Removed "{prop.title}" from your favourites.')
        else:
            Favourite.objects.create(tenant=request.user, property=prop)
            messages.success(request, f'Saved "{prop.title}" to your favourites.')
    if request.POST.get('next'):
        return redirect(request.POST.get('next'))
    return redirect('properties:property_detail', property_id=prop.id)


@login_required
def favourite_list(request):
    favourites = request.user.favourites.select_related(
        'property', 'property__landlord__profile'
    ).prefetch_related('property__images', 'property__amenities').order_by('-created_at')
    return render(
        request,
        'interactions/favourites.html',
        {'favourites': favourites}
    )


# ---------------------------------------------------------------------------
# Compare: pick 2 or 3 favourite homes and see them side by side
# ---------------------------------------------------------------------------

@login_required
def compare_select(request):
    # Only published homes from the user's favourites can be compared
    favourites = list(
        request.user.favourites.select_related('property')
        .prefetch_related('property__images')
        .filter(property__status='approved')
        .order_by('-created_at')
    )

    if request.method == 'POST':
        favourite_homes = {}
        for favourite in favourites:
            favourite_homes[favourite.property_id] = favourite.property

        chosen = []
        for value in request.POST.getlist('property'):
            if value.isdigit() and int(value) not in chosen:
                chosen.append(int(value))

        not_favourite = False
        for property_id in chosen:
            if property_id not in favourite_homes:
                not_favourite = True

        if not_favourite:
            messages.error(request, 'You can only compare homes from your favorites.')
        elif len(chosen) < 2 or len(chosen) > 3:
            messages.error(request, 'Please select 2 or 3 homes to compare.')
        else:
            titles = []
            for property_id in chosen:
                titles.append(favourite_homes[property_id].title)
            comparison = Comparison.objects.create(
                tenant=request.user,
                name=' vs '.join(titles)[:80]
            )
            position = 1
            for property_id in chosen:
                ComparisonItem.objects.create(
                    comparison=comparison,
                    property=favourite_homes[property_id],
                    position=position
                )
                position += 1
            return redirect('interactions:comparison_detail', comparison_id=comparison.id)

    return render(
        request,
        'interactions/compare_select.html',
        {'favourites': favourites}
    )


@login_required
def comparison_detail(request, comparison_id):
    comparison = get_object_or_404(Comparison, id=comparison_id, tenant=request.user)
    items = comparison.items.select_related('property').prefetch_related(
        'property__images', 'property__utilities', 'property__amenities'
    ).order_by('position')
    return render(
        request,
        'interactions/comparison_detail.html',
        {'items': items}
    )
