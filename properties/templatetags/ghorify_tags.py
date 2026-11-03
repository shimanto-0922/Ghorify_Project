from django import forms, template
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.html import format_html, format_html_join

from properties.forms import POPULAR_AREAS

register = template.Library()


@register.filter
def bs(field):
    # Give a form field the right Bootstrap class
    widget = field.field.widget
    if isinstance(widget, forms.CheckboxInput):
        css = 'form-check-input'
    elif isinstance(widget, forms.CheckboxSelectMultiple) or isinstance(widget, forms.RadioSelect):
        css = ''
    elif isinstance(widget, forms.Select) or isinstance(widget, forms.SelectMultiple):
        css = 'form-select'
    else:
        css = 'form-control'
    if field.errors:
        css += ' is-invalid'
    return field.as_widget(attrs={'class': css.strip()})


@register.filter
def widget_kind(field):
    # Used by partials/field.html to pick the right layout
    widget = field.field.widget
    if isinstance(widget, forms.CheckboxSelectMultiple):
        return 'multi'
    if isinstance(widget, forms.RadioSelect):
        return 'radio'
    if isinstance(widget, forms.CheckboxInput):
        return 'switch'
    return 'default'


@register.filter
def taka(value):
    # 12000 becomes ৳ 12,000
    if value is None or value == '':
        return '-'
    try:
        return f'৳ {intcomma(int(round(float(value))))}'
    except (TypeError, ValueError):
        return value


@register.filter
def has_amenity(prop, word):
    # True if one of the property's amenities contains the word
    for amenity in prop.amenities.all():
        if word.lower() in amenity.name.lower():
            return True
    return False


@register.filter
def reason_class(value):
    if value >= 1:
        return 'yes'
    if value > 0:
        return 'part'
    return 'no'


@register.filter
def match_color(percentage):
    if percentage >= 85:
        return '#16a34a'
    if percentage >= 65:
        return '#d97706'
    return '#64748b'


@register.simple_tag(takes_context=True)
def is_favourite(context, prop):
    # True when the logged in user has saved this property
    request = context.get('request')
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or user.is_platform_admin:
        return False
    # Load the saved ids once per page, not once per card
    if not hasattr(request, 'favourite_ids'):
        request.favourite_ids = set(user.favourites.values_list('property_id', flat=True))
    return prop.id in request.favourite_ids


@register.simple_tag
def area_datalist():
    options = format_html_join('', '<option value="{}">', ((area,) for area in POPULAR_AREAS))
    return format_html('<datalist id="area-list">{}</datalist>', options)


@register.simple_tag
def page_url(query_string, number):
    if query_string:
        return f'?{query_string}&page={number}'
    return f'?page={number}'
