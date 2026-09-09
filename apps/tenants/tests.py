from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.tenants.models import Company, SubscriptionPlan, Team
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
