from django import forms
from django.conf import settings
from django.contrib.auth.password_validation import validate_password

from .models import Profile, User


def normalize_phone(value):
    # '+880 1712-345678' or '8801712345678' becomes '01712345678'
    digits = ''
    for ch in str(value):
        if ch.isdigit():
            digits += ch
    if digits.startswith('880'):
        digits = digits[2:]
    return digits


class UserUpdateForm(forms.ModelForm):
    # Edit your own account on the profile page
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'avatar', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError('An account with this email already exists.')
        # Save NULL instead of '' so many users can skip the email
        return email or None

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get('phone') or '')
        if not phone:
            return phone
        # A Bangladeshi mobile number: 11 digits like 01712345678
        if len(phone) != 11 or not phone.startswith('01') or phone[2] not in '3456789':
            raise forms.ValidationError('Enter a valid Bangladeshi mobile number, e.g. 01712345678.')
        if User.objects.filter(phone=phone).exclude(id=self.instance.id).exists():
            raise forms.ValidationError('This phone number already has an account. Please log in instead.')
        return phone

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if 'avatar' in self.changed_data and avatar and avatar.size > settings.MAX_UPLOAD_SIZE:
            raise forms.ValidationError('File is too large. Maximum size is 5 MB.')
        return avatar


class RegisterForm(UserUpdateForm):
    # Quick sign up: name, phone number and password. Email is optional.
    # It uses the same email and phone checks as UserUpdateForm.
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email']
        labels = {
            'first_name': 'Name',
            'phone': 'Phone number',
            'email': 'Email (optional)',
        }

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name', '').strip()
        if not name:
            raise forms.ValidationError('Please write your name.')
        return name

    def clean_phone(self):
        phone = super().clean_phone()
        if not phone:
            raise forms.ValidationError('Enter a valid Bangladeshi mobile number, e.g. 01712345678.')
        # The phone number is also used as the username
        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError('This phone number already has an account. Please log in instead.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'The two passwords do not match.')
        elif password1:
            try:
                validate_password(password1)
            except forms.ValidationError as error:
                self.add_error('password1', error)
        return cleaned_data


class ProfileForm(forms.ModelForm):
    # NID or Birth Certificate. Everything here is optional.
    class Meta:
        model = Profile
        fields = ['nid_document', 'birth_certificate']
        labels = {
            'nid_document': 'NID',
        }

    def clean(self):
        cleaned_data = super().clean()
        # Only PDF, JPG or PNG files for both documents
        for name in ['nid_document', 'birth_certificate']:
            document = cleaned_data.get(name)
            if name in self.changed_data and document:
                if document.name.rsplit('.', 1)[-1].lower() not in ['pdf', 'jpg', 'jpeg', 'png']:
                    self.add_error(name, 'Only PDF, JPG or PNG files are accepted.')
        return cleaned_data
