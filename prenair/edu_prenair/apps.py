from django.apps import AppConfig


class EduPrenairConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'edu_prenair'

    def ready(self):
        import profiles.signals
        import edu_prenair.signals  # Ensure signals are imported

