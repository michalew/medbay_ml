# coding=utf-8
from reminders.calendar_events_configuration import event_type_fields
from reminders.models import CalendarEvent


class EventManager(object):
    def __init__(self, instance):
        self.instance = instance

    def prepare_title(self, possible_event):
        try:
            if possible_event['title']['title_method']:
                title_method = getattr(self, possible_event['title']['title_method'])
                title = title_method()
        except KeyError:
            title = self.get_title(possible_event)
        return title

    def get_dates(self, possible_event):
        # check if date_field is list for ranged event
        if isinstance(possible_event['date_field'], list):
            start_date = getattr(self.instance, possible_event['date_field'][0])
            end_date = getattr(self.instance, possible_event['date_field'][1])
        else:
            start_date = getattr(self.instance, possible_event['date_field'])
            end_date = getattr(self.instance, possible_event['date_field'])

        return start_date, end_date

    def process(self):
        """
        Adds or updates every type of event for object supplied via constructor

        :return: None
        """
        possible_events = event_type_fields.get(type(self.instance).__name__, None)

        # If we don't find any events in configuration file for that model we do nothing
        if possible_events is None:
            return

        for possible_event in possible_events:
            title = self.prepare_title(possible_event)

            # If for some reason title is blank then do not process an event
            if title is None:
                continue

            event_name = possible_event['event_name']
            model_name = type(self.instance).__name__
            subject_id = self.instance.id

            start_date, end_date = self.get_dates(possible_event)

            if start_date is None or end_date is None:
                continue

            if model_name == 'Ticket' and event_name == 'ticket-start-planned-range':
                if self.instance.status == 0:
                    event_name += "-open"
                if self.instance.status == 3:
                    event_name += "-expired"
                if self.instance.status == 6:
                    event_name += "-planned"
                CalendarEvent.objects.filter(
                    subject_id=subject_id, model_name=model_name, event_name__startswith='ticket-start-planned-range'
                ).delete()

            if model_name == 'Ticket' and event_name == 'ticket-start-execute-range':
                if self.instance.status == 2:
                    event_name += "-finished"
                CalendarEvent.objects.filter(
                    subject_id=subject_id, model_name=model_name, event_name__startswith='ticket-start-execute-range'
                ).delete()
                CalendarEvent.objects.filter(
                    subject_id=subject_id, model_name=model_name, event_name__startswith='ticket-start-planned-range'
                ).delete()

            try:
                event = CalendarEvent.objects.get(subject_id=subject_id, model_name=model_name, event_name=event_name)
            except CalendarEvent.DoesNotExist:
                event = CalendarEvent()
                event.subject_id = subject_id
                event.model_name = model_name
                event.event_name = event_name

            event.title = self.prepare_title(possible_event)
            event.start_date = start_date
            event.end_date = end_date
            event.save()

    def get_title(self, event_definition):
        """
        Method takes field names from configuration file and inject their values to text definition od title

        :param event_definition: one dictionary from calendar_events_configuration.py
        :return: str
        """
        title_text = event_definition["title"]["text"]

        tuple = ()
        for field in event_definition["title"]["fields"]:
            tuple = tuple + (getattr(self.instance, field),)

        title_text = title_text % tuple

        return title_text

    def delete(self):

        possible_events = event_type_fields[type(self.instance).__name__]

        # If we don't find any events in configuration file for that model we do nothing
        if possible_events is None:
            return

        for possible_event in possible_events:
            event_name = possible_event['event_name']
            model_name = type(self.instance).__name__
            subject_id = self.instance.id

            if model_name == 'Ticket' and event_name == 'ticket-start-planned-range':
                if self.instance.status == 0:
                    event_name += "-open"
                if self.instance.status == 3:
                    event_name += "-expired"
                if self.instance.status == 6:
                    event_name += "-planned"
            if model_name == 'Ticket' and event_name == 'ticket-start-execute-range':
                if self.instance.status == 2:
                    event_name += "-finished"
            CalendarEvent.objects.filter(subject_id=subject_id, model_name=model_name, event_name=event_name).delete()

    def get_ticket_closed_title(self):
        devices = self.instance.device.values_list('id', 'name', 'inventory_number')
        sort = self.instance.get_sort_display()

        title = f'Zakończono zgłoszenie: {sort} '
        for device in devices:
            title = f'{title} <a href="/a/cmms/device/{device[0]}/">{device[1]} ({device[2]})</a> '
        return title

    def get_document_expiration_date_title(self):
        devices = self.instance.device.values_list('id')
        if devices is None:
            return None
        title = f'Upływa data ważności dokumentu ({self.instance.name}) dla urządzeń: '
        for device in devices:
            title = f'{title} <a href="/a/cmms/device/{device[0]}/">#{device[0]}</a> '
        return title