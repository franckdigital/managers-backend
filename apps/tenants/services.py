from datetime import date, timedelta

from django.utils import timezone

BILLING_DAYS = {
    'monthly': 30,
    'quarterly': 90,
    'semi_annual': 180,
    'yearly': 365,
    'lifetime': 365 * 100,  # no nullable-end_date migration needed — 100 years reads as permanent
}


def _plan_covers_course(plan, course):
    """A global plan covers the whole catalogue; a scoped plan only covers the
    courses an admin explicitly attached to it via included_courses."""
    if course is None:
        return True
    if plan is None:
        return False
    if plan.is_global:
        return True
    return plan.included_courses.filter(pk=course.pk).exists()


def has_active_team_subscription(user, course=None):
    """True when the user is covered by an active subscription for `course` at ANY
    of three levels: their own team, their company (i.e. their site), or any parent
    company up the ownership chain. Global plans cover everything, scoped plans only
    their included_courses."""
    today = timezone.now().date()

    def _sub_ok(status, end, plan):
        if status != 'active':
            return False
        if end is not None and end < today:
            return False
        return _plan_covers_course(plan, course)

    # 1. Team-level subscription
    if user.team_id:
        team = user.team
        if _sub_ok(team.subscription_status, team.subscription_end, team.plan):
            return True

    # 2. The user's own company (their site) then every parent company
    company = user.company
    while company is not None:
        if _sub_ok(company.subscription_status, company.subscription_end, company.plan):
            return True
        company = company.parent

    return False


def has_active_b2c_subscription(user, course=None):
    """True when an individual (B2C) learner has a valid personal subscription
    whose plan covers `course` (or any subscription at all, if course is None)."""
    if user.company_id:
        return False
    today = timezone.now().date()
    sub = user.subscriptions.filter(status='active', end_date__gte=today).select_related('plan').first()
    if not sub:
        return False
    return _plan_covers_course(sub.plan, course)


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


def activate_team_subscription(team, plan, start_date=None, end_date=None, amount_paid=0):
    """Set a single team's subscription to active and record a history entry."""
    from apps.tenants.models import TeamSubscription

    today = timezone.now().date()
    start = start_date or today

    if end_date is None:
        end = _plan_end_date(plan, start)
    else:
        end = end_date if isinstance(end_date, date) else date.fromisoformat(str(end_date))

    team.plan = plan
    team.subscription_status = 'active'
    team.subscription_start = start
    team.subscription_end = end
    team.save(update_fields=['plan', 'subscription_status', 'subscription_start', 'subscription_end'])

    TeamSubscription.objects.create(
        team=team,
        plan=plan,
        status=TeamSubscription.STATUS_ACTIVE,
        start_date=start,
        end_date=end,
        amount_paid=amount_paid,
    )
    return team


def activate_user_subscription(user, plan, amount_paid=0, end_date=None):
    """Create an individual B2C subscription for a learner.
    `end_date` overrides the plan's default duration (used when an admin records a
    cash payment with an agreed term)."""
    from apps.tenants.models import UserSubscription

    today = timezone.now().date()
    if end_date is None:
        end = _plan_end_date(plan, today)
    else:
        end = end_date if isinstance(end_date, date) else date.fromisoformat(str(end_date))

    return UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.STATUS_ACTIVE,
        start_date=today,
        end_date=end,
        amount_paid=amount_paid,
    )
