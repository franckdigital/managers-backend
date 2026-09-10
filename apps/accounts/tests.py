from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.constants import Roles

User = get_user_model()


class PartnerAdminCrudTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.super_admin = User.objects.create_user(
            email='root@example.com', password='x', role=Roles.SUPER_ADMIN, is_superuser=True, is_staff=True,
        )

    def setUp(self):
        self.client.force_authenticate(self.super_admin)

    def test_super_admin_creates_partner_with_default_rate(self):
        res = self.client.post('/api/users/', {
            'email': 'video.partner@example.com',
            'password': 'Str0ngPass!42',
            'first_name': 'Vid', 'last_name': 'Partner',
            'role': Roles.PARTNER,
            'partner_default_rate': 35,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        partner = User.objects.get(email='video.partner@example.com')
        self.assertEqual(partner.role, Roles.PARTNER)
        self.assertEqual(float(partner.partner_default_rate), 35.0)
        self.assertIsNone(partner.company_id)

    def test_partner_list_filter_and_patch_rate(self):
        p = User.objects.create_user(email='p@example.com', password='x', role=Roles.PARTNER, partner_default_rate=20)
        User.objects.create_user(email='emp@example.com', password='x', role=Roles.EMPLOYEE)

        res = self.client.get('/api/users/', {'role': Roles.PARTNER})
        emails = {u['email'] for u in (res.data.get('results') or res.data)}
        self.assertEqual(emails, {'p@example.com'})

        res = self.client.patch(f'/api/users/{p.id}/', {'partner_default_rate': 40}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        p.refresh_from_db()
        self.assertEqual(float(p.partner_default_rate), 40.0)

    def test_eligible_recipients_includes_partner_email(self):
        User.objects.create_user(
            email='partner.pick@example.com', password='x', role=Roles.PARTNER,
            first_name='Pick', last_name='Me', partner_default_rate=30,
        )
        res = self.client.get('/api/revenue-share/eligible-recipients/')
        self.assertEqual(res.status_code, 200)
        row = next(r for r in res.data if r['email'] == 'partner.pick@example.com')
        self.assertEqual(row['name'], 'Pick Me')
        self.assertEqual(row['role'], Roles.PARTNER)
