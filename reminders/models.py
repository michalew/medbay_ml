from django.db import models

# Create your models here.
class CalendarEvent(models.Model):
    title = models.CharField(max_length=4096)
    model_name = models.CharField(max_length=4096)
    event_name = models.CharField(max_length=256)
    subject_id = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def get_url(self):
        if self.model_name == 'Ticket':
            return "/a/cmms/ticket/%d/" % self.subject_id
        if self.model_name == 'Note':
            return "/a/reminders/calendarevent/%d/" % self.id
        if self.model_name == 'Device':
            return "/a/cmms/device/%d/" % self.subject_id
        if self.model_name == 'Document':
            return "/a/cmms/document/%d/" % self.subject_id

    def __str__(self):
        return self.title

    class Meta:
        unique_together = ('subject_id', 'model_name', 'event_name')
        verbose_name = 'Wydarzenie'
        verbose_name_plural = 'Wydarzenia'
        permissions = (
            ("view_event_calendar", u"Może przeglądać kalendarz"),
        )