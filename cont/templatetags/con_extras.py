# con/templatetags/con_extras.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def currency(value):
    try:
        val = Decimal(value)
    except:
        val = Decimal('0.00')
    return f"COP {val:,.2f}"

@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
