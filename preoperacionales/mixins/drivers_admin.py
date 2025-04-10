from django.core.exceptions import PermissionDenied

class DriversAdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name="drivers_admin").exists():
            raise PermissionDenied("No tiene permisos para acceder a esta sección.")
        return super().dispatch(request, *args, **kwargs)
