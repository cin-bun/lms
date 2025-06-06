from typing import Iterable, NamedTuple

from braces.views import UserPassesTestMixin
from django.conf import settings
from django.core import signing
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import generic
from django.contrib.sites.models import Site

from admission.selectors import get_ongoing_interviews
from learning.icalendar import (
    StudentAssignmentICalendarEvent, StudentClassICalendarEvent,
    StudyEventICalendarEvent, TeacherAssignmentICalendarEvent,
    TeacherClassICalendarEvent, generate_icalendar, InterviewICalendarEvent
)
from learning.models import StudentAssignment
from learning.selectors import (
    get_student_classes, get_study_events, get_teacher_assignments, get_teacher_classes
)
from users.models import User


class ICalendarMeta(NamedTuple):
    name: str
    description: str
    file_name: str


class UserICalendarView(generic.base.View):
    def get(self, request, *args, **kwargs):
        user = self.get_user()
        site = Site.objects.get(pk=settings.SITE_ID)
        url_builder = request.build_absolute_uri
        product_id = f"-//{site.name} Calendar//{site.domain}//"
        tz = user.time_zone or settings.DEFAULT_TIMEZONE
        calendar_meta = self.get_calendar_meta(user, site, url_builder, tz)
        events = self.get_calendar_events(user, site, url_builder, tz)
        cal = generate_icalendar(product_id,
                                 name=calendar_meta.name,
                                 description=calendar_meta.description,
                                 time_zone=tz,
                                 events=events)
        response = HttpResponse(cal.to_ical(),
                                content_type="text/calendar; charset=UTF-8")
        response['Content-Disposition'] = "attachment; filename=\"{}\"".format(
            calendar_meta.file_name)
        return response

    def get_user(self):
        encoded_pk = self.kwargs['encoded_pk']
        qs = (User.objects
              .filter(pk=signing.loads(encoded_pk))
              .only("first_name", "last_name", "patronymic", "pk"))
        return get_object_or_404(qs)

    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        raise NotImplementedError

    def get_calendar_events(self, user, site, url_builder, tz) -> Iterable:
        raise NotImplementedError


class ICalClassesView(UserICalendarView):
    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        return ICalendarMeta(
            name=f"Занятия {site.name}",
            description=f"Календарь занятий {site.name} ({user.get_full_name()})",
            file_name="classes.ics"
        )

    def get_calendar_events(self, user, site, url_builder, tz):
        event_factory = StudentClassICalendarEvent(tz, url_builder, site)
        # FIXME: filter out past course classes?
        for course_class in get_student_classes(user, with_venue=True):
            yield event_factory.create(course_class, user)
        event_factory = TeacherClassICalendarEvent(tz, url_builder, site)
        for course_class in get_teacher_classes(user, with_venue=True):
            yield event_factory.create(course_class, user)


class ICalAssignmentsView(UserICalendarView):
    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        description = "Календарь сроков выполнения заданий {} ({})".format(
            site.name, user.get_full_name())
        return ICalendarMeta(
            name=f"Задания {site.name}",
            description=description,
            file_name="assignments.ics")

    def get_calendar_events(self, user, site, url_builder, tz):
        event_factory = TeacherAssignmentICalendarEvent(tz, url_builder, site)
        for assignment in get_teacher_assignments(user).with_future_deadline():
            yield event_factory.create(assignment, user)
        event_factory = StudentAssignmentICalendarEvent(tz, url_builder, site)
        queryset = (StudentAssignment.objects
                    .for_student(user)
                    .with_future_deadline())
        for sa in queryset:
            yield event_factory.create(sa, user)


class ICalEventsView(UserICalendarView):
    def get_user(self):
        return self.request.user

    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        return ICalendarMeta(
            name=f"События {site.name}",
            description="Календарь общих событий {}".format(site.name),
            file_name="events.ics")

    def get_calendar_events(self, user, site, url_builder, tz):
        event_factory = StudyEventICalendarEvent(tz, url_builder, site)
        filters = []
        future_events = Q(date__gt=timezone.now())
        filters.append(future_events)
        # FIXME: take into account all teacher branches?
        if hasattr(user, "branch_id") and user.branch_id:
            filters.append(Q(branch_id=user.branch_id))
        for e in get_study_events(filters).select_related('venue'):
            yield event_factory.create(e, user)

class ICalInterviewsView(UserICalendarView):
    @staticmethod
    def get_calendar_meta(user, site, url_builder, tz) -> ICalendarMeta:
        return ICalendarMeta(
            name=f"Собеседования {site.name}",
            description=f"Календарь собеседований {site.name} ({user.get_full_name()})",
            file_name="interviews.ics"
        )
    def get_calendar_events(self, user, site, url_builder, tz):
        event_factory = InterviewICalendarEvent(tz, url_builder, site)
        for interview in get_ongoing_interviews(user):
            yield event_factory.create(interview, user)
