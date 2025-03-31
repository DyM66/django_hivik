from django import template

register = template.Library()

@register.filter
def split(value, delimiter="_"):
    """
    Devuelve el fragmento resultante de hacer split por 'delimiter'.
    Por ejemplo: {{ "add_nomina"|split:"_" }}
    """
    return value.split(delimiter)

@register.filter
def has_permission(user, permission):
    perm_str = f"{permission.content_type.app_label}.{permission.codename}"
    return user.has_perm(perm_str)

