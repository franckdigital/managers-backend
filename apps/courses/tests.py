from django.test import TestCase

from apps.courses.models import Course
from apps.courses.serializers import course_access_plans
from apps.tenants.models import SubscriptionPlan


class CourseAccessPlansTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(title='Devenir performant', slug='devenir-performant')
        cls.other = Course.objects.create(title='Autre cours', slug='autre-cours')

        cls.global_b2c = SubscriptionPlan.objects.create(
            name='B2C À vie', code='b2c-vie', plan_type=SubscriptionPlan.PLAN_TYPE_B2C,
            price=20000, billing_cycle='lifetime', is_global=True, is_active=True,
        )
        cls.scoped_b2c = SubscriptionPlan.objects.create(
            name='Pack Management', code='b2c-mgmt', plan_type=SubscriptionPlan.PLAN_TYPE_B2C,
            price=10000, billing_cycle='lifetime', is_global=False, is_active=True,
        )
        cls.scoped_b2c.included_courses.add(cls.course)

        cls.enterprise = SubscriptionPlan.objects.create(
            name='Entreprise', code='ent', plan_type=SubscriptionPlan.PLAN_TYPE_ENTERPRISE,
            price=500000, is_global=True, is_active=True,
        )
        cls.inactive = SubscriptionPlan.objects.create(
            name='B2C désactivé', code='b2c-off', plan_type=SubscriptionPlan.PLAN_TYPE_B2C,
            price=5000, billing_cycle='lifetime', is_global=True, is_active=False,
        )
        cls.quarterly = SubscriptionPlan.objects.create(
            name='B2C Trimestriel', code='b2c-quarter', plan_type=SubscriptionPlan.PLAN_TYPE_B2C,
            price=13500, billing_cycle='quarterly', is_global=True, is_active=True,
        )

    def test_lists_global_and_scoped_b2c_plans_for_included_course(self):
        plans = course_access_plans(self.course, {})
        names = {p['name'] for p in plans}
        self.assertEqual(names, {'B2C À vie', 'Pack Management'})
        # sorted by price ascending
        self.assertEqual([p['name'] for p in plans], ['Pack Management', 'B2C À vie'])

    def test_excludes_enterprise_inactive_and_recurring_plans(self):
        names = {p['name'] for p in course_access_plans(self.course, {})}
        self.assertNotIn('Entreprise', names)
        self.assertNotIn('B2C désactivé', names)
        self.assertNotIn('B2C Trimestriel', names)  # only lifetime plans are surfaced

    def test_course_not_in_scoped_plan_only_gets_global(self):
        plans = course_access_plans(self.other, {})
        self.assertEqual([p['name'] for p in plans], ['B2C À vie'])

    def test_context_caches_global_plans(self):
        ctx = {}
        course_access_plans(self.course, ctx)
        self.assertIn('b2c_global_plans', ctx)
        self.assertEqual(len(ctx['b2c_global_plans']), 1)
