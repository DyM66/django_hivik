# got/templatetags/asset_tags.py
from django import template
from got.models import Equipo, Asset

register = template.Library()

@register.filter
def has_engines(asset_pk):
    systems = Asset.objects.get(pk=asset_pk).system_set.all()
    return Equipo.objects.filter(system__in=systems, type__code='r').exists()
