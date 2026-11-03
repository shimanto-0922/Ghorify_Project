from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from properties.models import Property

from .models import Comparison, Favourite


class InteractionFlowTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user('ll', 'll@x.com', 'pw', phone='01711111111')
        self.tenant = User.objects.create_user('tt', 'tt@x.com', 'pw')
        self.props = [Property.objects.create(
            landlord=self.landlord, title=f'Flat {i}', description='d', location='Mirpur', address='Secret road',
            price=20000, status='approved') for i in range(4)]
        self.prop = self.props[0]
        self.client.force_login(self.tenant)

    def favourite(self, *props):
        for p in props:
            Favourite.objects.create(tenant=self.tenant, property=p)

    def test_favourite_toggle(self):
        url = reverse('interactions:favourite_toggle', args=[self.prop.pk])
        self.client.post(url)
        self.assertTrue(Favourite.objects.filter(tenant=self.tenant, property=self.prop).exists())
        self.client.post(url)
        self.assertFalse(Favourite.objects.exists())

    def test_compare_page_asks_to_favourite_first(self):
        response = self.client.get(reverse('interactions:compare_select'))
        self.assertContains(response, 'Please favorite a few homes first')

    def test_compare_two_or_three_favourites(self):
        self.favourite(*self.props)
        url = reverse('interactions:compare_select')
        self.client.post(url, {'property': [self.props[0].pk]})                  # only one
        self.client.post(url, {'property': [p.pk for p in self.props]})        # four
        self.assertFalse(Comparison.objects.exists())
        response = self.client.post(url, {'property': [self.props[0].pk, self.props[1].pk]})
        comparison = Comparison.objects.get()
        self.assertRedirects(response, reverse('interactions:comparison_detail', args=[comparison.pk]))
        self.assertEqual(comparison.items.count(), 2)

    def test_cannot_compare_homes_that_are_not_favourites(self):
        self.favourite(self.props[0])
        self.client.post(reverse('interactions:compare_select'), {'property': [self.props[0].pk, self.props[1].pk]})
        self.assertFalse(Comparison.objects.exists())

    def test_phone_and_address_need_login(self):
        url = reverse('properties:property_detail', args=[self.prop.id])
        self.client.logout()
        page = self.client.get(url)
        self.assertNotContains(page, '01711111111')
        self.assertNotContains(page, 'Secret road')
        self.client.force_login(self.tenant)
        page = self.client.get(url)
        self.assertContains(page, '01711111111')
        self.assertContains(page, 'Secret road')

    def test_one_account_can_save_homes_and_post_its_own(self):
        own = Property.objects.create(landlord=self.tenant, title='My flat', description='d', location='Uttara',
                                      address='x', price=15000, status='approved')
        self.client.post(reverse('interactions:favourite_toggle', args=[self.prop.pk]))
        self.assertTrue(Favourite.objects.filter(tenant=self.tenant, property=self.prop).exists())
        self.assertEqual(self.client.get(reverse('properties:property_update', args=[own.pk])).status_code, 200)
