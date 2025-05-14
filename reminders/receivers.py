from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from cmms.models import Ticket
from reminders.calendar_events_configuration import event_models
from reminders.event_manager import EventManager


@receiver(post_save)
def receive_calendar_event(sender, **kwargs):
    if sender not in event_models:
        return

    instance = kwargs.get('instance')
    if instance is None:
        return

    event = EventManager(instance)
    event.process()


@receiver(post_delete)
def delete_calendar_event(sender, **kwargs):
    if sender not in event_models:
        return

    instance = kwargs.get('instance')
    if instance is None:
        return

    event = EventManager(instance)
    event.delete()


