from datetime import date, timedelta

from django.utils import timezone

BILLING_DAYS = {
    'monthly': 30,
    'quarterly': 90,
    'semi_annual': 180,
    'yearly': 365,
}


def has_active_team_subscription(user):
    """True when the user belongs to a company with an active subscription covering today."""
    if not user.company_id:
        return False
    company = user.company
    if company.subscription_status != 'active':
        return False
    today = timezone.now().date()
    if company.subscription_end and company.subscription_end < today:
        return False
    return True


def has_active_b2c_subscription(user):
    """True when an individual (B2C) learner has a valid personal subscription."""
    if user.company_id:
        return False
    today = timezone.now().date()
    return user.subscriptions.filter(status='active', end_date__gte=today).exists()


def _plan_end_date(plan, start):
    days = BILLING_DAYS.get(plan.billing_cycle, 30)
    return start + timedelta(days=days)


def activate_company_subscription(company, plan, start_date=None, end_date=None, amount_paid=0):
    """Set a company's subscription to active and record a history entry."""
    from apps.tenants.models import CompanySubscription

    today = timezone.now().date()
    start = start_date or today

    if end_date is None:
        end = _plan_end_date(plan, start)
    else:
        end = end_date if isinstance(end_date, date) else date.fromisoformat(str(end_date))

    company.plan = plan
    company.subscription_status = 'active'
    company.subscription_start = start
    company.subscription_end = end
    company.save(update_fields=['plan', 'subscription_status', 'subscription_start', 'subscription_end'])

    CompanySubscription.objects.create(
        company=company,
        plan=plan,
        status=CompanySubscription.STATUS_ACTIVE,
        start_date=start,
        end_date=end,
        amount_paid=amount_paid,
    )
    return company


def activate_user_subscription(user, plan, amount_paid=0):
    """Create an individual B2C subscription for a learner."""
    from apps.tenants.models import UserSubscription

    today = timezone.now().date()
    end = _plan_end_date(plan, today)
    return UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.STATUS_ACTIVE,
        start_date=today,
        end_date=end,
        amount_paid=amount_paid,
    )
