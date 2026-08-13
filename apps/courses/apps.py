from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = 'apps.courses'

    def ready(self):
        import apps.courses.signals  # noqa: F401
