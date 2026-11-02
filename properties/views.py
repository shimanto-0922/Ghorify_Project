from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404

from .models import Property, PropertyImage, Utility
from . import forms


def home(request):
    return property_list(request)


def property_list(request):
    # The filter bar sends these in the URL, e.g. ?category=bachelor&gender=female
    category = request.GET.get('category', '')
    gender = request.GET.get('gender', '')
    pricing = request.GET.get('pricing', '')
    location = request.GET.get('location', '')
    sort = request.GET.get('sort', '')

    properties = Property.objects.filter(status='approved').select_related(
        'landlord__profile'
    ).prefetch_related('images', 'amenities', 'utilities')
    if category:
        properties = properties.filter(category=category)
    if gender:
        properties = properties.filter(tenant_gender__in=['any', gender])
    if pricing == 'negotiable':
        properties = properties.filter(is_negotiable=True)
    if pricing == 'fixed':
        properties = properties.filter(is_negotiable=False)
    if location:
        properties = properties.filter(location__iexact=location)

    if sort == 'price_low':
        properties = properties.order_by('price')
    elif sort == 'price_high':
        properties = properties.order_by('-price')
    else:
        properties = properties.order_by('-created_at')

    # Bachelor posts are split by gender, so we ask "Male or Female?" first
    if category == 'bachelor' and not gender:
        properties = Property.objects.none()

    page = Paginator(properties, 12).get_page(request.GET.get('page'))
    query_string = request.GET.copy()
    query_string.pop('page', None)

    return render(
        request,
        'properties/browse.html',
        {
            'page': page,
            'query_string': query_string.urlencode(),
            'categories': Property.CATEGORY_CHOICES,
            'active_category': category,
            'active_gender': gender,
            'active_pricing': pricing,
            'areas': forms.POPULAR_AREAS,
        }
    )


def property_detail(request, property_id):
    prop = get_object_or_404(
        Property.objects.select_related('landlord', 'landlord__profile').prefetch_related(
            'images', 'utilities', 'amenities'
        ),
        id=property_id
    )
    user = request.user
    is_owner = user.is_authenticated and prop.landlord_id == user.id
    is_admin = user.is_authenticated and user.is_platform_admin

    # Pending or rejected posts are only seen by the owner and the admin
    if prop.status != 'approved' and not (is_owner or is_admin):
        raise Http404('This listing is not available.')

    return render(
        request,
        'properties/detail.html',
        {'property': prop}
    )


# ---------------------------------------------------------------------------
# Property CRUD (the logged in user's own posts)
# ---------------------------------------------------------------------------

@login_required
def my_properties(request):
    if request.user.is_platform_admin:
        messages.error(request, 'This page is for user accounts.')
        return redirect('dashboard:home')

    properties = request.user.properties.prefetch_related('images').order_by('-created_at')
    status = request.GET.get('status')
    if status in ['pending', 'approved', 'rejected']:
        properties = properties.filter(status=status)
    return render(
        request,
        'properties/my_properties.html',
        {'properties': properties, 'active_status': status}
    )


@login_required
def property_create(request):
    if request.user.is_platform_admin:
        messages.error(request, 'This page is for user accounts.')
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = forms.PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.landlord = request.user
            prop.status = 'pending'
            prop.save()
            form.save_m2m()
            # The first photo becomes the cover photo
            first = True
            for photo in request.FILES.getlist('photos'):
                PropertyImage.objects.create(property=prop, image=photo, is_primary=first)
                first = False
            messages.success(request, 'Listing created. It will be visible to tenants after admin approval.')
            return redirect('properties:utility_list', property_id=prop.id)
    else:
        form = forms.PropertyForm()
    return render(
        request,
        'properties/property_form.html',
        {'form': form, 'is_edit': False}
    )


@login_required
def property_update(request, property_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    if request.method == 'POST':
        form = forms.PropertyForm(request.POST, request.FILES, instance=prop)
        if form.is_valid():
            prop = form.save(commit=False)
            # A rejected post goes back to the admin after it is fixed
            if prop.status == 'rejected':
                prop.status = 'pending'
                prop.moderation_note = ''
                messages.info(request, 'Your changes were sent back to the admin for another review.')
            prop.save()
            form.save_m2m()
            # A new photo becomes the cover only if the post has no cover yet
            first = not prop.images.filter(is_primary=True).exists()
            for photo in request.FILES.getlist('photos'):
                PropertyImage.objects.create(property=prop, image=photo, is_primary=first)
                first = False
            messages.success(request, 'Listing updated.')
            return redirect('properties:property_detail', property_id=prop.id)
    else:
        form = forms.PropertyForm(instance=prop)
    return render(
        request,
        'properties/property_form.html',
        {'form': form, 'is_edit': True, 'property': prop}
    )


@login_required
def property_delete(request, property_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    if request.method == 'POST':
        # Remove the photo files from the media folder too
        for image in prop.images.all():
            image.image.delete(save=False)
        title = prop.title
        prop.delete()
        messages.success(request, f'"{title}" has been deleted.')
        return redirect('properties:my_properties')
    return render(
        request,
        'properties/property_confirm_delete.html',
        {'property': prop}
    )


# ---------------------------------------------------------------------------
# Photo CRUD (media files)
# ---------------------------------------------------------------------------

@login_required
def image_list(request, property_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    if request.method == 'POST':
        form = forms.PropertyImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.property = prop
            if not prop.images.exists():
                image.is_primary = True
            if image.is_primary:
                # Only one cover photo per property
                prop.images.update(is_primary=False)
            image.save()
            messages.success(request, 'Photo uploaded.')
            return redirect('properties:image_list', property_id=prop.id)
    else:
        form = forms.PropertyImageForm()
    return render(
        request,
        'properties/manage_images.html',
        {'property': prop, 'form': form, 'images': prop.images.all()}
    )


@login_required
def image_update(request, property_id, image_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    image = get_object_or_404(PropertyImage, id=image_id, property=prop)
    if request.method == 'POST':
        old_file = image.image.name
        form = forms.PropertyImageForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            new_file_uploaded = 'image' in form.changed_data
            image = form.save(commit=False)
            if image.is_primary:
                prop.images.exclude(id=image.id).update(is_primary=False)
            image.save()
            # Delete the old file when a new one replaced it
            if new_file_uploaded and old_file:
                image.image.storage.delete(old_file)
            messages.success(request, 'Photo updated.')
            return redirect('properties:image_list', property_id=prop.id)
    else:
        form = forms.PropertyImageForm(instance=image)
    return render(
        request,
        'properties/image_form.html',
        {'property': prop, 'form': form, 'image': image}
    )


@login_required
def image_delete(request, property_id, image_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    image = get_object_or_404(PropertyImage, id=image_id, property=prop)
    if request.method == 'POST':
        if prop.images.count() == 1:
            messages.error(request, 'A listing needs at least one photo. Upload another photo before deleting this one.')
            return redirect('properties:image_list', property_id=prop.id)
        was_cover = image.is_primary
        image.image.delete(save=False)
        image.delete()
        # If the cover photo was deleted, the next photo becomes the cover
        if was_cover:
            next_image = prop.images.first()
            next_image.is_primary = True
            next_image.save()
        messages.success(request, 'Photo deleted.')
    return redirect('properties:image_list', property_id=prop.id)


@login_required
def image_make_primary(request, property_id, image_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    image = get_object_or_404(PropertyImage, id=image_id, property=prop)
    if request.method == 'POST':
        prop.images.update(is_primary=False)
        image.is_primary = True
        image.save()
        messages.success(request, 'Cover photo changed.')
    return redirect('properties:image_list', property_id=prop.id)


# ---------------------------------------------------------------------------
# Utility CRUD (bills used for the monthly cost)
# ---------------------------------------------------------------------------

@login_required
def utility_list(request, property_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    if request.method == 'POST':
        # The new bill already knows its property, so the form can check for duplicates
        form = forms.UtilityForm(request.POST, instance=Utility(property=prop))
        if form.is_valid():
            utility = form.save()
            messages.success(request, f'{utility.get_name_display()} added.')
            return redirect('properties:utility_list', property_id=prop.id)
    else:
        form = forms.UtilityForm()
    return render(
        request,
        'properties/manage_utilities.html',
        {'property': prop, 'form': form, 'utilities': prop.utilities.all()}
    )


@login_required
def utility_update(request, property_id, utility_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    utility = get_object_or_404(Utility, id=utility_id, property=prop)
    if request.method == 'POST':
        form = forms.UtilityForm(request.POST, instance=utility)
        if form.is_valid():
            form.save()
            messages.success(request, 'Utility updated.')
            return redirect('properties:utility_list', property_id=prop.id)
    else:
        form = forms.UtilityForm(instance=utility)
    return render(
        request,
        'properties/utility_form.html',
        {'property': prop, 'form': form, 'utility': utility}
    )


@login_required
def utility_delete(request, property_id, utility_id):
    prop = get_object_or_404(Property, id=property_id, landlord=request.user)
    utility = get_object_or_404(Utility, id=utility_id, property=prop)
    if request.method == 'POST':
        utility.delete()
        messages.success(request, 'Utility removed.')
    return redirect('properties:utility_list', property_id=prop.id)
