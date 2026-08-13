from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.core.constants import Roles


def _role(request):
    user = request.user
    return getattr(user, 'role', None) if user and user.is_authenticated else None


class HasRole(BasePermission):
    """Usage: permission_classes = [HasRole.for_roles(Roles.HR, Roles.COMPANY_ADMIN)]"""

    allowed_roles = ()

    def has_permission(self, request, view):
        role = _role(request)
        if role is None:
            return False
        if request.user.is_superuser or role == Roles.SUPER_ADMIN:
            return True
        return role in self.allowed_roles

    @classmethod
    def for_roles(cls, *roles):
        return type('HasRoleScoped', (cls,), {'allowed_roles': set(roles)})


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or _role(request) == Roles.SUPER_ADMIN))


class IsCompanyAdmin(HasRole):
    allowed_roles = {Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN}


class IsHR(HasRole):
    allowed_roles = {Roles.HR, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN}


class IsManager(HasRole):
    allowed_roles = {Roles.MANAGER, Roles.HR, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN}


class IsTrainer(HasRole):
    allowed_roles = {Roles.TRAINER}


class IsSameCompany(BasePermission):
    """Object-level: a user may only access objects belonging to their own company.
    Super admins bypass this check entirely (platform-wide access)."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or _role(request) == Roles.SUPER_ADMIN:
            return True
        obj_company = getattr(obj, 'company', None)
        return obj_company is not None and obj_company_id_matches(obj_company, user)


def obj_company_id_matches(obj_company, user):
    return getattr(user, 'company_id', None) == obj_company.id


class ReadOnlyOrHasRole(HasRole):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return super().has_permission(request, view)
