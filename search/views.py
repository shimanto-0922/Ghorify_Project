from django.core.paginator import Paginator
from django.shortcuts import render

from properties.models import Property
from . import forms
from .matching import smart_match


def search(request):
    has_query = False
    for key in request.GET:
        if key != 'page':
            has_query = True

    if has_query:
        form = forms.SmartMatchForm(request.GET)
    else:
        form = forms.SmartMatchForm()

    page = None
    total = 0
    if has_query and form.is_valid():
        prefs = form.cleaned_data
        properties = Property.objects.filter(status='approved').prefetch_related(
            'images', 'amenities', 'utilities'
        ).order_by('-created_at')
        results = smart_match(properties, prefs)
        total = len(results)
        page = Paginator(results, 9).get_page(request.GET.get('page'))

    query_string = request.GET.copy()
    query_string.pop('page', None)
    return render(
        request,
        'search/search.html',
        {
            'form': form,
            'page': page,
            'total': total,
            'has_query': has_query,
            'query_string': query_string.urlencode(),
        }
    )
