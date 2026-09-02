from django.apps import AppConfig
from django.conf import settings


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        from .models import UserWebsite 
        try:
            custom_domains = list(
                UserWebsite.objects.filter(is_published=True, custom_domain__isnull=False)
                .values_list('custom_domain', flat=True)
            )
            settings.ALLOWED_HOSTS += custom_domains
        except Exception as e:
            print("Could not load custom domains into ALLOWED_HOSTS:", e)
