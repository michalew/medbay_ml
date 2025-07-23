from django.urls import re_path
from reminders.views import CalendarView, GetEventView, SaveEventView, GetExcelEventsReport

urlpatterns = [
    re_path(r'^$', CalendarView.as_view()),
    re_path(r'^wydarzenia$', GetEventView.as_view()),
    re_path(r'^wydarzenie/zapisz$', SaveEventView.as_view()),
    re_path(
        r'^eksport/(?P<from>\d{4}-\d{2}-\d{2})/(?P<to>\d{4}-\d{2}-\d{2})$',
        GetExcelEventsReport.as_view(),
        name='events_export'
    ),
]
