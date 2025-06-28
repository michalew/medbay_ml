from cmms.models import Ticket, Device, Document

# models from which event to calendar are created
event_models = [
    Ticket,
    Device,
    Document
]

event_type_fields = {
    'Ticket': [
        {
            'event_name': 'ticket-finished',
            'date_field': 'date_finish',
            'title': {
                'title_method': 'get_ticket_closed_title',
            }
        },
        {
            'event_name': 'ticket-start-planned-range',
            'date_field': ['timestamp', 'planned_date_execute'],
            'title': {
                'text': 'Zgłoszenie %s, czas od założenia do planowanej daty wykonania',
                'fields': ['id'],
            }
        },
        {
            'event_name': 'ticket-start-execute-range',
            'date_field': ['timestamp', 'date_execute'],
            'title': {
                'text': 'Zgłoszenie %s, czas od założenia do wykonania',
                'fields': ['id'],
            }
        },
        #{
        #    'event_name': 'ticket-planned-date',
        #    'date_field': 'planned_date_execute',
        #    'title': {
        #        'text': u'Data planowania zgłoszenia %s. (%s)',
        #        'fields': ['id', 'description'],
        #    }
        #},
        #{
        #    'event_name': 'ticket-execute-date',
        #    'date_field': 'date_execute',
        #    'title': {
        #        'text': u'Wykonanie zgłoszenia o id %s. (%s)',
        #        'fields': ['id', 'description'],
        #    }
        #},
        #{
        #    'event_name': 'ticket-added-date',
        #    'date_field': 'timestamp',
        #    'title': {
        #        'text': u'Dodano zgłoszenie o id %s. (%s)',
        #        'fields': ['id', 'description'],
        #    }
        #}
    ],
    'Device': [
        {
            'event_name': 'device-warranty',
            'date_field': 'date_warranty',
            'title': {
                'text': 'Koniec gwarancji urządzenia <a href="/a/cmms/device/%s">%s</a>',
                'fields': ['id', 'name'],
            }
        },
        #{
        #    'event_name': 'device-manufactured-bought-range',
        #    'date_field': ['date_manufactured', 'date_bought'],
        #    'title': {
        #        'text': u'Urządzenie %s, czas od produkcji do zakupu',
        #        'fields': ['id'],
        #    }
        #}
    ],
    'Document': [
        {
            'event_name': 'document-expiration-date',
            'date_field': 'date_expiration',
            'title': {
                'title_method': 'get_document_expiration_date_title',
            }
        }
    ]
}

# configuration file validation
for key in event_type_fields:
    for event in event_type_fields[key]:
        second_level_keys = ['event_name', 'date_field', 'title']
        for second_level_key in second_level_keys:
            try:
                event[second_level_key]
            except KeyError:
                raise KeyError('You have forgotten about %s in %s section in calendar_events_configration file!'
                               % (second_level_key, key))

        for title_keys in event['title']:
            second_level_keys = ['text', 'fields']
            method_name = event['title'].get('title_method', None)
            if method_name is None:
                for second_level_key in second_level_keys:
                    try:
                        event['title'][second_level_key]
                    except KeyError:
                        raise KeyError(
                            'You have forgotten about %s in %s section in calenedar_events_configration file!'
                            % (second_level_key, key))
