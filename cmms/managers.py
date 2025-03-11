from django.db.models import Manager, QuerySet
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user



class DocumentQuerySet(QuerySet):
    def for_user(self, user):
        from .models import Ticket  # avoid circular import
        # check permissions
        if not user.has_perm("cmms.view_document"):
            return self.none()

        # get list of devices/tickets visible for this user
        devices = get_objects_for_user(
            user, 'cmms.view_device', accept_global_perms=False)
        tickets = Ticket.objects.filter(device__in=devices).distinct()

        # return either public documents or somehow related to tickets/devices
        # visible for given user
        return self.filter(
            Q(device__in=devices) | Q(ticket__in=tickets)).distinct()


class DocumentManager(Manager):
    def for_user(self, user):
        return self.all().for_user(user)

    def get_queryset(self):
        return DocumentQuerySet(self.model, using=self._db)