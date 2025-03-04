from guardian.shortcuts import assign_perm, remove_perm
from celery import shared_task
from config.settings import DEFAULT_FROM_EMAIL, DEBUG, DOMAIN_NAME
from django.core.mail import EmailMessage
from django.utils.safestring import mark_safe
from django_comments.models import Comment
from celery.utils.log import get_task_logger
import datetime
import cmms
from crm.models import UserProfile
from django.conf import settings

logger = get_task_logger(__name__)

def reset_permissions(user, devices):
    if not user or not devices:
        return

    # reset all permissions
    for device in devices:
        remove_perm("cmms.view_device", user, device)

def update_permissions(user, devices):
    # get permissions for user
    can_view_device = user.has_perm("cmms.view_all_devices") or user.has_perm("cmms.view_device")

    # set device permissions
    for device in devices:
        if can_view_device:
            assign_perm('cmms.view_device', user, device)

@shared_task(name='utils.tasks.setup_permissions')
def setup_permissions(user_id, reset_device_ids, user_device_ids):
    user = UserProfile.objects.get(pk=user_id)
    reset_devices = cmms.models.Device.objects.filter(pk__in=reset_device_ids)
    user_devices = cmms.models.Device.objects.filter(pk__in=user_device_ids)

    try:
        # remove permissions
        reset_permissions(user, reset_devices)

        # update permissions
        if user_devices:
            update_permissions(user, user_devices)
    except Exception as e:
        logger.error(f"Error in setup_permissions: {e}")

@shared_task(name='utils.tasks.send_service_email')
def send_service_email(user_id, service_id, document_id, content_id, ticket_content_id):
    if DEBUG:
        import django
        django.setup()

    now = datetime.datetime.now()

    document = cmms.models.Document.objects.get(pk=document_id)
    obj = cmms.models.Service.objects.get(pk=service_id)

    if not obj:
        return False

    msg = "Dzień dobry,<br/> w załączniku przesyłamy zlecenie na wykonanie usługi konserwacji sprzętu medycznego.<br/> W razie pytań prosimy o kontakt."

    contractor_email = None
    if obj.sort == 0:
        contractor_email = obj.person_completing.email
    elif obj.sort == 1:
        contractor_email = obj.contractor.email

    if not contractor_email:
        return False

    recipient = [contractor_email] if contractor_email and not settings.DEBUG_EMAIL else ["medcmms.kontrahent@gmail.com"]
    if obj.person_creating: recipient.append(obj.person_creating.email)
    if obj.person_completing: recipient.append(obj.person_completing.email)
    if obj.person_assigned: recipient.append(obj.person_assigned.email)

    email = EmailMessage(
        f"Zlecenie nr #{obj.pk}",
        msg,
        DEFAULT_FROM_EMAIL,
        recipient,
    )
    email.content_subtype = "html"
    email.attach_file(document.scan.path)

    email.send(fail_silently=False)
    logger.info(f"Sent email for Service {obj.pk} to {recipient}")

    if obj.status == 1:
        comment = mark_safe(f"Wysłano zapytanie ofertowe do <a href='http://{DOMAIN_NAME}/{obj.get_absolute_url()}'>zlecenia nr #{obj.pk}</a> na adres {recipient[0]}.")
    elif obj.status == 2:
        comment = mark_safe(f"Wysłano akceptację oferty do <a href='http://{DOMAIN_NAME}/{obj.get_absolute_url()}'>zlecenia nr #{obj.pk}</a> na adres {recipient[0]}.")
    else:
        comment = mark_safe(f"Wysłano <a href='http://{DOMAIN_NAME}/{obj.get_absolute_url()}'>zlecenie nr #{obj.pk}</a> na adres {recipient[0]}.")

    Comment.objects.create(
        comment=comment,
        site_id=1,
        object_pk=obj.pk,
        content_type_id=content_id,
        user_id=user_id,
        submit_date=now
    )

    for ticket in obj.ticket.all():
        Comment.objects.create(
            comment=comment,
            site_id=1,
            object_pk=ticket.pk,
            content_type_id=ticket_content_id,
            user_id=user_id,
            submit_date=now
        )
