import datetime
import time

from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.utils.html import strip_tags
from django.views.generic import TemplateView, FormView

from reminders.forms import CalendarEventForm
from reminders.models import CalendarEvent
from utils.view_mixins import AjaxView, JSONResponseMixin
from utils.views import render_xls

from guardian.decorators import permission_required_or_403
from django.utils.decorators import method_decorator


class CalendarView(TemplateView):
    template_name = "reminders/calendar.html"

    @method_decorator(permission_required_or_403('reminders.view_event_calendar'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CalendarEventForm()
        return context


class GetEventView(AjaxView, JSONResponseMixin, TemplateView):
    def get_context_data(self, **kwargs):
        start = self.request.GET.get('from')
        end = self.request.GET.get('to')

        if start is None or end is None:
            raise Http404()

        try:
            start = int(start)
            end = int(end)
        except (ValueError, TypeError):
            raise Http404()

        start_dt = datetime.datetime.fromtimestamp(start / 1000.0).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = datetime.datetime.fromtimestamp(end / 1000.0).replace(hour=23, minute=59, second=59, microsecond=999999)

        events1 = CalendarEvent.objects.filter(start_date__gte=start_dt, start_date__lte=end_dt)
        events2 = CalendarEvent.objects.filter(end_date__gte=start_dt, end_date__lte=end_dt)
        events3 = CalendarEvent.objects.filter(start_date__lte=start_dt, end_date__gte=end_dt)

        events = events1 | events2 | events3

        results = []
        for index, event in enumerate(events):
            result = {
                'id': index,
                'title': event.title,
                'class': event.event_name,
                'start': int(event.start_date.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000),
                'end': int(event.end_date.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000),
                'url': event.get_url(),
                'start_date': event.start_date.strftime('%Y-%m-%d'),
                'end_date': event.end_date.strftime('%Y-%m-%d'),
            }
            results.append(result)

        return {
            'success': 1,
            'result': results,
        }


class SaveEventView(FormView):
    form_class = CalendarEventForm
    template_name = "reminders/calendar.html"

    def form_valid(self, form):
        start_date = form.cleaned_data.get('start_date')
        title = form.cleaned_data.get('title')

        end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        subject_id = time.mktime(datetime.datetime.now().timetuple())
        model_name = 'Note'
        event_name = 'event-info'

        event = CalendarEvent(
            title=title,
            start_date=start_date,
            end_date=end_date,
            subject_id=subject_id,
            model_name=model_name,
            event_name=event_name,
        )
        event.save()

        return HttpResponse()

    def form_invalid(self, form):
        # render_to_response is deprecated, use render instead
        response = render(self.request, 'reminders/note_form.html', {'form': form})
        return HttpResponse(response, status=500)


class GetExcelEventsReport(TemplateView):
    def get(self, request, *args, **kwargs):
        start = kwargs.get('from')
        end = kwargs.get('to')

        if start is None or end is None:
            raise Http404()

        try:
            start_date = datetime.datetime.strptime(start + " 00:00:00", "%Y-%m-%d %H:%M:%S")
            end_date = datetime.datetime.strptime(end + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise Http404()

        events = CalendarEvent.objects.filter(
            start_date__gte=start_date,
            start_date__lte=end_date
        ).order_by('start_date')

        for event in events:
            event.title = strip_tags(event.title)

        response = render_xls('event', events, ['start_date', 'end_date', 'title'])

        return response
from django.shortcuts import render

# Create your views here.
