from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/', include('apps.core.urls')),
    path('api/', include('apps.accounts.urls')),
    path('api/', include('apps.tenants.urls')),
    path('api/', include('apps.catalog.urls')),
    path('api/', include('apps.payments.urls')),
    path('api/', include('apps.courses.urls')),
    path('api/', include('apps.learning_paths.urls')),
    path('api/', include('apps.assessments.urls')),
    path('api/', include('apps.virtual_classes.urls')),
    path('api/', include('apps.social.urls')),
    path('api/', include('apps.gamification.urls')),
    path('api/', include('apps.certificates.urls')),
    path('api/hr/', include('apps.hr_analytics.urls')),
    path('api/kpi-pro/', include('apps.kpi_pro.urls')),
    path('api/hr-agent/', include('apps.hr_agent.urls')),
    path('api/ai/', include('apps.ai_engine.urls')),
    path('api/integrations/', include('apps.integrations.urls')),
    path('api/progression/', include('apps.progression.urls')),
    path('api/content-security/', include('apps.content_security.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/revenue-share/', include('apps.revenue_share.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
