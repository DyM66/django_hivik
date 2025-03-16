from django.apps import AppConfig


class NtfConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ntf'

    def ready(self):
        import ntf.signals