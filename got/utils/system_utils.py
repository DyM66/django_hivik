from got.models import System

def get_full_systems(asset, user):
    systems = asset.system_set.all()
    other_asset_systems = System.objects.filter(location=asset.name).exclude(asset=asset)

    combined = systems.union(other_asset_systems)
    return combined
    # return (systems.union(other_asset_systems)).order_by('group')


def get_full_systems_ids(asset, user):
    systems = asset.system_set.values_list('id', flat=True)
    other_asset_systems = System.objects.filter(location=asset.name).exclude(asset=asset).values_list('id', flat=True)
    all_systems_ids = systems.union(other_asset_systems)

    # if user.groups.filter(name='buzos_members').exists():
    #     station = user.profile.station
    #     if station:
    #         all_systems_ids = System.objects.filter(id__in=all_systems_ids, location__iexact=station).values_list('id', flat=True)
    #     else:
    #         all_systems_ids = System.objects.none().values_list('id', flat=True)
    return all_systems_ids