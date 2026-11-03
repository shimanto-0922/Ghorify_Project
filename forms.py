from django import forms

from properties.models import Amenity, Property


class SmartMatchForm(forms.Form):
    # What the user wants. Every field is optional.
    location = forms.CharField(
        required=False,
        max_length=80,
        label='Area',
        widget=forms.TextInput(attrs={'list': 'area-list', 'autocomplete': 'off', 'placeholder': 'Any area in Dhaka'})
    )
    category = forms.ChoiceField(required=False, choices=[('', 'Any')] + Property.CATEGORY_CHOICES)
    property_type = forms.ChoiceField(required=False, label='Type', choices=[('', 'Any')] + Property.TYPE_CHOICES)
    min_price = forms.IntegerField(required=False, min_value=0, widget=forms.NumberInput(attrs={'placeholder': 'Min'}))
    max_price = forms.IntegerField(required=False, min_value=0, widget=forms.NumberInput(attrs={'placeholder': 'Max'}))
    budget_includes_bills = forms.BooleanField(
        required=False,
        help_text='Compare the budget with rent + service charge + utilities.'
    )
    min_bedrooms = forms.IntegerField(required=False, min_value=0, label='Min beds')
    min_bathrooms = forms.IntegerField(required=False, min_value=0, label='Min baths')
    tenant_gender = forms.ChoiceField(
        required=False,
        label='I am',
        choices=[('', 'Prefer not to say'), ('male', 'Male'), ('female', 'Female')],
        help_text='Hides male-only or female-only listings that do not fit you.'
    )
    needs_parking = forms.BooleanField(required=False, label='Parking required')
    needs_pet_friendly = forms.BooleanField(required=False, label='Pet friendly required')
    amenities = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Amenity.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        if min_price and max_price and min_price > max_price:
            self.add_error('max_price', 'Maximum rent must be higher than the minimum.')
        return cleaned_data
