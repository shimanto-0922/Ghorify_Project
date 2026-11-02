import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import normalize_phone
from .models import Profile, User


class QuickSignupTests(TestCase):
    def signup(self, **overrides):
        data = {'first_name': 'Rahim', 'phone': '01712345678',
                'password1': 'abc123', 'password2': 'abc123'}
        data.update(overrides)
        return self.client.post(reverse('accounts:register'), data)

    def test_signup_needs_only_name_phone_and_password(self):
        response = self.signup()
        self.assertRedirects(response, reverse('dashboard:home'), fetch_redirect_response=False)
        user = User.objects.get(phone='01712345678')
        self.assertEqual(user.username, '01712345678')
        self.assertIsNone(user.email)
        self.assertEqual(user.role, 'user')
        self.assertTrue(user.profile)

    def test_short_password_is_rejected(self):
        self.signup(password1='abc', password2='abc')
        self.assertFalse(User.objects.exists())

    def test_same_phone_cannot_sign_up_twice(self):
        self.signup()
        self.client.logout()
        self.signup(first_name='Other')
        self.assertEqual(User.objects.count(), 1)

    def test_login_with_phone_in_any_format(self):
        self.signup()
        self.client.logout()
        for typed in ('01712345678', '+880 1712-345678', '8801712345678'):
            response = self.client.post(reverse('accounts:login'), {'username': typed, 'password': 'abc123'})
            self.assertEqual(response.status_code, 302, typed)
            self.client.logout()

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone('+880 1712-345678'), '01712345678')
        self.assertEqual(normalize_phone('01712345678'), '01712345678')


TEMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class TenantDocumentTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user('t1', password='abc123', phone='01711111111', first_name='T')
        Profile.objects.create(user=self.user)
        self.client.force_login(self.user)
        self.base = {'first_name': 'T', 'last_name': '', 'email': '', 'phone': '01711111111', 'bio': ''}

    def post(self, **files):
        return self.client.post(reverse('accounts:profile'), {**self.base, **files})

    def test_profile_saves_without_any_document(self):
        self.assertEqual(self.post().status_code, 302)
        self.assertFalse(self.user.profile.nid_document or self.user.profile.birth_certificate)

    def test_upload_nid_and_birth_certificate(self):
        self.post(nid_document=SimpleUploadedFile('nid.pdf', b'%PDF-1.4 demo', content_type='application/pdf'),
                  birth_certificate=SimpleUploadedFile('bc.jpg', b'fake-jpg', content_type='image/jpeg'))
        profile = self.user.profile
        profile.refresh_from_db()
        self.assertTrue(profile.nid_document and profile.birth_certificate)
        self.assertEqual(profile.status, 'pending')  # sent to the admin for verification

    def test_wrong_file_type_is_rejected(self):
        response = self.post(nid_document=SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream'))
        self.assertContains(response, 'Only PDF, JPG or PNG files are accepted.')

    def test_document_can_be_removed(self):
        self.post(nid_document=SimpleUploadedFile('nid.pdf', b'%PDF', content_type='application/pdf'))
        self.post(**{'nid_document-clear': 'on'})
        profile = self.user.profile
        profile.refresh_from_db()
        self.assertFalse(profile.nid_document)
