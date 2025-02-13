from django.apps import AppConfig


class MtoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mto'

    def ready(self):
        import mto.signals 