from django import forms
from django.conf import settings

from .models import Property, PropertyImage, Utility


# Ghorify only covers Dhaka city
POPULAR_AREAS = [
    'Adabor', 'Aftabnagar', 'Agargaon', 'Azimpur', 'Badda', 'Banani', 'Banasree', 'Baridhara',
    'Baridhara DOHS', 'Basabo', 'Bashundhara', 'Cantonment', 'Demra', 'Dhanmondi', 'Eskaton',
    'Farmgate', 'Gulshan', 'Hazaribagh', 'Jatrabari', 'Kafrul', 'Kalabagan', 'Kamrangirchar',
    'Karwan Bazar', 'Khilgaon', 'Khilkhet', 'Kuril', 'Lalbagh', 'Lalmatia', 'Malibagh', 'Mirpur',
    'Mirpur DOHS', 'Moghbazar', 'Mohakhali', 'Mohakhali DOHS', 'Mohammadpur', 'Motijheel', 'Mugda',
    'Niketan', 'Nikunja', 'Old Dhaka', 'Pallabi', 'Paltan', 'Panthapath', 'Rampura', 'Segunbagicha',
    'Shahbag', 'Shantinagar', 'Sher-e-Bangla Nagar', 'Shyamoli', 'Shyampur', 'Sutrapur', 'Tejgaon',
    'Uttara', 'Wari',
]

MAX_PHOTOS = 10


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'title', 'property_type', 'category', 'tenant_gender', 'description',
            'location', 'address',
            'price', 'is_negotiable', 'service_charge', 'advance_months',
            'bedrooms', 'bathrooms', 'balconies', 'floor',
            'pet_friendly', 'parking', 'amenities',
            'house_rules', 'available_from',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'house_rules': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'e.g. No guests after 10 PM, no smoking inside'}
            ),
            'location': forms.TextInput(attrs={'list': 'area-list', 'autocomplete': 'off'}),
            'available_from': forms.DateInput(attrs={'type': 'date'}),
            'amenities': forms.CheckboxSelectMultiple,
        }
        labels = {
            'location': 'Area',
            'price': 'Monthly rent (BDT)',
            'is_negotiable': 'Rent is negotiable',
            'service_charge': 'Service charge (BDT / month)',
            'advance_months': 'Advance (months)',
            'tenant_gender': 'Who can rent',
        }
        help_texts = {
            'location': 'Area in Dhaka, e.g. Dhanmondi',
            'address': 'Road / house number. Shown only to tenants after approval.',
            'floor': '0 for ground floor',
            'tenant_gender': 'Only for bachelor listings.',
            'house_rules': 'Guest policy, smoking, cooking rules, etc.',
        }

    def clean_location(self):
        # The area must be one of the Dhaka areas in our list
        typed = self.cleaned_data['location'].strip()
        for area in POPULAR_AREAS:
            if area.lower() == typed.lower():
                return area
        raise forms.ValidationError('Please choose an area of Dhaka from the list, e.g. Dhanmondi or Mirpur.')

    def clean_service_charge(self):
        # Service charge is optional, an empty box means 0
        return self.cleaned_data.get('service_charge') or 0

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        bedrooms = cleaned_data.get('bedrooms')

        if category == 'family' and bedrooms == 0:
            self.add_error('bedrooms', 'A family listing needs at least one bedroom.')

        # "Who can rent" is only asked for bachelor posts
        if category != 'bachelor':
            cleaned_data['tenant_gender'] = 'any'

        # Every post needs at least one photo
        photos = self.files.getlist('photos')
        existing = 0
        if self.instance.id:
            existing = self.instance.images.count()
        if existing + len(photos) == 0:
            self.add_error(None, 'Please add at least one photo of the property.')
        elif existing + len(photos) > MAX_PHOTOS:
            self.add_error(None, f'A property can have at most {MAX_PHOTOS} photos.')
        else:
            for photo in photos:
                image_form = PropertyImageForm(data={}, files={'image': photo})
                if not image_form.is_valid():
                    self.add_error(None, image_form.errors['image'][0])
                    break
        return cleaned_data


class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = PropertyImage
        fields = ['image', 'caption', 'is_primary']

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > settings.MAX_UPLOAD_SIZE:
            raise forms.ValidationError(f'"{image.name}" is larger than 5 MB.')
        return image


class UtilityForm(forms.ModelForm):
    class Meta:
        model = Utility
        fields = ['name', 'amount', 'billing_period', 'included_in_rent', 'note']
        labels = {
            'amount': 'Estimated amount (BDT)',
        }
        help_texts = {
            'included_in_rent': 'Tick if the rent already covers this bill.',
        }

    def clean_name(self):
        # The same bill cannot be added twice to a property (except "Other")
        name = self.cleaned_data['name']
        same_bill = Utility.objects.filter(property=self.instance.property, name=name).exclude(id=self.instance.id)
        if name != 'other' and same_bill.exists():
            raise forms.ValidationError('This utility is already listed. Edit the existing one instead.')
        return name
