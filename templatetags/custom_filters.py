from django import template

register = template.Library()

@register.filter
def get_item(list, index):
    """Obtiene un elemento de la lista por su índice."""
    try:
        return list[int(index)]  # Asegúrate de convertir 'index' a entero
    except (IndexError, ValueError):
        return None  # Si el índice no existe o no es válido, retorna None
