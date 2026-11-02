import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import Profile, User

from .models import Property, PropertyImage, Utility

TEMP_MEDIA = tempfile.mkdtemp()


def fake_image(name='photo.jpg'):
    buf = io.BytesIO()
    Image.new('RGB', (40, 30), (200, 100, 50)).save(buf, 'JPEG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/jpeg')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class PropertyCrudTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.landlord = User.objects.create_user('ll', 'll@x.com', 'pw')
        self.client.force_login(self.landlord)
        self.data = {
            'title': 'Test flat', 'property_type': 'apartment', 'category': 'family', 'description': 'desc',
            'location': 'Uttara', 'address': 'Road 3', 'price': 25000, 'service_charge': 1000, 'advance_months': 2,
            'bedrooms': 2, 'bathrooms': 2, 'floor': 3,
            'division': 'dhaka', 'city': 'Dhaka', 'tenant_gender': 'any', 'balconies': 1,
        }

    def create(self):
        return self.client.post(reverse('properties:property_create'), {'photos': [fake_image()], **self.data})

    def test_who_can_rent_only_for_bachelor(self):
        self.data['tenant_gender'] = 'male'
        self.create()                                   # family post: gender is ignored
        self.data.update(category='bachelor', title='Mess')
        self.create()
        self.assertEqual(Property.objects.get(title='Test flat').tenant_gender, 'any')
        self.assertEqual(Property.objects.get(title='Mess').tenant_gender, 'male')

    def test_location_must_be_a_dhaka_area(self):
        self.data['location'] = '.,ml'
        response = self.create()
        self.assertFalse(Property.objects.exists())
        self.assertContains(response, 'Please choose an area of Dhaka')
        self.data['location'] = 'mirpur'
        self.create()
        self.assertEqual(Property.objects.get().location, 'Mirpur')

    def test_service_charge_is_optional(self):
        self.data['service_charge'] = ''
        self.create()
        self.assertEqual(Property.objects.get().service_charge, 0)

    def test_create_with_photos_starts_pending(self):
        self.data['photos'] = [fake_image('a.jpg'), fake_image('b.jpg')]
        self.create()
        prop = Property.objects.get()
        self.assertEqual(prop.status, 'pending')
        self.assertEqual(prop.images.count(), 2)
        self.assertEqual(prop.images.filter(is_primary=True).count(), 1)

    def test_pending_listing_hidden_from_public(self):
        self.create()
        prop = Property.objects.get()
        self.client.logout()
        self.assertEqual(self.client.get(reverse('properties:property_detail', args=[prop.id])).status_code, 404)

    def test_editing_rejected_listing_resubmits_it(self):
        self.create()
        prop = Property.objects.get()
        prop.status = 'rejected'
        prop.save()
        self.data['title'] = 'Fixed title'
        self.client.post(reverse('properties:property_update', args=[prop.pk]), self.data)
        prop.refresh_from_db()
        self.assertEqual((prop.title, prop.status), ('Fixed title', 'pending'))

    def test_other_landlord_cannot_edit_or_delete(self):
        self.create()
        prop = Property.objects.get()
        intruder = User.objects.create_user('xx', 'xx@x.com', 'pw')
        self.client.force_login(intruder)
        self.assertEqual(self.client.get(reverse('properties:property_update', args=[prop.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('properties:property_delete', args=[prop.pk])).status_code, 404)

    def test_deleting_cover_photo_promotes_next(self):
        self.data['photos'] = [fake_image('a.jpg'), fake_image('b.jpg')]
        self.create()
        prop = Property.objects.get()
        cover = prop.images.get(is_primary=True)
        self.client.post(reverse('properties:image_delete', args=[prop.pk, cover.pk]))
        self.assertTrue(PropertyImage.objects.get().is_primary)

    def test_post_needs_at_least_one_photo(self):
        response = self.client.post(reverse('properties:property_create'), self.data)
        self.assertFalse(Property.objects.exists())
        self.assertContains(response, 'Please add at least one photo')

    def test_last_photo_cannot_be_deleted(self):
        self.create()
        prop = Property.objects.get()
        self.client.post(reverse('properties:image_delete', args=[prop.pk, prop.images.get().pk]))
        self.assertEqual(prop.images.count(), 1)

    def test_monthly_cost_includes_only_separate_bills(self):
        self.create()
        prop = Property.objects.get()
        Utility.objects.create(property=prop, name='electricity', amount=2000)
        Utility.objects.create(property=prop, name='gas', amount=1080, included_in_rent=True)
        Utility.objects.create(property=prop, name='internet', amount=12000, billing_period='yearly')
        self.assertEqual(prop.monthly_cost, 25000 + 1000 + 2000 + 1000)

    def test_any_user_can_post_and_guests_must_log_in(self):
        other = User.objects.create_user('tt', 'tt@x.com', 'pw')
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('properties:property_create')).status_code, 200)
        self.client.logout()
        response = self.client.get(reverse('properties:property_create'))
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_admin_account_cannot_post(self):
        admin = User.objects.create_superuser('boss', 'b@x.com', 'pw')
        self.client.force_login(admin)
        self.assertRedirects(self.client.get(reverse('properties:property_create')), reverse('dashboard:home'),
                             fetch_redirect_response=False)


class SmartMatchPageTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('own', 'own@x.com', 'pw')
        make = lambda **kw: Property.objects.create(**{
            'landlord': owner, 'title': 'Flat', 'description': 'd', 'location': 'Mirpur', 'address': 'x',
            'price': 20000, 'bedrooms': 2, 'bathrooms': 1, 'floor': 3, 'status': 'approved', **kw})
        make(title='Cheap', price=8000, bedrooms=1)
        make(title='Big', price=40000, bedrooms=4, parking=True, location='Uttara')
        make(title='Mid', price=20000, bedrooms=3)

    def ranked(self, query):
        response = self.client.get(reverse('search:search') + query)
        return [(m['property'].title, m['percentage']) for m in response.context['page'].object_list], response

    def test_all_homes_in_budget_are_ranked_by_match(self):
        ranked, _ = self.ranked('?min_price=5000&max_price=45000&min_bedrooms=3&needs_parking=on')
        self.assertEqual(ranked, [('Big', 100), ('Mid', 90), ('Cheap', 60)])

    def test_homes_outside_the_budget_are_left_out(self):
        ranked, _ = self.ranked('?min_price=15000&max_price=30000')
        self.assertEqual(ranked, [('Mid', 100)])

    def test_min_budget_above_max_shows_an_error(self):
        response = self.client.get(reverse('search:search') + '?min_price=50000&max_price=10000')
        self.assertContains(response, 'Maximum rent must be higher than the minimum.')

    def test_location_list_has_every_main_dhaka_area(self):
        response = self.client.get(reverse('properties:property_list'))
        for area in ['Dhanmondi', 'Gulshan', 'Mirpur', 'Uttara', 'Mohammadpur', 'Bashundhara', 'Old Dhaka']:
            self.assertIn(area, response.context['areas'])
        self.assertNotIn('.,ml', response.context['areas'])


class ModerationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('boss', 'b@x.com', 'pw')
        self.owner = User.objects.create_user('own', 'own@x.com', 'pw')
        Profile.objects.create(user=self.owner)
        self.prop = Property.objects.create(landlord=self.owner, title='Flat', description='d', location='Mirpur',
                                            address='x', price=20000)
        self.client.force_login(self.admin)

    def approve(self):
        self.client.post(reverse('dashboard:moderate_property', args=[self.prop.pk]), {'decision': 'approve'})
        self.prop.refresh_from_db()

    def test_post_from_owner_without_documents_can_be_approved(self):
        self.approve()
        self.assertEqual(self.prop.status, 'approved')
        self.assertNotContains(self.client.get(reverse('properties:property_detail', args=[self.prop.id])), '✓ Verified')

    def test_verified_owner_gets_the_badge(self):
        self.owner.profile.status = 'verified'
        self.owner.profile.save()
        self.approve()
        self.assertContains(self.client.get(reverse('properties:property_detail', args=[self.prop.id])), '✓ Verified')
