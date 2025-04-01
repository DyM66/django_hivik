# permissions_dashboard/views.py
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group, User
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json


class PermissionMatrixView(TemplateView):
    template_name = "permissions_management/permission_matrix.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1) Recolectar todos los ContentTypes (apps/modelos)
        contenttypes = (ContentType.objects
            .exclude(app_label__in=["admin","sessions","contenttypes","auth", "site"])
            .order_by("app_label","model"))
        
        # Agrupar info en un diccionario: {app_label: {model_label: [perm, perm...], ...}, ...}
        permission_structure = {}
        for ct in contenttypes:
            perms = Permission.objects.filter(content_type=ct).order_by("codename")

            if ct.app_label not in permission_structure:
                permission_structure[ct.app_label] = {}
            permission_structure[ct.app_label][ct.model] = perms

        # Agrega permission_structure al contexto
        context["permission_structure"] = permission_structure

        # 2) Convertir ese diccionario en una lista que incluya el "colspan"
        #    que es la suma total de permisos de todos sus modelos
        apps_data = []
        for app_label, models_dict in permission_structure.items():
            # Contar la suma total de permisos
            total_perms_for_app = 0
            # Crear lista de modelos
            models_data = []
            for model_label, perms in models_dict.items():
                models_data.append({
                    'model_label': model_label,
                    'perms': perms,
                    'num_perms': perms.count(),
                })
                total_perms_for_app += perms.count()

            apps_data.append({
                'app_label': app_label,
                'models': models_data,
                'colspan': total_perms_for_app,
            })
        
        # 3) Obtenemos grupos y usuarios
        groups = Group.objects.order_by("name")
        users = User.objects.order_by("username")

        # 4) Enviamos 'apps_data' en lugar de 'permission_structure'
        context['apps_data'] = apps_data
        context['groups'] = groups
        context['users'] = users

        # En PermissionMatrixView.get_context_data, luego de crear apps_data
        sum_of_all_colspans = sum(app["colspan"] for app in apps_data)
        # +1 si incluyes la columna “Grupo/Usuario”
        total_columns = 1 + sum_of_all_colspans
        context["sum_of_all_columns"] = total_columns
        return context


@csrf_exempt
def toggle_permission_ajax(request):
    """
    Recibe JSON:
      { 
        "permission_id": 123,
        "object_type": "user" or "group",
        "object_id": 45
      }
    Retorna { "success": true } o { "success": false, "error": "..." }
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
        perm_id = data.get('permission_id')
        obj_type = data.get('object_type')
        obj_id = data.get('object_id')
        
        perm = Permission.objects.get(id=perm_id)

        if obj_type == "group":
            group = Group.objects.get(id=obj_id)
            # ¿Tiene el permiso?
            if perm in group.permissions.all():
                # Quitar
                group.permissions.remove(perm)
            else:
                # Agregar
                group.permissions.add(perm)
            group.save()
        elif obj_type == "user":
            user = User.objects.get(id=obj_id)
            # Revisar si el user lo tiene directamente
            # OJO: user.has_perm no distingue si es por user o por group
            # Para “togglear” sólo en el user, chequeamos user.user_permissions
            if perm in user.user_permissions.all():
                # Quitar (user lo tenía directo)
                user.user_permissions.remove(perm)
            else:
                # Agregarlo directo al user
                user.user_permissions.add(perm)
            user.save()
        else:
            return JsonResponse({"success": False, "error": "Tipo de objeto inválido"})
        
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)