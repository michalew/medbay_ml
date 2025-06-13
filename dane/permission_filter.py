"""
Hide permission in the Django admin which are irrelevant, and not used at all.

Based on: https://gist.github.com/vdboor/6280390
"""
from django.db.models import Q
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType


class PermissionFilterMixin(object):
    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name in ('permissions', 'user_permissions'):
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            qs = _filter_permissions(qs)
            kwargs['queryset'] = qs

        return super(PermissionFilterMixin, self).formfield_for_manytomany(
            db_field, request, **kwargs)


def get_excluded_permissions():
    """
    Lists excluded content types.
    """
    filters = Q()

    # list of excluded content types, "*" means excluding entire app
    excluded_contenttypes = [
        ("auth", "permission"),
        ("contenttypes", "contenttype"),
        ("sessions", "session"),
        ("sites", "site"),
        ("admin", "logentry"),
        ("crm", "hospital"),
        ("djcelery", "*"),
        ("django", "*"),
        ("csvimport", "*"),
        ("tastypie", "*"),
        ("south", "*"),
        ("kombu_transport_django", "*")
    ]

    for app_label, model in excluded_contenttypes:
        if model == "*":
            filters = filters | Q(app_label=app_label)
        else:
            filters = filters | Q(app_label=app_label, model=model)

    # also exclude historical ones
    filters = filters | Q(model__contains="historical")

    return ContentType.objects.filter(filters)


def _filter_permissions(qs):
    """
    Hides permissions for certain content types to make list more
    readable.
    """
    return qs.exclude(content_type__pk__in=get_excluded_permissions())
