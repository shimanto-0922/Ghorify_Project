"""Fill the database with realistic demo data for presentations.

    python manage.py seed_demo          # add demo data
    python manage.py seed_demo --reset  # wipe demo users first

Every demo account uses the password: ghorify123
Listing photos are real photos from Bangladesh (static/img/photos/bd_*.jpg, see CREDITS.md).
"""
import io
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from accounts.models import Profile, User
from interactions.models import Comparison, ComparisonItem, Favourite
from properties.models import Amenity, Property, PropertyImage, Utility

PASSWORD = 'ghorify123'
PHOTO_DIR = Path(settings.BASE_DIR) / 'static' / 'img' / 'photos'

AMENITIES = [
    'Lift', 'Gas line', 'WiFi ready', '24/7 security', 'CCTV', 'Rooftop access', '24/7 water supply',
    'Near school', 'Near hospital',
]

# Demo ads written like real to-let posts in Dhaka. Photos are real photos from Bangladesh
# (static/img/photos/bd_*.jpg, see CREDITS.md there). The first photo is the cover.
# title, area, type, category, rent, service charge, beds, baths, balconies, floor,
# pets, parking, who can rent, negotiable, photos, description
LISTINGS = [
    ('To-Let: 3 Bed Family Flat near Dhanmondi Lake, Road 8/A', 'Dhanmondi', 'apartment', 'family',
     38000, 3000, 3, 3, 2, 5, False, True, 'any', False,
     ['bd_building_1', 'bd_bed_1', 'bd_dining_1', 'bd_view_1'],
     '3 bed, 3 bath, drawing-dining and 2 balconies on the 5th floor. South facing, lots of light and air.\n\n'
     'Lift, 24 hour water, gas line, guard and 1 car parking. Dhanmondi Lake, school and kacha bazar are '
     '5 minutes away on foot. Only for a small family. 2 months advance.'),
    ('Family Flat for Rent at Gulshan 2, Road 55 (Lake View)', 'Gulshan', 'apartment', 'family',
     85000, 8000, 3, 4, 3, 8, True, True, 'any', True,
     ['bd_building_6', 'bd_bed_3', 'bd_view_5', 'bd_bed_4'],
     'Lake view apartment with 3 bed, 4 bath and 3 balconies. Wide drawing room, separate dining and a big '
     'kitchen.\n\nTwo lifts, CCTV, 24/7 security, car parking and rooftop access. Near Gulshan 2 circle. '
     'Rent is a little negotiable for a long stay.'),
    ('Bachelor Seat Available - Mirpur 10 (Male, Job Holder)', 'Mirpur', 'room', 'bachelor',
     5500, 500, 1, 1, 1, 4, False, False, 'male', True,
     ['bd_building_8', 'bd_bed_9', 'bd_bed_10'],
     'One seat in a 2 seat room for a male job holder or student. Shared bathroom, kitchen with gas line and '
     'a balcony.\n\nWiFi ready, the bua (maid) for cooking can be shared. 3 minutes walk from Mirpur 10 metro '
     'station. Only for non-smokers.'),
    ('Duplex House with Rooftop Garden - Uttara Sector 4', 'Uttara', 'house', 'family',
     65000, 4000, 4, 4, 3, 2, True, True, 'any', True,
     ['bd_house_3', 'bd_bed_8', 'bd_roof_1', 'bd_dining_1'],
     'Two floor duplex house with 4 bed, 4 bath, a family living room and a private rooftop garden.\n\n'
     'Own car garage, CCTV and guard. Very calm road, park and mosque nearby. Good for a big family.'),
    ('2 Bed Small Family Flat - Mohammadpur Tajmahal Road', 'Mohammadpur', 'apartment', 'family',
     18000, 1500, 2, 2, 1, 3, False, False, 'any', True,
     ['bd_building_13', 'bd_bed_2', 'bd_view_4'],
     '2 bed, 2 bath, drawing-dining and 1 balcony on the 3rd floor. Tiles floor, gas line, 24 hour water.\n\n'
     'Near Tajmahal Road, school and bazar. Small family only. 2 months advance.'),
    ('Sublet: 1 Room for Female Student or Job Holder - Lalmatia', 'Lalmatia', 'room', 'sublet',
     8000, 0, 1, 1, 1, 3, False, False, 'any', True,
     ['bd_building_14', 'bd_bed_5', 'bd_bed_6'],
     'One big room inside our family flat with an attached bathroom and a balcony. Bed, table and almirah '
     'are in the room.\n\nKitchen is shared with a small family. Gas and water bills are included. Very '
     'safe area near Lalmatia Mohila College.'),
    ('New Flat for Rent - Bashundhara R/A, Block C', 'Bashundhara', 'apartment', 'family',
     32000, 3500, 3, 3, 2, 6, False, True, 'any', False,
     ['bd_building_2', 'bd_bed_4', 'bd_view_2', 'bd_bed_3'],
     'Brand new 3 bed flat, first tenant. 2 balconies, drawing, dining and a big kitchen.\n\n'
     'Lift, 24/7 security, CCTV and car parking. Near NSU, AIUB and Jamuna Future Park. Family only.'),
    ('Bachelor Mess Seat for Students - Badda, Near Brac University', 'Badda', 'apartment', 'bachelor',
     4500, 500, 3, 2, 1, 5, False, False, 'male', True,
     ['bd_building_12', 'bd_bed_10', 'bd_bed_9'],
     'Seats available in a student mess. 3 rooms, 2 bathrooms and a shared kitchen.\n\nMeal system with a '
     'bua, WiFi and filtered water. Walking distance to Brac University and Merul Badda bus stand.'),
    ('Full House for Rent in Baridhara (Diplomatic Zone)', 'Baridhara', 'house', 'family',
     150000, 10000, 5, 5, 4, 0, True, True, 'any', False,
     ['bd_house_2', 'bd_bed_1', 'bd_dining_1', 'bd_bed_8'],
     'Independent house with 5 bed, 5 bath, a big lawn and a garage for 2 cars.\n\n'
     'Quiet diplomatic area with 24/7 security. Suitable for an expat family or a large family. '
     '3 months advance.'),
    ('Female Seat Available - Farmgate, Near Tejgaon College', 'Farmgate', 'room', 'bachelor',
     6000, 300, 1, 1, 1, 4, False, False, 'female', True,
     ['bd_building_9', 'bd_bed_6', 'bd_bed_7'],
     'Seat in a 2 seat room for a female student or job holder. Shared bathroom and kitchen.\n\n'
     'Female only flat with a guard and gate lock at 10 PM. Very near Farmgate bus stand and metro station.'),
    ('2 Room Flat for Working Women - Mirpur 2', 'Mirpur', 'apartment', 'bachelor',
     14000, 1000, 2, 2, 1, 5, False, False, 'female', False,
     ['bd_building_7', 'bd_bed_5', 'bd_view_3'],
     '2 rooms, 2 bathrooms, a kitchen and a balcony. Good for 2 to 4 working women sharing.\n\n'
     'Lift, 24 hour water, gas line and a guard. Near Mirpur 2 stadium and the bus stand.'),
    ('Single Room for Female Student - Banani Road 11', 'Banani', 'room', 'bachelor',
     8500, 500, 1, 1, 0, 3, False, False, 'female', True,
     ['bd_house_1', 'bd_bed_7', 'bd_bed_2'],
     'Single room with an attached bathroom for a female student. Shared kitchen.\n\n'
     'WiFi, CCTV and a guard at the gate. Near Banani Road 11 and Gulshan Avenue.'),
    ('3 Bed Flat for Rent - Shyamoli Ring Road', 'Shyamoli', 'apartment', 'family',
     25000, 2000, 3, 2, 2, 4, False, True, 'any', True,
     ['bd_building_4', 'bd_bed_4', 'bd_view_6'],
     '3 bed, 2 bath, drawing-dining and 2 balconies. Gas line, 24 hour water and a lift.\n\n'
     'Near Shyamoli Square, Ring Road and Kallyanpur bus stand. Family only.'),
    ('Sublet for Small Family or Couple - Khilgaon Taltola', 'Khilgaon', 'room', 'sublet',
     9000, 0, 1, 1, 1, 2, False, False, 'any', True,
     ['bd_building_10', 'bd_bed_3', 'bd_dining_1'],
     'One room with a balcony and an attached bathroom inside a family flat. Good for a couple or a small '
     'family.\n\nKitchen is shared. Gas and water bills are included in the rent. Near Taltola market.'),
    ('Family Flat Near Rampura Bridge, Banasree Road', 'Rampura', 'apartment', 'family',
     20000, 1500, 2, 2, 1, 6, False, False, 'any', True,
     ['bd_building_11', 'bd_bed_2', 'bd_roof_2'],
     '2 bed, 2 bath and 1 balcony on the 6th floor. Lift, gas line and rooftop access.\n\n'
     'Near Rampura Bridge, Banasree Road and the school. Small family only.'),
    ('To-Let: 3 Bed Apartment - Tejgaon, Near Karwan Bazar', 'Tejgaon', 'apartment', 'family',
     28000, 2500, 3, 3, 2, 7, False, True, 'any', False,
     ['bd_building_3', 'bd_bed_1', 'bd_view_1'],
     '3 bed, 3 bath, 2 balconies, drawing and dining. Lift and car parking.\n\n'
     'Walking distance to Karwan Bazar and Farmgate. Good for office goers.'),
]

CAPTIONS = {
    'building': 'Building front', 'house': 'Front view', 'bed': 'Bedroom', 'dining': 'Dining',
    'view': 'View from the balcony', 'roof': 'Rooftop',
}

# Words in the ad text and the amenity they mean
AMENITY_WORDS = [
    ('lift', 'Lift'), ('gas line', 'Gas line'), ('gas and water bills', 'Gas line'),
    ('24 hour water', '24/7 water supply'), ('filtered water', '24/7 water supply'), ('water bills', '24/7 water supply'),
    ('wifi', 'WiFi ready'), ('guard', '24/7 security'), ('24/7 security', '24/7 security'),
    ('cctv', 'CCTV'), ('rooftop', 'Rooftop access'), ('school', 'Near school'), ('college', 'Near school'),
    ('university', 'Near school'), ('hospital', 'Near hospital'),
]

# The listing numbers (from 0) posted by the unverified demo user, so they stay pending
PENDING_LISTINGS = [4, 13]

RULES = {
    'family': 'No loud music after 11 PM.\nVisitors should inform the caretaker.\nNo smoking in common areas.',
    'bachelor': 'Guests allowed until 10 PM.\nKeep the shared kitchen clean.\nNo smoking inside rooms.',
    'sublet': 'Guests must leave by 9 PM.\nShared kitchen with the host family.\nKeep noise low after 10 PM.',
}


def photo_file(name):
    return ContentFile((PHOTO_DIR / f'{name}.jpg').read_bytes(), name=f'{name}.jpg')


def make_document(text):
    """A simple fake NID scan so the verification screen has something to open."""
    img = Image.new('RGB', (900, 560), (236, 246, 243))
    d = ImageDraw.Draw(img)
    d.rectangle((20, 20, 880, 540), outline=(15, 118, 110), width=6)
    d.rectangle((60, 120, 300, 420), fill=(205, 235, 229))
    d.text((340, 120), 'GOVERNMENT OF THE PEOPLE\'S REPUBLIC OF BANGLADESH', fill=(15, 23, 42))
    d.text((340, 160), 'NATIONAL ID CARD  (DEMO)', fill=(15, 118, 110))
    d.text((340, 220), text, fill=(15, 23, 42))
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=80)
    return ContentFile(buf.getvalue(), name='nid.jpg')


class Command(BaseCommand):
    help = 'Create demo users, listings, photos and interactions.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing demo data first.')

    def user(self, name, first, last, role, **extra):
        # Normal users log in with their phone number, so it is also their username
        username = extra.get('phone') or name
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'first_name': first, 'last_name': last, 'role': role,
                      'email': f'{name}@ghorify.test', **extra},
        )
        if created:
            user.set_password(PASSWORD)
            user.save()
        if role == 'user':
            Profile.objects.get_or_create(user=user)
        return user

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts['reset']:
            for image in PropertyImage.objects.filter(property__landlord__email__endswith='@ghorify.test'):
                image.image.delete(save=False)
            User.objects.filter(email__endswith='@ghorify.test').delete()
            Amenity.objects.all().delete()
            self.stdout.write('Old demo data removed.')

        amenities = {}
        for name in AMENITIES:
            amenities[name] = Amenity.objects.get_or_create(name=name)[0]

        admin = self.user('admin', 'Ghorify', 'Admin', 'admin', is_staff=True, is_superuser=True)
        # Demo users who post homes (rahim and nasrin are verified, kamal is waiting).
        landlords = [
            self.user('rahim', 'Rahim', 'Uddin', 'user', phone='01711000001'),
            self.user('nasrin', 'Nasrin', 'Akter', 'user', phone='01811000002'),
            self.user('kamal', 'Kamal', 'Hossain', 'user', phone='01911000003'),
        ]
        for i, landlord in enumerate(landlords):
            profile = landlord.profile
            if not profile.nid_document:
                profile.nid_document.save(f'nid_{landlord.first_name.lower()}.jpg',
                                               make_document(f'Name: {landlord.get_full_name()}'), save=False)
            profile.save()
            if i < 2:
                profile.status = 'verified'
                profile.verified_by = admin
                profile.verified_at = timezone.now()
            else:
                profile.status = 'pending'
            profile.save()

        # Demo users who are looking for a home.
        tenants = [
            self.user('tanvir', 'Tanvir', 'Ahmed', 'user', phone='01611000004'),
            self.user('mim', 'Mim', 'Rahman', 'user', phone='01511000005'),
            self.user('sakib', 'Sakib', 'Hasan', 'user', phone='01311000006'),
        ]

        if Property.objects.filter(landlord__in=landlords).exists():
            self.stdout.write(self.style.WARNING('Demo listings already exist. Use --reset to rebuild.'))
            return

        today = timezone.localdate()
        properties = []
        for idx, row in enumerate(LISTINGS):
            (title, area, ptype, cat, rent, service, beds, baths, balconies, floor,
             pets, park, gender, nego, photos, description) = row
            # The unverified landlord (kamal) gets a couple of listings that stay pending.
            if idx in PENDING_LISTINGS:
                landlord = landlords[2]
            else:
                landlord = landlords[idx % 2]
            prop = Property.objects.create(
                landlord=landlord, title=title, property_type=ptype, category=cat,
                tenant_gender=gender if cat == 'bachelor' else 'any',
                description=description,
                location=area, address=f'House {10 + idx}, Road {2 + idx % 9}, {area}, Dhaka',
                price=rent, is_negotiable=nego, service_charge=service, advance_months=2 if rent < 50000 else 3,
                bedrooms=beds, bathrooms=baths, balconies=balconies, floor=floor,
                pet_friendly=pets, parking=park,
                house_rules=RULES[cat],
                available_from=today + timedelta(days=idx % 4 * 7),
                status='approved' if landlord.profile.status == 'verified' else 'pending',
            )
            # Amenities follow what the ad text says
            text = description.lower()
            for word, amenity_name in AMENITY_WORDS:
                if word in text:
                    prop.amenities.add(amenities[amenity_name])

            for number, name in enumerate(photos):
                kind = name.split('_')[1]
                PropertyImage.objects.create(property=prop, image=photo_file(name), is_primary=(number == 0),
                                             caption=CAPTIONS[kind])

            Utility.objects.create(property=prop, name='electricity', amount=1500 + beds * 700)
            Utility.objects.create(property=prop, name='gas', amount=1080, included_in_rent=(cat == 'sublet'))
            Utility.objects.create(property=prop, name='water', amount=400 + beds * 100)
            if idx % 2 == 0:
                Utility.objects.create(property=prop, name='internet', amount=1000, note='40 Mbps line')
            properties.append(prop)

        live = [p for p in properties if p.status == 'approved']
        tanvir = tenants[0]
        by_title = {p.title: p for p in properties}

        for p in live[:4]:
            Favourite.objects.create(tenant=tanvir, property=p)
        compare_titles = [LISTINGS[0][0], LISTINGS[6][0], LISTINGS[3][0]]
        comparison = Comparison.objects.create(tenant=tanvir, name=' vs '.join(compare_titles)[:80])
        for position, t in enumerate(compare_titles, start=1):
            ComparisonItem.objects.create(comparison=comparison, property=by_title[t], position=position)

        self.stdout.write(self.style.SUCCESS(
            f'Demo ready: {len(properties)} listings ({len(live)} live). '
            f'Log in as admin, or with phone 01711000001 (rahim) / 01611000004 (tanvir). Password: {PASSWORD}.'))
