from django.apps import AppConfig


class CoreApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_api'

    def ready(self):
        # With GEMINI_API_KEY set, every "Generate with AI" text call is
        # answered by Gemini (Groq / OpenAI stay as the fallback).
        from prenair.gemini_patch import install

        install()
