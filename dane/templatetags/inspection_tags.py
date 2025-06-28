from django import template
from cmms.models import Ticket

register = template.Library()


@register.simple_tag
def get_ticket(ticket_id):
    return Ticket.objects.filter(pk=ticket_id).first()
