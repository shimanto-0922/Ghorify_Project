from django.test import TestCase

from accounts.models import User
from properties.models import Amenity, Property, Utility

from .matching import score_property, smart_match


def make_property(landlord, **overrides):
    data = dict(landlord=landlord, title='Flat', description='Nice', location='Dhanmondi', address='Road 1',
                price=30000, service_charge=2000, bedrooms=3, bathrooms=2, status='approved')
    data.update(overrides)
    return Property.objects.create(**data)


def visible():
    return Property.objects.filter(status='approved')


class MatchEngineTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user('ll', 'll@x.com', 'pw')
        self.flat = make_property(self.landlord, parking=True)

    def test_perfect_match_is_100(self):
        result = score_property(self.flat, {'location': 'Dhanmondi', 'max_price': 35000, 'min_bedrooms': 3})
        self.assertEqual(result['percentage'], 100)

    def test_empty_preferences_do_not_lower_score(self):
        self.assertEqual(score_property(self.flat, {})['percentage'], 100)

    def test_slightly_over_budget_gets_partial_points(self):
        # 30000 rent vs 28000 budget is ~7% over -> half of the 30 budget points
        result = score_property(self.flat, {'max_price': 28000, 'location': 'Dhanmondi'})
        self.assertEqual(result['percentage'], round((15 + 20) / 50 * 100))

    def test_budget_can_include_bills(self):
        Utility.objects.create(property=self.flat, name='electricity', amount=4000)
        prefs = {'max_price': 33000, 'budget_includes_bills': True}
        # 30000 + 2000 + 4000 = 36000 -> more than 10% over 33000
        self.assertLess(score_property(self.flat, prefs)['percentage'], 100)
        self.assertEqual(score_property(self.flat, {'max_price': 33000})['percentage'], 100)

    def test_amenities_score_is_proportional(self):
        lift, wifi = Amenity.objects.create(name='Lift'), Amenity.objects.create(name='WiFi')
        self.flat.amenities.add(lift)
        result = score_property(self.flat, {'amenities': [lift, wifi]})
        self.assertEqual(result['percentage'], 50)

    def test_gender_restricted_listing_is_hidden_from_other_gender(self):
        male_only = make_property(self.landlord, title='Mess', category='bachelor', tenant_gender='male')
        results = smart_match(visible(), {'tenant_gender': 'female'})
        self.assertNotIn(male_only, [r['property'] for r in results])
        self.assertIn(self.flat, [r['property'] for r in results])

    def test_homes_over_budget_are_left_out(self):
        make_property(self.landlord, title='Expensive', price=60000)
        results = smart_match(visible(), {'max_price': 35000})
        self.assertEqual([r['property'] for r in results], [self.flat])

    def test_smart_match_is_sorted_by_percentage(self):
        far = make_property(self.landlord, title='Far', location='Uttara')
        results = smart_match(visible(), {'location': 'Dhanmondi', 'min_bedrooms': 3})
        self.assertEqual(results[0]['property'], self.flat)
        self.assertNotIn(far, [r['property'] for r in results if r['percentage'] == 100])
