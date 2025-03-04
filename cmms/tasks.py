from django.http import Http404

from config.settings import DEFAULT_FROM_EMAIL, DOMAIN_NAME, DEBUG
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from celery import shared_task
from celery.utils.log import get_task_logger
from crm.models import UserProfile
from django_comments.models import Comment
from datetime import datetime
from django.db.models import Q
from django.apps import apps

import cmms
import re

EMAIL_DELAY = 20

logger = get_task_logger(__name__)


@shared_task
def send_mileage_notifications():
    logger.info("Sending mileage notifications")

    # initialize error count
    error_count = 0

    # get all mileage items
    mileages = cmms.models.Mileage.objects.all()

    # send e-mail for each one
    for item in mileages:
        # try to send a reminder
        result = item.remind()

        # check if exited with errors
        if result != 1:
            error_count += 1
            logger.info("Can't send e-mail for mileage %s" % item.name)

    if error_count == 0:
        logger.info('Mileage e-mails sent\n')
    else:
        logger.info('Errors occurred with %s mileages' % error_count)


@shared_task
def autoprogress_tickets():
    # add info to log that task is running
    logger.info("Autoprogress tickets was called.")

    # get all tickets we need to care about
    planned_tickets = cmms.models.Ticket.objects.filter(status=6)
    open_tickets = cmms.models.Ticket.objects.filter(Q(status=1) | Q(status=0))

    # try to get contenttype
    try:
        ct = ContentType.objects.get(model="ticket", app_label="cmms")
    except ContentType.DoesNotExist:
        raise Http404

    # iterate through all the planned tickets
    for ticket in planned_tickets:
        # check if ticket execution date before current date
        if ticket.timestamp and ticket.timestamp < datetime.now().date():
            # generate comment text
            comment = "Osoba dokonująca zmian: SYSTEM<br/><br/>Wprowadzone zmiany:<br/>"
            comment += "- Status: %s => Otwarte" % ticket.get_status_name()

            # change status and save
            ticket.status = 0
            ticket.save()
            logger.info("changed status of %s to 'Otwarte'" % ticket)

            # create comment
            now = datetime.now()
            Comment.objects.create(comment=comment, site_id=1, object_pk=ticket.pk, content_type_id=ct.pk, user_id=1,
                                   submit_date=now)
            changelog_email_task.apply_async(countdown=EMAIL_DELAY,
                                             args=[ticket.pk,
                                                   (ticket.__module__ + "." + ticket.__class__.__name__).lower()],
                                             kwargs={"as_system": True})

    # iterate through all the open tickets
    for ticket in open_tickets:
        # check if ticket planned execution date before current date
        if ticket.planned_date_execute and ticket.planned_date_execute < datetime.now().date():
            # generate comment text
            comment = "Osoba dokonująca zmian: SYSTEM<br/><br/>Wprowadzone zmiany:<br/>"
            comment += "- Status: %s => Przeterminowane" % ticket.get_status_name()

            # change status and save
            ticket.status = 3
            ticket.save()
            logger.info("changed status of %s to 'Przeterminowane'" % ticket)

            # create comment
            now = datetime.now()
            Comment.objects.create(comment=comment, site_id=1, object_pk=ticket.pk, content_type_id=ct.pk, user_id=1,
                                   submit_date=now)
            changelog_email_task.apply_async(countdown=EMAIL_DELAY,
                                             args=[ticket.pk,
                                                   (ticket.__module__ + "." + ticket.__class__.__name__).lower()],
                                             kwargs={"as_system": True})


@shared_task
def mileage_remind(obj_id):
    obj = cmms.models.Mileage.objects.get(pk=obj_id)

    if not obj:
        return

    body = """
            Licznik "%s" do urządzenia "%s", producent: %s, model: %s, nr seryjny: %s, nr inwentarzowy: %s, znajdującego się w lokalizacji %s przekroczył ustaloną wartość graniczną.
Aktualna wartość licznika wynosi %s co stanowi %s wartości końcowej.
Uwaga: %s

    http://%s/a/cmms/mileage/%s

    """ % (obj.name, obj.device.name, obj.device.make, obj.device.model, obj.device.serial_number,
           obj.device.inventory_number, obj.device.location, obj.state, obj.get_percentage(), obj.warning,
           DOMAIN_NAME, obj.pk)

    if obj.device.location:
        # get staff from location
        send_to = list(obj.device.location.staff.values_list('email', flat=True))
        # make sure person responsible for location is in the list
        if obj.device.location.person:
            send_to += [obj.device.location.person.email, ]
    else:
        send_to = []

    # get all users who can see all devices
    all_users = UserProfile.objects.all()
    for user in all_users:
        if user.has_perm("cmms.view_all_devices"):
            send_to += [user.email, ]

    # deduplicate
    send_to = list(set(send_to))
    subject = "Licznik do urządzenia %s przekroczył wartość graniczną" % obj.device.name

    # generate html body
    html_body = body.replace("\n", "<br/>")
    html_body = html_body.replace(
        "http://%s/a/cmms/mileage/%s" % (DOMAIN_NAME, obj.pk),
        "<a href='http://%s/a/cmms/mileage/%s'>Pokaż licznik</a>" % (DOMAIN_NAME, obj.pk)
    )

    logger.info("Sending emails to %s" % (send_to,))

    # send email
    for i in send_to:
        send_mail(subject, body.replace('<br/>', '\n'), DEFAULT_FROM_EMAIL, [i], html_message=html_body)
        logger.info("Sending emails to %s" % (send_to,))


@shared_task
def ticket_email_task(obj_id, created):
    # fixes tasks crashing for no reason
    if DEBUG:
        import django
        django.setup()

    obj = cmms.models.Ticket.objects.get(pk=obj_id)

    if not created:
        return

    body = "Witamy\n\n"

    subject = "Nowe zgłoszenie nr (#%s)" % str(obj.pk)
    body += "Utworzono nowe zgłoszenie nr #%s \n" % str(obj.pk)

    body += "Osoba zgłaszająca: %s \n" % obj.person_creating
    body += "Opis zgłoszenia: %s \n\n" % obj.description

    if created:
        body += "Powiązane urządzenia: \n"
        for device in obj.device.all():
            body += "%s, %s, %s, %s, %s, %s, %s \n" % (device.pk, device.name, device.model,
                                                       device.serial_number, device.inventory_number, device.location,
                                                       device.cost_centre)
        body += "\n"

    body += "Status zgłoszenia: %s \n" % obj.get_status_name()
    body += "Planowana data wykonania: %s \n \n" % obj.planned_date_execute

    body += "Link do zgłoszenia: http://%s/a/cmms/ticket/%s\n\n" % (DOMAIN_NAME, obj.pk)

    body += "Pozdrawiamy\n" \
            "system medCMMS\n" \
            "(Mail wygenerowany automatycznie - prosimy nie odpowiadać)"

    # get person creating ticket email
    try:
        send_to = [obj.person_creating.email, ]
    except:
        send_to = []
    for device in obj.device.all():
        # get person responsible for device email
        if device.person_responsible:
            send_to += [device.person_responsible.email, ]

    # get all users who can see all devices
    all_users = UserProfile.objects.all()
    for user in all_users:
        if user.has_perm("cmms.view_all_devices"):
            send_to += [user.email, ]

    # deduplicate
    send_to = list(set(send_to))

    # generate html body
    html_body = body.replace("\n", "<br/>")
    html_body = html_body.replace(
        "Link do zgłoszenia: http://%s/a/cmms/ticket/%s" % (DOMAIN_NAME, obj.pk),
        "<a href='http://%s/a/cmms/ticket/%s'>Pokaż zgłoszenie</a>" % (DOMAIN_NAME, obj.pk)
    )

    logger.info("Sending emails to %s" % (send_to,))

    # send email
    for i in send_to:
        send_mail(subject, body.replace('<br/>', '\n'), DEFAULT_FROM_EMAIL, [i], html_message=html_body)
        logger.info("Sent '%s' to %s" % (subject, i))


@shared_task
def service_email_task(obj_id, created):
    # fixes tasks crashing for no reason
    if DEBUG:
        import django
        django.setup()

    obj = cmms.models.Service.objects.get(pk=obj_id)

    if not created:
        return

    body = "Witamy\n\n"

    subject = "Nowe zlecenie nr (#%s)" % str(obj.pk)
    body += "Utworzono nowe zgłoszenie nr #%s \n" % str(obj.pk)

    body += "Osoba tworząca zlecenie: %s \n" % obj.person_creating
    body += "Opis zlecenia: %s \n\n" % obj.description

    if created:
        body += "Powiązane zgłoszenia: \n"
        for ticket in obj.ticket.all():
            body += "#%s, %s \n" % (ticket.pk, ticket.description)
        body += "\n"

    body += "Rodzaj zlecenia: %s \n" % obj.get_sort_name()
    body += "Status zlecenia: %s \n" % obj.get_status_name()

    body += "Link do zlecenia: http://%s/a/cmms/service/%s\n\n" % (DOMAIN_NAME, obj.pk)

    body += "Pozdrawiamy\n" \
            "system medCMMS\n" \
            "(Mail wygenerowany automatycznie - prosimy nie odpowiadać)"

    # get person creating ticket email
    try:
        send_to = [obj.person_creating.email]
    except AttributeError:
        send_to = []

    for ticket in obj.ticket.all():
        for device in ticket.device.all():
            # get person responsible for device email
            if device.person_responsible:
                send_to.append(device.person_responsible.email)

    # get all users who can see all devices
    all_users = UserProfile.objects.all()
    for user in all_users:
        if user.has_perm("cmms.view_all_devices"):
            send_to.append(user.email)

    # deduplicate
    send_to = list(set(send_to))

    # generate html body
    html_body = body.replace("\n", "<br/>")
    html_body = html_body.replace(
        "Link do zlecenia: http://%s/a/cmms/service/%s" % (DOMAIN_NAME, obj.pk),
        "<a href='http://%s/a/cmms/service/%s'>Pokaż zlecenie</a>" % (DOMAIN_NAME, obj.pk)
    )

    logger.info("Sending emails to %s" % (send_to,))

    # send email
    for i in send_to:
        send_mail(subject, body.replace('<br/>', '\n'), DEFAULT_FROM_EMAIL, [i], html_message=html_body)
        logger.info("Sent '%s' to %s" % (subject, i))


@shared_task
def comment_email_task(obj_id, comment_id, model_name):
    # fixes tasks crashing for no reason
    if DEBUG:
        import django
        django.setup()

    comment = Comment.objects.get(pk=comment_id)

    if model_name == "Ticket":
        obj = cmms.models.Ticket.objects.get(pk=obj_id)
        devices = obj.device.all()
        model = "zgłoszenia"
    elif model_name == "Service":
        obj = cmms.models.Service.objects.get(pk=obj_id)
        model = "zlecenia"
        tickets = [i.pk for i in obj.ticket.all()]
        devices = cmms.models.Device.objects.filter(ticket__in=tickets).distinct()
    else:
        return

    subject = "Nowy komentarz do %s nr (#%s)" % (model, str(obj.pk))

    body = "Witamy\n\n"

    body += "Do %s nr #%s dodano komentarz: \n" % (model, str(obj.pk))

    body += "Osoba zgłaszająca: %s \n" % obj.person_creating
    body += "Opis %s: %s \n" % (model, obj.description)

    if model_name == "Service":
        body += "Rodzaj zlecenia: %s \n" % obj.get_sort_name()

    body += "Status %s: %s \n" % (model, obj.get_status_name())

    if model_name == "Ticket":
        body += "Planowana data wykonania: %s \n \n" % obj.planned_date_execute

    body += "Użytkownik %s dodał komentarz:\n%s\n\n" % (comment.user, comment.comment)

    body += "Link do %s: http://%s/a/cmms/%s/%s\n\n" % (model, DOMAIN_NAME, model_name.lower(), obj.pk)

    body += "Pozdrawiamy\n" \
            "system medCMMS\n" \
            "(Mail wygenerowany automatycznie - prosimy nie odpowiadać)"

    # get person creating ticket email
    try:
        send_to = [obj.person_creating.email]
    except AttributeError:
        send_to = []

    for device in devices:
        # get person responsible for device email
        if device.person_responsible:
            send_to.append(device.person_responsible.email)

    # get all users who can see all devices
    all_users = UserProfile.objects.all()
    for user in all_users:
        if user.has_perm("cmms.view_all_devices"):
            send_to.append(user.email)

    # deduplicate
    send_to = list(set(send_to))

    # generate html body
    html_body = body.replace("\n", "<br/>")
    html_body = html_body.replace(
        "Link do %s: http://%s/a/cmms/%s/%s" % (model, DOMAIN_NAME, model_name.lower(), obj.pk),
        "<a href='http://%s/a/cmms/%s/%s'>Pokaż %s</a>" % (DOMAIN_NAME, model_name.lower(), obj.pk, model)
    )

    # try to find all urls in non-html
    while True:
        # do regex matching
        link = re.search("<a href='.*'>.*</a>", body)
        if link:
            # get url and title from link match
            url = re.search("(?<=href=').*?(?=')", link.group())
            title = re.search("(?<='>).*?(?=</a>)", link.group())
            if url:
                # replace url and title in non-html body
                body = body.replace(link.group(), "%s (%s)" % (title.group(), url.group()))
        else:
            break

    logger.info("Sending emails to %s" % (send_to,))

    # send email
    for i in send_to:
        send_mail(subject, body.replace('<br/>', '\n'), DEFAULT_FROM_EMAIL, [i], html_message=html_body)
        logger.info("Sent '%s' to %s" % (subject, i))


@shared_task
def changelog_email_task(obj_pk, model_path, as_system=False):
    # fixes tasks crashing for no reason
    if DEBUG:
        import django
        django.setup()

    # get rel model
    rel_model = apps.get_model(app_label=model_path.split('.')[0], model_name="%s" % model_path.split('.')[2])

    # get obj
    obj = rel_model.objects.get(pk=obj_pk)

    app_label = model_path.split('.')[0]
    model_name = model_path.split('.')[2]

    # try to get contenttype from the db
    try:
        content_type_from_model_name = ContentType.objects.get(model=model_name, app_label=app_label)
    except Exception as e:
        logger.error(e)
        return

    if not as_system:
        comment = "Osoba dokonująca zmian: %s<br/><br/>Wprowadzone zmiany:<br/>" % (obj.history.first().history_user)
    else:
        comment = "Osoba dokonująca zmian: SYSTEM<br/><br/>Wprowadzone zmiany:<br/>"

    # parse diff
    diff = obj.history.first().diff()
    for line in diff:
        comment += "%s<br/>" % line

    body = "Witamy\n\n"
    subject = "Edycja %s nr (#%s)" % (rel_model._meta.verbose_name_plural.lower(), str(obj.pk))
