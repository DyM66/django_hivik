from django.apps import AppConfig


class DthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dth'

    def ready(self):
        # Importamos las señales
        import dth.signals