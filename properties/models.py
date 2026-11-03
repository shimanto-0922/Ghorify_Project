from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator

from accounts.models import User


class Amenity(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Property(models.Model):
    TYPE_CHOICES = [
        ('apartment', 'Apartment / Flat'),
        ('house', 'Full house'),
        ('room', 'Single room'),
    ]
    CATEGORY_CHOICES = [
        ('family', 'Family'),
        ('bachelor', 'Bachelor'),
        ('sublet', 'Sublet'),
    ]
    GENDER_CHOICES = [
        ('any', 'Anyone'),
        ('male', 'Male only'),
        ('female', 'Female only'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending review'),
        ('approved', 'Published'),
        ('rejected', 'Rejected'),
    ]

    landlord = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='properties'
        # related_name='properties' lets us write user.properties.all()
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    property_type = models.CharField(max_length=12, choices=TYPE_CHOICES, default='apartment')
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='family')
    location = models.CharField(max_length=80)
    address = models.CharField(max_length=255)
    price = models.PositiveIntegerField(validators=[MinValueValidator(500)])
    is_negotiable = models.BooleanField(default=False)
    service_charge = models.PositiveIntegerField(default=0, blank=True)
    advance_months = models.PositiveSmallIntegerField(default=2)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.PositiveSmallIntegerField(default=1)
    balconies = models.PositiveSmallIntegerField(default=0)
    floor = models.SmallIntegerField(default=1)
    pet_friendly = models.BooleanField(default=False)
    parking = models.BooleanField(default=False)
    amenities = models.ManyToManyField(Amenity, blank=True, related_name='properties')
    tenant_gender = models.CharField(max_length=6, choices=GENDER_CHOICES, default='any')
    house_rules = models.TextField(blank=True)
    available_from = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    moderation_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def monthly_cost(self):
        # Rent + service charge + every bill the tenant pays separately
        total = Decimal(self.price) + Decimal(self.service_charge)
        for utility in self.utilities.all():
            if not utility.included_in_rent:
                total += utility.monthly_amount()
        return total

    @property
    def advance_amount(self):
        return self.price * self.advance_months

    @property
    def primary_image(self):
        # The cover photo (images are ordered with the cover first)
        return self.images.all().first()


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='properties/')
    caption = models.CharField(max_length=120, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # The cover photo comes first
        ordering = ['-is_primary', 'uploaded_at']

    def __str__(self):
        return f'Image for {self.property}'


class Utility(models.Model):
    NAME_CHOICES = [
        ('electricity', 'Electricity'),
        ('gas', 'Gas'),
        ('water', 'Water'),
        ('internet', 'Internet'),
        ('garbage', 'Garbage / cleaning'),
        ('security', 'Security guard'),
        ('other', 'Other'),
    ]
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='utilities'
    )
    name = models.CharField(max_length=15, choices=NAME_CHOICES)
    amount = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(0)])
    billing_period = models.CharField(max_length=8, choices=PERIOD_CHOICES, default='monthly')
    included_in_rent = models.BooleanField(default=False)
    note = models.CharField(max_length=120, blank=True)
    created_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.get_name_display()} - {self.property}'

    # A normal method, because the field named 'property' hides the @property decorator here
    def monthly_amount(self):
        if self.billing_period == 'yearly':
            return (self.amount / 12).quantize(Decimal('0.01'))
        return self.amount
