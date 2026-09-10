from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.core.constants import Roles
from apps.tenants.models import Company, Department, SubscriptionPlan, Team
from apps.tenants.services import has_active_team_subscription

User = get_user_model()


class HasActiveTeamSubscriptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plan = SubscriptionPlan.objects.create(
            name='Entreprise Global', code='ent-global',
            plan_type=SubscriptionPlan.PLAN_TYPE_ENTERPRISE, is_global=True,
        )
        cls.parent = Company.objects.create(name='Holding')
        cls.site = Company.objects.create(name='Filiale Abidjan', parent=cls.parent)
        cls.team = Team.objects.create(company=cls.site, name='Équipe Support')

    def setUp(self):
        # Reset every level to "no subscription" before each test.
        for obj in (self.parent, self.site):
            obj.plan = None
            obj.subscription_status = 'trial'
            obj.subscription_end = None
            obj.save()
        self.team.plan = None
        self.team.subscription_status = 'trial'
        self.team.subscription_end = None
        self.team.save()
        self.user = User.objects.create_user(
            email='emp@example.com', password='x', company=self.site, team=self.team,
        )

    def _future(self):
        return timezone.now().date() + timedelta(days=30)

    def _activate(self, obj):
        obj.plan = self.plan
        obj.subscription_status = 'active'
        obj.subscription_end = self._future()
        obj.save()

    def test_no_subscription_denies_access(self):
        self.assertFalse(has_active_team_subscription(self.user))

    def test_team_subscription_grants_access(self):
        self._activate(self.team)
        self.assertTrue(has_active_team_subscription(self.user))

    def test_site_subscription_grants_access(self):
        self._activate(self.site)
        self.assertTrue(has_active_team_subscription(self.user))

    def test_parent_company_subscription_grants_access(self):
        self._activate(self.parent)
        self.assertTrue(has_active_team_subscription(self.user))

    def test_expired_team_subscription_denies_access(self):
        self.team.plan = self.plan
        self.team.subscription_status = 'active'
        self.team.subscription_end = timezone.now().date() - timedelta(days=1)
        self.team.save()
        self.assertFalse(has_active_team_subscription(self.user))

    def test_scoped_plan_only_covers_included_courses(self):
        from apps.courses.models import Course

        scoped = SubscriptionPlan.objects.create(
            name='Pack ciblé', code='scoped', plan_type=SubscriptionPlan.PLAN_TYPE_ENTERPRISE, is_global=False,
        )
        covered = Course.objects.create(title='Couvert', slug='couvert')
        other = Course.objects.create(title='Non couvert', slug='non-couvert')
        scoped.included_courses.add(covered)
        self.team.plan = scoped
        self.team.subscription_status = 'active'
        self.team.subscription_end = self._future()
        self.team.save()
        self.assertTrue(has_active_team_subscription(self.user, covered))
        self.assertFalse(has_active_team_subscription(self.user, other))


class SubscriptionPaymentAccessTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plan = SubscriptionPlan.objects.create(
            name='Enterprise', code='ent', plan_type=SubscriptionPlan.PLAN_TYPE_ENTERPRISE,
            price=100000, billing_cycle='yearly', is_active=True,
        )
        cls.company = Company.objects.create(name='ACME')
        cls.hr = User.objects.create_user(email='hr@acme.test', password='x', role=Roles.HR, company=cls.company)
        cls.admin = User.objects.create_user(
            email='admin@acme.test', password='x', role=Roles.COMPANY_ADMIN, company=cls.company,
        )

    def test_hr_can_pay_company_subscription_manually_and_it_activates(self):
        self.client.force_authenticate(self.hr)
        res = self.client.post(
            f'/api/companies/{self.company.id}/subscribe/',
            {'plan': self.plan.id, 'provider': 'manual'}, format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.company.refresh_from_db()
        self.assertEqual(self.company.subscription_status, 'active')
        self.assertEqual(self.company.plan_id, self.plan.id)

    def test_hr_cannot_use_free_activate_endpoint(self):
        self.client.force_authenticate(self.hr)
        res = self.client.post(
            f'/api/companies/{self.company.id}/activate-subscription/',
            {'plan': self.plan.id}, format='json',
        )
        self.assertEqual(res.status_code, 403)

    def test_company_admin_cannot_use_free_activate_endpoint(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(
            f'/api/companies/{self.company.id}/activate-subscription/',
            {'plan': self.plan.id}, format='json',
        )
        self.assertEqual(res.status_code, 403)


class OrgStructureCreationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.super_admin = User.objects.create_user(
            email='root2@example.com', password='x', role=Roles.SUPER_ADMIN, is_superuser=True,
        )
        cls.parent = Company.objects.create(name='Groupe')
        cls.sub = Company.objects.create(name='Filiale A', parent=cls.parent)
        cls.other = Company.objects.create(name='Autre société')
        cls.admin = User.objects.create_user(
            email='ca@groupe.test', password='x', role=Roles.COMPANY_ADMIN, company=cls.parent,
        )

    def test_super_admin_must_pick_company_for_team(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.post('/api/teams/', {'name': 'Sans société'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('company', res.data.get('errors', res.data))

    def test_super_admin_creates_team_on_chosen_subsidiary(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.post('/api/teams/', {'name': 'Support', 'company': self.sub.id}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Team.objects.get(name='Support').company_id, self.sub.id)

    def test_company_admin_can_create_team_on_own_subsidiary_not_on_foreign_company(self):
        self.client.force_authenticate(self.admin)
        ok = self.client.post('/api/teams/', {'name': 'T1', 'company': self.sub.id}, format='json')
        self.assertEqual(ok.status_code, 201, ok.data)

        ko = self.client.post('/api/teams/', {'name': 'T2', 'company': self.other.id}, format='json')
        self.assertEqual(ko.status_code, 400)
        self.assertIn('company', ko.data.get('errors', ko.data))

    def test_department_company_must_match_when_creating_service(self):
        self.client.force_authenticate(self.super_admin)
        dept = Department.objects.create(company=self.sub, name='RH')
        res = self.client.post(
            '/api/services/',
            {'name': 'Paie', 'company': self.other.id, 'department': dept.id}, format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('department', res.data.get('errors', res.data))


class TeamAttachmentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plan = SubscriptionPlan.objects.create(
            name='Ent', code='ent-att', plan_type=SubscriptionPlan.PLAN_TYPE_ENTERPRISE,
            price=100000, billing_cycle='yearly', is_active=True, is_global=True,
        )
        cls.company = Company.objects.create(name='ACME2')
        cls.team = Team.objects.create(company=cls.company, name='Support')
        cls.admin = User.objects.create_user(
            email='a@acme2.test', password='x', role=Roles.COMPANY_ADMIN, company=cls.company,
        )
        cls.super_admin = User.objects.create_user(
            email='root3@example.com', password='x', role=Roles.SUPER_ADMIN, is_superuser=True,
        )

    def test_attach_requires_active_company_subscription(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(f'/api/teams/{self.team.id}/attach-subscription/')
        self.assertEqual(res.status_code, 400)

    def test_attach_mirrors_company_subscription_onto_team(self):
        from apps.tenants.services import activate_company_subscription
        activate_company_subscription(self.company, self.plan)
        self.company.refresh_from_db()

        self.client.force_authenticate(self.admin)
        res = self.client.post(f'/api/teams/{self.team.id}/attach-subscription/')
        self.assertEqual(res.status_code, 200, res.data)
        self.team.refresh_from_db()
        self.assertEqual(self.team.subscription_status, 'active')
        self.assertEqual(self.team.plan_id, self.plan.id)
        self.assertEqual(self.team.subscription_end, self.company.subscription_end)

        # Detach clears the team record (company-wide access unaffected)
        res = self.client.post(f'/api/teams/{self.team.id}/detach-subscription/')
        self.assertEqual(res.status_code, 200)
        self.team.refresh_from_db()
        self.assertIsNone(self.team.plan_id)
        self.assertEqual(self.team.subscription_status, 'trial')

    def test_activate_company_subscription_with_covered_team_ids(self):
        from apps.tenants.services import activate_company_subscription
        activate_company_subscription(self.company, self.plan, covered_team_ids=[self.team.id])
        self.team.refresh_from_db()
        self.assertEqual(self.team.subscription_status, 'active')
        self.assertEqual(self.team.plan_id, self.plan.id)

    def test_no_team_subscribe_endpoint_anymore(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.post(f'/api/teams/{self.team.id}/subscribe/', {'plan': self.plan.id}, format='json')
        self.assertIn(res.status_code, (404, 405))
