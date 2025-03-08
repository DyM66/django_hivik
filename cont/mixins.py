# got/mixins.py
from django.core.exceptions import PermissionDenied

class FinanceMembersRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name="finance_members").exists():
            raise PermissionDenied("No tiene permisos para acceder a esta sección.")
        return super().dispatch(request, *args, **kwargs)
