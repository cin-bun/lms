# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import csv
import datetime
import logging
import os
import unicodecsv

from calendar import Calendar
from collections import OrderedDict, defaultdict

from annoying.exceptions import Redirect
from six import viewvalues
from itertools import chain

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, \
    MultipleObjectsReturned

from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Q, F, Prefetch, Count, When, Value, Case
from django.http import HttpResponseBadRequest, Http404, HttpResponse, \
    HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta
from learning.settings import ASSIGNMENT_COMMENT_ATTACHMENT, \
    ASSIGNMENT_TASK_ATTACHMENT, SEMESTER_AUTUMN_SPRING_INDEX_DIFF, \
    CENTER_FOUNDATION_YEAR, SEMESTER_TYPES
from core.views import ProtectedFormMixin, LoginRequiredMixin, SuperUserOnlyMixin
from learning.utils import get_current_semester_pair, get_semester_index
from learning.viewmixins import TeacherOnlyMixin, StudentOnlyMixin, \
    CuratorOnlyMixin, FailedCourseContextMixin, ParticipantOnlyMixin
from core import comment_persistence
from .models import Course, CourseClass, CourseOffering, Venue, \
    CourseOfferingNews, Enrollment, Assignment, AssignmentAttachment, \
    StudentAssignment, AssignmentComment, \
    CourseClassAttachment, AssignmentNotification, \
    CourseOfferingNewsNotification, Semester, NonCourseEvent, \
    OnlineCourse, InternationalSchool
from .forms import CourseOfferingPKForm, \
    CourseOfferingEditDescrForm, \
    CourseOfferingNewsForm, \
    CourseClassForm, CourseForm, \
    AssignmentCommentForm, AssignmentGradeForm, AssignmentForm, \
    MarksSheetTeacherImportGradesForm, GradeBookFormFactory
from core.notifications import get_unread_notifications_cache
from core.utils import hashids, get_club_domain
from . import utils
from .management.imports import ImportGradesByStepicID, ImportGradesByYandexLogin


logger = logging.getLogger(__name__)


class TimetableTeacherView(TeacherOnlyMixin,
                           generic.ListView):
    model = CourseClass
    user_type = 'teacher'
    template_name = "learning/timetable_teacher.html"

    def __init__(self, *args, **kwargs):
        self._context_weeks = None
        super(TimetableTeacherView, self).__init__(*args, **kwargs)

    def get_queryset(self):
        month_qstr = self.request.GET.get('month')
        year_qstr = self.request.GET.get('year')
        try:
            year = int(year_qstr)
            month = int(month_qstr)
        except TypeError:
            today = now().date()
            year, month = today.year, today.month
        chosen_month_date = datetime.date(year=year, month=month, day=1)
        prev_month_date = chosen_month_date + relativedelta(months=-1)
        next_month_date = chosen_month_date + relativedelta(months=+1)
        self._context_dates = {'month': month,
                               'year': year,
                               'current_date': chosen_month_date,
                               'prev_date': prev_month_date,
                               'next_date': next_month_date}
        return (CourseClass.objects
                .filter(date__month=month,
                        date__year=year,
                        course_offering__teachers=self.request.user)
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    def get_context_data(self, *args, **kwargs):
        context = (super(TimetableTeacherView, self)
                   .get_context_data(*args, **kwargs))
        context.update(self._context_dates)
        context['user_type'] = self.user_type
        return context


class TimetableStudentView(StudentOnlyMixin,
                           generic.ListView):
    model = CourseClass
    user_type = 'student'
    template_name = "learning/timetable_student.html"

    def __init__(self, *args, **kwargs):
        self._context_weeks = None
        super(TimetableStudentView, self).__init__(*args, **kwargs)

    def get_queryset(self):
        week_qstr = self.request.GET.get('week')
        year_qstr = self.request.GET.get('year')
        try:
            week = int(week_qstr)
            year = int(year_qstr)
        except TypeError:
            # This returns current week number. Beware: the week's number
            # is as of ISO8601, so 29th of December can be reported as
            # 1st week of the next year.
            year, week, _ = now().date().isocalendar()
        start = utils.iso_to_gregorian(year, week, 1)
        end = utils.iso_to_gregorian(year, week, 7)
        next_w_cal = (start + datetime.timedelta(weeks=1)).isocalendar()
        prev_w_cal = (start + datetime.timedelta(weeks=-1)).isocalendar()
        self._context_weeks = {'week': week,
                               'week_start': start,
                               'week_end': end,
                               'month': start.month,
                               'year': year,
                               'prev_year': prev_w_cal[0],
                               'prev_week': prev_w_cal[1],
                               'next_year': next_w_cal[0],
                               'next_week': next_w_cal[1]}
        return (CourseClass.objects
                .filter(date__range=[start, end],
                        course_offering__enrolled_students=self.request.user)
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))

    def get_context_data(self, *args, **kwargs):
        context = (super(TimetableStudentView, self)
                   .get_context_data(*args, **kwargs))
        context.update(self._context_weeks)
        context['user_type'] = self.user_type
        return context


class CalendarMixin(object):
    model = CourseClass
    template_name = "learning/calendar.html"

    def __init__(self, *args, **kwargs):
        self._month_date = None
        self._non_course_events = None
        super(CalendarMixin, self).__init__(*args, **kwargs)

    def noncourse_events(self, request, month, year, prev_month_date,
                         next_month_date):
        if request.site.domain == settings.CLUB_DOMAIN:
            return NonCourseEvent.objects.none()
        return (NonCourseEvent.objects
               .filter(Q(date__month=month, date__year=year)
                       | Q(date__month=prev_month_date.month,
                           date__year=prev_month_date.year)
                       | Q(date__month=next_month_date.month,
                           date__year=next_month_date.year))
               .order_by('date', 'starts_at')
               .select_related('venue'))

    def get_queryset(self):
        year_qstr = self.request.GET.get('year')
        month_qstr = self.request.GET.get('month')
        try:
            year = int(year_qstr)
            month = int(month_qstr)
        except TypeError:
            today = now().date()
            year, month = today.year, today.month
        self._month_date = datetime.date(year=year, month=month, day=1)
        prev_month_date = self._month_date + relativedelta(months=-1)
        next_month_date = self._month_date + relativedelta(months=+1)

        # FIXME(Dmitry): somewhat dirty, come up with better generalization
        self._non_course_events = \
            self.noncourse_events(self.request, month, year, prev_month_date,
                                  next_month_date)

        q = (CourseClass.objects
                .filter(Q(date__month=month,
                          date__year=year)
                        | Q(date__month=prev_month_date.month,
                            date__year=prev_month_date.year)
                        | Q(date__month=next_month_date.month,
                            date__year=next_month_date.year))
                .order_by('date', 'starts_at')
                .select_related('venue',
                                'course_offering',
                                'course_offering__course',
                                'course_offering__semester'))
        # Note: Logic repeated from .site_related() CourseOffering queryset
        # to avoid additional query.
        if self.request.site.domain == settings.CLUB_DOMAIN:
            q = q.filter(course_offering__is_open=True)
            if hasattr(self.request, 'city'):
                q = q.filter(Q(course_offering__city__pk=self.request.city.code)
                             | Q(course_offering__city__isnull=True))
        else:
            q = q.filter(course_offering__city__pk=settings.DEFAULT_CITY_CODE)
        return q

    def get_context_data(self, *args, **kwargs):
        context = (super(CalendarMixin, self)
                   .get_context_data(*args, **kwargs))
        context['next_date'] = self._month_date + relativedelta(months=1)
        context['prev_date'] = self._month_date + relativedelta(months=-1)
        context['user_type'] = self.user_type

        events = sorted(chain(context['object_list'],
                              self._non_course_events.all()),
                        key=lambda evt: (evt.date, evt.starts_at))

        dates_to_events = defaultdict(list)
        for event in events:
            dates_to_events[event.date].append(event)

        cal = Calendar(0)

        month_cal = cal.monthdatescalendar(self._month_date.year,
                                           self._month_date.month)
        month = [(week[0].isocalendar()[1],
                  [(day, dates_to_events[day],
                    day.month == self._month_date.month,
                    now().date() == day)
                   for day in week])
                 for week in month_cal]
        context['month'] = month
        context['month_date'] = self._month_date
        return context


class CalendarTeacherView(TeacherOnlyMixin,
                          CalendarMixin,
                          generic.ListView):
    user_type = 'teacher'

    def get_queryset(self):
        return (super(CalendarTeacherView, self).get_queryset()
                .filter(course_offering__teachers=self.request.user))


class CalendarStudentView(StudentOnlyMixin,
                          CalendarMixin,
                          generic.ListView):
    user_type = "student"

    def get_queryset(self):
        return (super(CalendarStudentView, self).get_queryset()
                .filter(course_offering__enrolled_students=self.request.user))


class CalendarFullView(LoginRequiredMixin,
                       CalendarMixin,
                       generic.ListView):
    user_type = 'full'


class CoursesListView(generic.ListView):
    model = Semester
    template_name = "learning/courses/list.html"

    def get_queryset(self):
        co_queryset = (CourseOffering.custom.site_related(self.request)
            .select_related('course')
            .prefetch_related('teachers')
            .order_by('course__name'))
        q = (self.model.objects.prefetch_related(
                Prefetch(
                    'courseoffering_set',
                    queryset=co_queryset,
                    to_attr='courseofferings'
                ),
            )
        )
        # Courses in CS Center started at 2011 year
        if self.request.site.domain != settings.CLUB_DOMAIN:
            q = (q.filter(year__gte=2011)
                .exclude(type=Case(
                    When(year=2011, then=Value(Semester.TYPES.spring)),
                    default=Value(""))
                ))
        return q

    def get_context_data(self, **kwargs):
        context = super(CoursesListView, self).get_context_data(**kwargs)
        semester_list = [s for s in context["semester_list"]
                         if s.type != Semester.TYPES.summer]
        if not semester_list:
            return context
        # Check if we only have the fall semester for the ongoing year.
        current = semester_list[0]
        if current.type == Semester.TYPES.autumn:
            semester = Semester(type=Semester.TYPES.spring,
                                year=current.year + 1)
            semester.courseofferings = []
            semester_list.insert(0, semester)
        # Hide empty pairs
        context["semester_list"] = [
            (a, s) for s, a in utils.grouper(semester_list, 2) if \
                (a and a.courseofferings) or (s and s.courseofferings)
        ]
        return context


class CourseTeacherListView(TeacherOnlyMixin,
                            generic.ListView):
    model = CourseOffering
    context_object_name = 'course_list'
    template_name = "learning/courses/list_teacher.html"

    def get_queryset(self):
        return (self.model.objects
                .filter(teachers=self.request.user)
                .order_by('-semester__year', '-semester__type', 'course__name')
                .select_related('course', 'semester')
                .prefetch_related('teachers'))

    def get_context_data(self, **kwargs):
        context = (super(CourseTeacherListView, self)
                   .get_context_data(**kwargs))
        ongoing, archive = utils.split_list(context['course_list'],
                                            lambda course: course.is_ongoing)
        context['course_list_ongoing'] = ongoing
        context['course_list_archive'] = archive
        return context


class CourseStudentListView(StudentOnlyMixin,
                            generic.TemplateView):
    model = CourseOffering
    context_object_name = 'course_list'
    template_name = "learning/courses/list_student.html"

    def get_context_data(self, **kwargs):
        year, semester_type = utils.get_current_semester_pair()
        available = (CourseOffering.custom.site_related(self.request)
                     .filter(semester__type=semester_type,
                             semester__year=year)
                     .exclude(enrolled_students=self.request.user)
                     .order_by('semester__year', '-semester__type',
                               'course__name')
                     .select_related('course', 'semester')
                     .prefetch_related('teachers'))

        enrolled_on = (Enrollment.objects
                       .filter(student=self.request.user)
                       .order_by('course_offering__semester__year',
                                 '-course_offering__semester__type',
                                 'course_offering__course__name')
                       .select_related('course_offering',
                                       'course_offering__course',
                                       'course_offering__semester')
                       .prefetch_related('course_offering__teachers'))
        ongoing, archive = utils.split_list(
            enrolled_on,
            lambda e: (e.course_offering.semester.year == year
                       and e.course_offering.semester.type == semester_type))

        context = {}
        context['course_list_available'] = available
        context['enrollments_ongoing'] = ongoing
        context['enrollments_archive'] = archive
        return context


class CourseVideoListView(generic.ListView):
    model = CourseOffering
    template_name = "learning/courses_video_list.html"
    context_object_name = 'course_list'

    def get_queryset(self):
        return (self.model.objects
                .filter(is_published_in_video=True)
                .order_by('-semester__year', 'semester__type')
                .select_related('course', 'semester'))

    def get_context_data(self, **kwargs):
        context = (super(CourseVideoListView, self)
                   .get_context_data(**kwargs))
        full = context[self.context_object_name]
        chunks = []
        for i in range(0, len(full), 3):
            chunks.append(full[i:i+3])
        context['course_list_chunks'] = chunks
        return context


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "learning/courses/detail.html"
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = (super(CourseDetailView, self)
                   .get_context_data(**kwargs))
        context['offerings'] = self.object.courseoffering_set.all()
        return context


class CourseUpdateView(CuratorOnlyMixin,
                       ProtectedFormMixin,
                       generic.UpdateView):
    model = Course
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseForm

    def is_form_allowed(self, user, obj):
        return user.is_authenticated() and user.is_curator


class GetCourseOfferingObjectMixin(object):
    model = CourseOffering

    def get_object(self):
        try:
            year, semester_type = self.kwargs['semester_slug'].split("-", 1)
            year = int(year)
        except ValueError:
            raise Http404

        return get_object_or_404(
            self.get_queryset()
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug'])
            .select_related('course',
                            'semester')
            .prefetch_related('teachers',
                              'courseclass_set',
                              'courseclass_set__venue',
                              'courseclass_set__courseclassattachment_set',
                              'courseofferingnews_set',
                              'assignment_set'))


class CourseOfferingDetailView(GetCourseOfferingObjectMixin,
                               FailedCourseContextMixin,
                               generic.DetailView):
    context_object_name = 'course_offering'
    template_name = "learning/courseoffering_detail.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        co = context[self.context_object_name]
        if settings.SITE_ID == settings.CENTER_SITE_ID and co.is_open:
            index = get_semester_index(CENTER_FOUNDATION_YEAR,
                                       SEMESTER_TYPES.autumn)
            if co.semester.index < index:
                return HttpResponseRedirect(
                    get_club_domain(co.city.code) + co.get_absolute_url())
        return self.render_to_response(context)

    def get_queryset(self):
        return self.model.custom.site_related(self.request)

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseOfferingDetailView, self)
                   .get_context_data(*args, **kwargs))
        is_enrolled = (self.request.user.is_authenticated() and
                       self.request.user.is_student and
                       (self.request.user
                        .enrolled_on_set
                        .filter(pk=self.object.pk)
                        .exists()))
        context['is_enrolled'] = is_enrolled
        context['enrollment_opened'] = context[self.context_object_name].enrollment_opened()
        is_actual_teacher = (self.request.user.is_authenticated() and
                             self.request.user in self.object.teachers.all())
        context['is_actual_teacher'] = is_actual_teacher
        assignments = self.object.assignment_set.all().order_by('deadline_at', 'title')
        for assignment in assignments:
            if is_actual_teacher or \
              (self.request.user.is_authenticated() and
               self.request.user.is_curator):
                setattr(assignment, 'magic_link',
                        reverse("assignment_detail_teacher",
                                args=[assignment.pk]))
            elif is_enrolled:
                try:
                    a_s = (StudentAssignment.objects
                           .filter(assignment=assignment,
                                   student=self.request.user)
                           .get())
                    setattr(assignment, 'magic_link',
                            reverse("a_s_detail_student", args=[a_s.pk]))
                except ObjectDoesNotExist:
                    logger.error("can't find StudentAssignment for "
                                 "student ID {0}, assignment ID {1}"
                                 .format(self.request.user.pk, assignment.pk))
        context['assignments'] = assignments
        context['can_view_assignments'] = (
            self.request.user.is_student
            or context['is_actual_teacher']
            or self.request.user.is_curator)
        context['can_view_news'] = not context['is_failed_completed_course'] and (
                                   self.request.user.is_authenticated() or
                                   self.request.site.domain == settings.CLUB_DOMAIN)

        course_classes = list(self.object.courseclass_set.all())
        for cc in course_classes:
            rev_args = [self.object.course.slug,
                        self.object.semester.slug,
                        cc.pk]
            base_url = reverse('class_detail', args=rev_args)
            base_teacher_url = reverse('course_class_edit', args=rev_args)
            materials = []
            if cc.slides:
                if is_actual_teacher:
                    url = base_teacher_url + "#div_id_slides"
                else:
                    url = base_url + "#slides"
                materials.append({'url': url,
                                  'name': _("Slides")})
            if cc.video_url:
                if is_actual_teacher:
                    url = base_teacher_url + "#div_id_video"
                else:
                    url = base_url + "#video"
                materials.append({'url': url,
                                  'name': _("CourseClass|Video")})
            if cc.courseclassattachment_set.count() > 0:
                if is_actual_teacher:
                    url = base_teacher_url + "#div_id_attachments"
                else:
                    url = base_url + "#attachments"
                materials.append({'url': url,
                                  'name': _("Files")})
            other_materials_embed = (
                cc.other_materials.startswith(
                    ("<iframe src=\"https://www.slideshare",
                     "<iframe src=\"http://www.slideshare"))
                and cc.other_materials.strip().endswith("</iframe>"))
            if cc.other_materials and not other_materials_embed:
                if is_actual_teacher:
                    url = base_teacher_url + "#div_id_other_materials"
                else:
                    url = base_url + "#other_materials"
                materials.append({'url': url,
                                  'name': _("CourseClass|Other [materials]")})
            for x in materials:
                x.update({'name': x['name'].lower()})
            materials_str = ", ".join(",&nbsp;"
                                      .join(("<a href={url}>{name}</a>"
                                             .format(**x))
                                            for x in materials[i:i+2])
                                      for i in range(0, len(materials), 2))
            materials_str = materials_str or _("No")

            setattr(cc, 'materials_str', materials_str)

        # Not sure if it's the best place for this, but it's the simplest one
        if self.request.user.is_authenticated():
            cache = get_unread_notifications_cache()
            if self.object in cache.courseoffering_news:
                (CourseOfferingNewsNotification.unread
                 .filter(course_offering_news__course_offering=self.object,
                         user=self.request.user)
                 .update(is_unread=False))

        return context


class CourseOfferingEditDescrView(TeacherOnlyMixin,
                                  ProtectedFormMixin,
                                  GetCourseOfferingObjectMixin,
                                  generic.UpdateView):
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingEditDescrForm

    def is_form_allowed(self, user, obj):
        return (user.is_authenticated() and user.is_curator) or (user in obj.teachers.all())

    def get_queryset(self):
        return self.model.custom.site_related(self.request)


class CourseOfferingNewsCreateView(TeacherOnlyMixin,
                                   ProtectedFormMixin,
                                   generic.CreateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super(CourseOfferingNewsCreateView, self).__init__(*args, **kwargs)

    def form_valid(self, form):
        form.instance.course_offering = self._course_offering
        self.success_url = self._course_offering.get_absolute_url()
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        self.object.save()
        return redirect(self.get_success_url())

    def is_form_allowed(self, user, obj):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        self._course_offering = get_object_or_404(
            CourseOffering.objects
            .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug']))
        return (user.is_authenticated() and user.is_curator) or \
               (user in self._course_offering.teachers.all())


class CourseOfferingNewsUpdateView(TeacherOnlyMixin,
                                   ProtectedFormMixin,
                                   generic.UpdateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def get_success_url(self):
        return self.object.course_offering.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return (user.is_authenticated() and user.is_curator) or \
               (user in obj.course_offering.teachers.all())


class CourseOfferingNewsDeleteView(TeacherOnlyMixin,
                                   ProtectedFormMixin,
                                   generic.DeleteView):
    model = CourseOfferingNews
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        return self.object.course_offering.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return (user.is_authenticated() and user.is_curator) or \
               (user in obj.course_offering.teachers.all())


class CourseOfferingEnrollView(StudentOnlyMixin, generic.FormView):
    http_method_names = ['post']
    form_class = CourseOfferingPKForm

    def form_valid(self, form):
        course_offering = get_object_or_404(
            CourseOffering.objects
                .filter(pk=form.cleaned_data['course_offering_pk'])
                .select_related("semester"))
        # CourseOffering enrollment should be active
        if not course_offering.enrollment_opened():
            return HttpResponseForbidden()
        # Club students can't enroll on center courses
        if self.request.site.domain == settings.CLUB_DOMAIN and \
           not course_offering.is_open:
            return HttpResponseForbidden()
        Enrollment.objects.get_or_create(
            student=self.request.user, course_offering=course_offering)
        if self.request.POST.get('back') == 'course_list_student':
            return redirect('course_list_student')
        else:
            return redirect('course_offering_detail',
                            course_slug=course_offering.course.slug,
                            semester_slug=course_offering.semester.slug)


class CourseOfferingUnenrollView(StudentOnlyMixin, generic.DeleteView):
    template_name = "learning/simple_delete_confirmation.html"

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super(CourseOfferingUnenrollView, self).__init__(*args, **kwargs)

    def get_object(self, _=None):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        course_offering = get_object_or_404(
            CourseOffering.objects
                .filter(semester__type=semester_type,
                    semester__year=year,
                    course__slug=self.kwargs['course_slug'])
                .select_related("semester"))
        self._course_offering = course_offering
        enrollment = get_object_or_404(
            Enrollment.objects.filter(student=self.request.user,
                                      course_offering=course_offering))
        if not enrollment.course_offering.enrollment_opened():
            raise PermissionDenied
        return enrollment

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseOfferingUnenrollView, self)
                   .get_context_data(*args, **kwargs))
        context['confirmation_text'] = (
            _("Are you sure you want to unenroll "
              "from \"%(course)s\"?")
            % {'course': self.object.course_offering})
        context['confirmation_button_text'] = _("Unenroll")
        return context

    def get_success_url(self):
        if self.request.GET.get('back') == 'course_list_student':
            return reverse('course_list_student')
        else:
            c_o = self._course_offering
            return reverse('course_offering_detail',
                           kwargs={"course_slug": c_o.course.slug,
                                   "semester_slug": c_o.semester.slug})


class CourseClassDetailView(generic.DetailView):
    model = CourseClass
    context_object_name = 'course_class'

    def get_context_data(self, *args, **kwargs):
        context = (super(CourseClassDetailView, self)
                   .get_context_data(*args, **kwargs))
        context['is_actual_teacher'] = (
            self.request.user.is_authenticated() and
            self.request.user in (self.object
                                  .course_offering
                                  .teachers.all()))
        context['attachments'] = self.object.courseclassattachment_set.all()
        return context


class CourseClassCreateUpdateMixin(TeacherOnlyMixin, ProtectedFormMixin):
    model = CourseClass
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseClassForm

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super(CourseClassCreateUpdateMixin, self).__init__(*args, **kwargs)

    def is_form_allowed(self, user, obj):
        return (obj is None or
                (user.is_authenticated() and user.is_curator) or
                user in obj.course_offering.teachers.all())

    def get_initial(self, *args, **kwargs):
        initial = (super(CourseClassCreateUpdateMixin, self)
                   .get_initial(*args, **kwargs))
        # Prefetch Course Offering model
        course_slug, semester_year, semester_type \
            = utils.co_from_kwargs(self.kwargs)
        base_qs = CourseOffering.custom.site_related(self.request)
        if not self.request.user.is_curator:
            base_qs = base_qs.filter(teachers=self.request.user)

        self._course_offering = get_object_or_404(
            base_qs.filter(course__slug=course_slug,
                           semester__year=semester_year,
                           semester__type=semester_type))
        # TODO: Add tests for initial data after discussion
        if isinstance(self, generic.CreateView):
            previous_class = (CourseClass.objects
                              .filter(course_offering=self._course_offering.pk)
                              .defer("description")
                              .order_by("-date", "starts_at")
                              .first())
            if previous_class is not None:
                initial["type"] = previous_class.type
                initial["venue"] = previous_class.venue
                initial["starts_at"] = previous_class.starts_at
                initial["ends_at"] = previous_class.ends_at
                initial["date"] = previous_class.date + datetime.timedelta(
                    weeks=1)
        return initial

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        if self.object is not None:
            # NOTE(Dmitry): dirty, but I don't see a better way given
            #               that forms are generated in code
            co = self.object.course_offering
            remove_links = "<ul class=\"list-unstyled\">{0}</ul>".format(
                "".join("<li>"
                        "<i class=\"fa fa-times\"></i>&nbsp;"
                        "<a href=\"{0}\">{1}</a>"
                        "</li>"
                        .format(reverse('course_class_attachment_delete',
                                        args=[co.course.slug,
                                              co.semester.slug,
                                              self.object.pk,
                                              attachment.pk]),
                                attachment.material_file_name)
                        for attachment
                        in self.object.courseclassattachment_set.all()))
        else:
            remove_links = ""
        return form_class(remove_links=remove_links,
                          **self.get_form_kwargs())

    def form_valid(self, form):
        assert self._course_offering is not None
        # FIXME: Think how to move this logic into form.
        # TODO: Move to get_form_class? Show this error ASAP
        # Can't add course classes after course already completed.
        if self._course_offering.is_completed:
            form.add_error(None, "Sorry, course already completed. "
                                 "You can't update or add classes")
            return super(CourseClassCreateUpdateMixin, self).form_invalid(form)
        self.object = form.save(commit=False)
        self.object.course_offering = self._course_offering
        self.object.save()
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            for attachment in attachments:
                CourseClassAttachment(course_class=self.object,
                                      material=attachment).save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.request.GET.get('back') == 'timetable':
            return reverse('timetable_teacher')
        if self.request.GET.get('back') == 'course_offering':
            return self._course_offering.get_absolute_url()
        if self.request.GET.get('back') == 'calendar':
            return reverse('calendar_teacher')
        elif "_addanother" in self.request.POST:
            messages.success(self.request, self.MESSAGE_SUCCESS, extra_tags='timeout')
            return reverse('course_class_add',
                           args=[self._course_offering.course.slug,
                                 self._course_offering.semester.slug])
        else:
            return super(CourseClassCreateUpdateMixin, self).get_success_url()




class CourseClassCreateView(CourseClassCreateUpdateMixin,
                            generic.CreateView):
    MESSAGE_SUCCESS = _("The class was successfully created.")


class CourseClassUpdateView(CourseClassCreateUpdateMixin,
                            generic.UpdateView):
    MESSAGE_SUCCESS = _("The class was successfully updated.")


class CourseClassAttachmentDeleteView(TeacherOnlyMixin,
                                      ProtectedFormMixin,
                                      generic.DeleteView):
    model = CourseClassAttachment
    template_name = "learning/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return (user.is_authenticated() and user.is_curator) or \
               (user in obj.course_class.course_offering.teachers.all())

    def get_success_url(self):
        co = self.object.course_class.course_offering
        return reverse('course_class_edit',
                       args=[co.course.slug,
                             co.semester.slug,
                             self.object.course_class.pk])

    def delete(self, request, *args, **kwargs):
        resp = (super(CourseClassAttachmentDeleteView, self)
                .delete(request, *args, **kwargs))
        os.remove(self.object.material.path)
        return resp


class CourseClassDeleteView(TeacherOnlyMixin,
                            ProtectedFormMixin,
                            generic.DeleteView):
    model = CourseClass
    template_name = "learning/simple_delete_confirmation.html"
    success_url = reverse_lazy('timetable_teacher')

    def is_form_allowed(self, user, obj):
        return (user.is_authenticated() and user.is_curator) or \
               (user in obj.course_offering.teachers.all())


class VenueListView(generic.ListView):
    model = Venue
    template_name = "learning/venue_list.html"

    def get_queryset(self):
        q = Venue.objects.filter(sites__pk=settings.SITE_ID)
        if hasattr(self.request, 'city'):
            q = q.filter(
                Q(city__pk=self.request.city.code) | Q(city__isnull=True))
        return q


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "learning/venue_detail.html"


class StudentAssignmentListView(StudentOnlyMixin, generic.ListView):
    """ Show assignments from current semester only. """
    model = StudentAssignment
    context_object_name = 'assignment_list'
    template_name = "learning/assignment_list_student.html"
    user_type = 'student'

    def get_queryset(self):
        current_semester = Semester.get_current()
        self.current_semester = current_semester
        return (self.model.objects
                .filter(
                    student=self.request.user,
                    assignment__course_offering__semester=current_semester)
                .order_by('assignment__deadline_at',
                          'assignment__course_offering__course__name',
                          'pk')
                # FIXME: this prefetch doesn't seem to work
                .prefetch_related('assignmentnotification_set')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester',
                                'student'))

    def get_context_data(self, *args, **kwargs):
        context = (super(StudentAssignmentListView, self)
                   .get_context_data(*args, **kwargs))
        # Get active student enrollments and then related co's
        actual_co = (Enrollment.objects.filter(
            course_offering__semester=self.current_semester,
            student=self.request.user).values_list("course_offering", flat=True))
        open_, archive = utils.split_list(
            context['assignment_list'],
            lambda a_s: a_s.assignment.is_open and a_s.assignment.course_offering.pk in actual_co)
        archive.reverse()
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        context['user_type'] = self.user_type
        return context


class AssignmentTeacherListView(TeacherOnlyMixin,
                                generic.ListView):
    model = StudentAssignment
    context_object_name = 'assignment_list'
    template_name = "learning/assignment_list_teacher.html"
    user_type = 'teacher'

    def get_queryset(self):
        base_qs = \
            (self.model.objects
             .filter(assignment__course_offering__teachers=self.request.user,
                     grade__isnull=True)
             .order_by('assignment__course_offering__course__name',
                       'assignment__deadline_at',
                       'assignment__pk',
                       'last_commented')
             .select_related('assignment',
                             'assignment__course_offering',
                             'assignment__course_offering__course',
                             'assignment__course_offering__semester',
                             'student'))
        if self.request.GET.get('show_all') == 'true':
            return base_qs
        else:
            return base_qs.filter(assignment__is_online=True,
                                  grade__isnull=True)

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentTeacherListView, self)
                   .get_context_data(*args, **kwargs))
        if self.request.GET.get('show_all') == 'true':
            open_ = context['assignment_list']
        else:
            open_ = [a_s
                     for a_s in context['assignment_list']
                     if a_s.last_commented]
        archive = (Assignment.objects
                   .filter(course_offering__teachers=self.request.user)
                   .order_by('-deadline_at',
                             'course_offering__course__name',
                             'pk')
                   .select_related('course_offering',
                                   'course_offering__course',
                                   'course_offering__semester'))
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        context['user_type'] = self.user_type
        context['show_all'] = \
            (self.request.GET.get('show_all') == 'true')
        return context


class AssignmentTeacherDetailView(TeacherOnlyMixin,
                                  generic.DetailView):
    model = Assignment
    template_name = "learning/assignment_detail_teacher.html"
    context_object_name = 'assignment'

    def get_queryset(self):
        return (self.model.objects
                .select_related('course_offering',
                                'course_offering__course',
                                'course_offering__semester')
                .prefetch_related('assignmentattachment_set'))

    def get_context_data(self, *args, **kwargs):
        context = (super(AssignmentTeacherDetailView, self)
                   .get_context_data(*args, **kwargs))

        is_actual_teacher = (
            self.request.user in (self.object
                                  .course_offering
                                  .teachers.all()))
        if not is_actual_teacher and (not self.request.user.is_authenticated()
           or not self.request.user.is_curator):
            raise PermissionDenied
        context['a_s_list'] = \
            (StudentAssignment.objects
             .filter(assignment__pk=self.object.pk)
             .select_related('assignment',
                             'assignment__course_offering',
                             'assignment__course_offering__course',
                             'assignment__course_offering__semester',
                             'student')
             .prefetch_related('student__groups'))
        return context


class StudentAssignmentDetailMixin(object):
    model = AssignmentComment
    template_name = "learning/student_assignment_detail.html"
    form_class = AssignmentCommentForm

    def get_context_data(self, *args, **kwargs):
        context = (super(StudentAssignmentDetailMixin, self)
                   .get_context_data(*args, **kwargs))
        pk = self.kwargs.get('pk')
        a_s = get_object_or_404(
            StudentAssignment
            .objects
            .filter(pk=pk)
            .select_related('assignment',
                            'student',
                            'assignment__course_offering',
                            'assignment__course_offering__course',
                            'assignment__course_offering__semester')
            .prefetch_related('assignment__course_offering__teachers',
                              'assignment__assignmentattachment_set'))

        # Not sure if it's the best place for this, but it's the simplest one
        (AssignmentNotification.unread
         .filter(student_assignment=a_s, user=self.request.user)
         .update(is_unread=False))

        self._additional_permissions_check(a_s=a_s)

        context['a_s'] = a_s
        context['course_offering'] = a_s.assignment.course_offering
        context['user_type'] = self.user_type

        comments = (AssignmentComment.objects.filter(student_assignment=a_s)
                                             .order_by('created')
                                             .select_related('author'))
        for c in comments:
            if c.author == a_s.student:
                setattr(c, 'first_student_comment', True)
                break
        context['comments'] = comments
        context['one_teacher'] = (a_s
                                  .assignment
                                  .course_offering
                                  .teachers
                                  .count() == 1)
        context['hashes_json'] = comment_persistence.get_hashes_json()
        return context

    def _additional_permissions_check(self, *args, **kwargs):
        pass

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        a_s = get_object_or_404(StudentAssignment.objects.filter(pk=pk))
        comment = form.save(commit=False)
        comment.student_assignment = a_s
        comment.author = self.request.user
        comment.save()
        comment_persistence.report_saved(comment.text)
        return redirect(self.get_success_url())


# shitty name :(
# Note: We should redirects teacher, so replace StudentOnlyMixin with ParticipantOnlyMixin.
# TODO: Practice says it's not really good idea to use generic for this action. Refactor ASAP?
class StudentAssignmentStudentDetailView(ParticipantOnlyMixin,
                                         FailedCourseContextMixin,
                                         StudentAssignmentDetailMixin,
                                         generic.CreateView):
    user_type = 'student'

    def get(self, request, *args, **kwargs):
        try:
            response = super(StudentAssignmentStudentDetailView, self).get(request, *args,
                                                                           **kwargs)
        except Redirect as e:
            return HttpResponseRedirect(e.kwargs.get('url'))
        return response

    def get_context_data(self, *args, **kwargs):
        context = (super(StudentAssignmentStudentDetailView, self)
                   .get_context_data(*args, **kwargs))
        if context['is_failed_completed_course']:
            raise PermissionDenied
        return context

    def _additional_permissions_check(self, *args, **kwargs):
        a_s = kwargs.get("a_s")
        user = self.request.user
        if user in a_s.assignment.course_offering.teachers.all():
            raise Redirect(url=reverse("a_s_detail_teacher", args=[a_s.pk]))
        # This should guard against reading other's assignments. Not generic
        # enough, but can't think of better way
        if not a_s.student == user and not user.is_curator:
            raise Redirect(url="{}?next={}".format(settings.LOGIN_URL,
                                                   self.request.get_full_path()))

    def get_success_url(self):
        pk = self.kwargs.get('pk')
        return reverse('a_s_detail_student', args=[pk])


class StudentAssignmentTeacherDetailView(TeacherOnlyMixin,
                                         StudentAssignmentDetailMixin,
                                         generic.CreateView):
    user_type = 'teacher'

    def get_context_data(self, *args, **kwargs):
        context = (super(StudentAssignmentTeacherDetailView, self)
                   .get_context_data(*args, **kwargs))
        a_s = context['a_s']
        co = a_s.assignment.course_offering
        initial = {'grade': a_s.grade}
        is_actual_teacher = (
            self.request.user in (a_s
                                  .assignment
                                  .course_offering
                                  .teachers.all()))
        if (not is_actual_teacher and not self.request.user.is_curator):
            raise PermissionDenied
        context['is_actual_teacher'] = is_actual_teacher
        context['grade_form'] = AssignmentGradeForm(
            initial, grade_max=a_s.assignment.grade_max)
        base = (
            StudentAssignment.objects
            .filter(grade__isnull=True,
                    is_passed=True,
                    assignment__course_offering=co,
                    assignment__course_offering__teachers=self.request.user)
            .order_by('assignment__deadline_at',
                      'assignment__course_offering__course__name',
                      'pk'))
        next_a_s = (base.filter(pk__gt=a_s.pk).first() or
                    base.filter(pk__lt=a_s.pk).first())
        context['next_a_s_pk'] = next_a_s.pk if next_a_s else None
        return context

    def post(self, request, *args, **kwargs):
        if 'grading_form' in request.POST:
            pk = self.kwargs.get('pk')
            a_s = get_object_or_404(StudentAssignment.objects.filter(pk=pk))
            form = AssignmentGradeForm(request.POST,
                                       grade_max=a_s.assignment.grade_max)

            # Too hard to use ProtectedFormMixin here, let's just inline it's
            # logic. A little drawback is that teachers still can leave
            # comments under other's teachers assignments, but can not grade,
            # so it's acceptable, IMO.
            teachers = a_s.assignment.course_offering.teachers.all()
            if request.user not in teachers:
                raise PermissionDenied

            if form.is_valid():
                a_s.grade = form.cleaned_data['grade']
                a_s.save()
                return redirect(reverse('a_s_detail_teacher', args=[pk]))
            else:
                # not sure if we can do anything more meaningful here.
                # it shoudn't happen, after all.
                return HttpResponseBadRequest(_("Grading form is invalid") +
                                              "{}".format(form.errors))
        else:
            return (super(StudentAssignmentTeacherDetailView, self)
                    .post(request, *args, **kwargs))

    def get_success_url(self):
        pk = self.kwargs.get('pk')
        return reverse('a_s_detail_teacher', args=[pk])


class AssignmentCreateUpdateMixin(TeacherOnlyMixin, ProtectedFormMixin):
    model = Assignment
    template_name = "learning/simple_crispy_form.html"
    form_class = AssignmentForm
    success_url = reverse_lazy('assignment_list_teacher')

    def __init__(self, *args, **kwargs):
        self._course_offering = None
        super(AssignmentCreateUpdateMixin, self).__init__(*args, **kwargs)

    def is_form_allowed(self, user, obj):
        return (obj is None or
                (user.is_authenticated() and user.is_curator) or
                user in obj.course_offering.teachers.all())

    def get_initial(self):
        initial = super(AssignmentCreateUpdateMixin, self).get_initial()
        course_slug, semester_year, semester_type \
            = utils.co_from_kwargs(self.kwargs)
        if self.request.user.is_authenticated() and self.request.user.is_curator:
            base_qs = CourseOffering.objects
        else:
            base_qs = (CourseOffering.objects
                       .filter(teachers=self.request.user))
        self._course_offering = get_object_or_404(
            base_qs.filter(course__slug=course_slug,
                           semester__year=semester_year,
                           semester__type=semester_type))
        initial['course_offering'] = self._course_offering
        return initial

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        if self.object is not None:
            # NOTE(Dmitry): dirty, but I don't see a better way given
            #               that forms are generated in code
            co = self.object.course_offering
            remove_links = "<ul class=\"list-unstyled\">{0}</ul>".format(
                "".join("<li>"
                        "<i class=\"fa fa-times\"></i>&nbsp;"
                        "<a href=\"{0}\">{1}</a>"
                        "</li>"
                        .format(reverse('assignment_attachment_delete',
                                        args=[co.course.slug,
                                              co.semester.slug,
                                              self.object.pk,
                                              aa.pk]),
                                aa.file_name)
                        for aa
                        in self.object.assignmentattachment_set.all()))
        else:
            remove_links = ""
        return form_class(remove_links=remove_links,
                          **self.get_form_kwargs())


    def get_success_url(self):
        return reverse('course_offering_detail',
                       args=[self._course_offering.course.slug,
                             self._course_offering.semester.slug])

    def form_valid(self, form):
        self.object = form.save(commit=False)
        assert self._course_offering is not None
        self.object.course_offering = self._course_offering
        self.object.save()
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            for attachment in attachments:
                (AssignmentAttachment.objects
                 .create(assignment=self.object,
                         attachment=attachment))
        return redirect(self.get_success_url())


class AssignmentCreateView(AssignmentCreateUpdateMixin,
                           generic.CreateView):
    pass


# Same here
class AssignmentUpdateView(AssignmentCreateUpdateMixin,
                           generic.UpdateView):
    pass


class AssignmentDeleteView(TeacherOnlyMixin,
                           ProtectedFormMixin,
                           generic.DeleteView):
    model = Assignment
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        return reverse('assignment_list_teacher')

    def is_form_allowed(self, user, obj):
        return (user.is_authenticated() and user.is_curator) or \
               (user in obj.course_offering.teachers.all())


class AssignmentAttachmentDeleteView(TeacherOnlyMixin,
                                     ProtectedFormMixin,
                                     generic.DeleteView):
    model = AssignmentAttachment
    template_name = "learning/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return (user.is_authenticated() and user.is_curator) or \
               (user in obj.assignment.course_offering.teachers.all())

    def get_success_url(self):
        co = self.object.assignment.course_offering
        return reverse('assignment_edit',
                       args=[co.course.slug,
                             co.semester.slug,
                             self.object.assignment.pk])

    def delete(self, request, *args, **kwargs):
        resp = (super(AssignmentAttachmentDeleteView, self)
                .delete(request, *args, **kwargs))
        os.remove(self.object.attachment.path)
        return resp


class MarksSheetTeacherDispatchView(TeacherOnlyMixin,
                                    generic.ListView):
    class RedirectException(Exception):
        def __init__(self, url):
            self.url = url

    is_for_staff = None
    ms_url_name = None
    model = Semester
    template_name = "learning/markssheet_teacher_dispatch.html"

    def __init__(self, *args, **kwargs):
        super(MarksSheetTeacherDispatchView, self).__init__(*args, **kwargs)
        if kwargs.get('is_for_staff'):
            self.is_for_staff = True
            self.ms_url_name = 'course_markssheet_staff'
        else:
            self.is_for_staff = False
            self.ms_url_name = 'markssheet_teacher'

    def get(self, request, *args, **kwargs):
        try:
            return (super(MarksSheetTeacherDispatchView, self)
                    .get(request, *args, **kwargs))
        except MarksSheetTeacherDispatchView.RedirectException as re:
            return HttpResponseRedirect(re.url)

    def get_queryset(self):
        current_year, semester_type = get_current_semester_pair()
        semester_index = get_semester_index(current_year, semester_type)
        if semester_type == Semester.TYPES.autumn:
            semester_index += SEMESTER_AUTUMN_SPRING_INDEX_DIFF  # skip to spring semester
        return (self.model.objects
                .filter(index__lte=semester_index)
                .exclude(type=Semester.TYPES.summer)
                .prefetch_related("courseoffering_set",
                                  "courseoffering_set__course"))

    def get_context_data(self, *args, **kwargs):
        context = (super(MarksSheetTeacherDispatchView, self)
                   .get_context_data(**kwargs))
        semester_list = [s for s in context["semester_list"]
                           if s.type != Semester.TYPES.summer]
        if not semester_list:
            return context

        now_ = now()
        for semester in semester_list:
            if self.request.user.is_authenticated() and self.request.user.is_curator:
                cos = semester.courseoffering_set.all()
            else:
                cos = (semester.courseoffering_set
                       .filter(teachers=self.request.user))
            semester.courseofferings = sorted(
                cos,
                key=lambda co: co.course.name)
            if len(semester.courseofferings) == 1 \
               and semester.starts_at <= now_ <= semester.ends_at:
                co = semester.courseofferings[0]
                url = reverse(self.ms_url_name,
                              args=[co.course.slug,
                                    co.semester.year,
                                    co.semester.type])
                raise MarksSheetTeacherDispatchView.RedirectException(url)

        # Check if we only have the fall semester for the ongoing year.
        current = semester_list[0]
        if current.type == Semester.TYPES.autumn:
            semester = Semester(type=Semester.TYPES.spring,
                                year=current.year + 1)
            semester.courseofferings = []
            semester_list.insert(0, semester)

        context["semester_list"] = [
            (a, s) for s, a in utils.grouper(semester_list, 2)]
        context['ms_url_name'] = self.ms_url_name
        return context


class MarksSheetTeacherView(TeacherOnlyMixin,
                            generic.FormView):
    is_for_staff = False
    user_type = 'teacher'
    template_name = "learning/gradebook.html"
    context_object_name = 'assignment_list'

    def __init__(self, *args, **kwargs):
        self.student_assignments = None
        self.enrollment_list = None
        self.course_offering_list = None
        self.course_offering = None
        super(MarksSheetTeacherView, self).__init__(*args, **kwargs)
        self.is_for_staff = kwargs.get('is_for_staff', False)

    def get_form_class(self):
        try:
            semester_year = int(self.kwargs['semester_year'])
        except (ValueError, TypeError):
            raise Http404('Course offering not found')

        co_queryset = CourseOffering.objects
        if not self.request.user.is_curator:
            co_queryset = co_queryset.filter(teachers=self.request.user)

        try:
            course_offering = (co_queryset
                  .select_related('semester', 'course')
                  .get(course__slug=self.kwargs['course_slug'],
                       semester__type=self.kwargs['semester_type'],
                       semester__year=semester_year))
        except ObjectDoesNotExist:
            raise Http404('Course offering not found')
        self.course_offering = course_offering

        # Sacrifice attributes access for better performance
        student_assignments = (
            StudentAssignment.objects
                .filter(assignment__course_offering=course_offering)
                .values("pk",
                        "grade",
                        "is_passed",
                        "assignment__pk",
                        "assignment__title",
                        "assignment__is_online",
                        "assignment__grade_max",
                        "assignment__grade_min",
                        "student__pk")
                .order_by("assignment__pk",
                          "student__pk")
        )
        self.student_assignments = student_assignments

        enrollment_list = (Enrollment.objects
                           .filter(course_offering=course_offering)
                           .select_related("student"))
        self.enrollment_list = enrollment_list

        course_offering_list = (co_queryset
                                .order_by('-semester__year',
                                          '-semester__type',
                                          '-pk')
                                .select_related('semester', 'course'))
        self.course_offering_list = course_offering_list

        return (GradeBookFormFactory.build_form_class(student_assignments,
                                                      enrollment_list))

    def get_initial(self):
        return (GradeBookFormFactory
                .transform_to_initial(self.student_assignments, self.enrollment_list))

    def get_success_url(self):
        co = self.course_offering
        if self.is_for_staff:
            url_name = 'course_markssheet_staff'
        else:
            url_name = 'markssheet_teacher'
        return reverse(url_name, args=[co.course.slug,
                                       co.semester.year,
                                       co.semester.type])

    def form_valid(self, form):
        a_s_index, enrollment_index = \
            GradeBookFormFactory.build_indexes(self.student_assignments,
                                               self.enrollment_list)
        for field in form.changed_data:
            if field in a_s_index:
                a_s = a_s_index[field]
                StudentAssignment.objects.filter(pk=a_s["pk"]).update(grade=form.cleaned_data[field])
                continue
            # Looking for final_grade_*
            elif field in enrollment_index:
                enrollment = enrollment_index[field]
                enrollment.grade = form.cleaned_data[field]
                enrollment.save()
                continue
        return redirect(self.get_success_url())

    def get_context_data(self, *args, **kwargs):
        context = (super(MarksSheetTeacherView, self)
                   .get_context_data(*args, **kwargs))
        context['course_offering'] = self.course_offering
        context['course_offering_list'] = self.course_offering_list
        context['user_type'] = self.user_type

        students = OrderedDict()
        assignments = OrderedDict()

        def get_final_grade_widget(enrollment_pk):
            key = GradeBookFormFactory.FINAL_GRADE_PREFIX.format(enrollment_pk)
            return kwargs['form'][key]

        for enrollment in self.enrollment_list:
            student_id = enrollment.student_id
            if student_id not in students:
                students[student_id] = OrderedDict({
                    "student": enrollment.student,
                    "grade": get_final_grade_widget(enrollment.pk),
                    "total": 0
                })

        for a_s in self.student_assignments:
            student_id = a_s["student__pk"]
            assignment_id = a_s["assignment__pk"]
            # The student unsubscribed from the course
            if student_id not in students:
                continue

            if assignment_id not in assignments:
                assignments[assignment_id] = {
                    "header": {
                        "pk": a_s["assignment__pk"],
                        "title": a_s["assignment__title"],
                        "is_online": a_s["assignment__is_online"],
                        "grade_min": a_s["assignment__grade_min"],
                        "grade_max": a_s["assignment__grade_max"],
                    },
                    "students": OrderedDict(((sid, None) for sid in students))
                }
            assignment = assignments[assignment_id]

            state = None
            if assignment["header"]["is_online"]:
                state_value = StudentAssignment.calculate_state(
                    a_s["grade"],
                    assignment["header"]["is_online"],
                    a_s["is_passed"],
                    assignment["header"]["grade_min"],
                    assignment["header"]["grade_max"],
                )
                if a_s["grade"] is not None:
                    state = "{0}/{1}".format(a_s["grade"],
                                             assignment["header"]["grade_max"])
                else:
                    state = StudentAssignment.SHORT_STATES[state_value]
            assignment["students"][student_id] = {
                "pk": a_s["pk"],
                "grade": a_s["grade"],
                "is_passed": a_s["is_passed"],
                "state": state
            }

            if a_s["grade"] is not None:
                students[student_id]["total"] += int(a_s["grade"])

        for assignment in assignments.values():
            # we should check for "assignment consistency": that all
            # student assignments are presented
            assert any(s is not None for s in assignment["students"])

        context['students'] = students
        context['assignments'] = assignments
        # Magic "100" constant - width of .assignment column
        context['assignments_width'] = len(assignments) * 100

        return context


class MarksSheetTeacherCSVView(TeacherOnlyMixin,
                               generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        course_slug = kwargs['course_slug']
        semester_slug = kwargs['semester_slug']
        try:
            semester_year, semester_type = semester_slug.split('-')
            semester_year = int(semester_year)
        except (ValueError, TypeError):
            raise Http404('Course offering not found')
        if request.user.is_authenticated() and request.user.is_curator:
            base_qs = CourseOffering.objects
        else:
            base_qs = CourseOffering.objects.filter(teachers=request.user)
        try:
            co = base_qs.get(
                course__slug=course_slug,
                semester__type=semester_type,
                semester__year=semester_year)
        except ObjectDoesNotExist:
            raise Http404('Course offering not found')
        a_ss = (StudentAssignment.objects
                .filter(assignment__course_offering=co)
                .order_by('student', 'assignment')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester',
                                'student'))
        enrollments = (Enrollment.objects
                       .filter(course_offering=co)
                       .select_related('course_offering', 'student'))
        structured = OrderedDict()
        enrollment_grades = {}
        for enrollment in enrollments:
            student = enrollment.student
            enrollment_grades[student] = enrollment.grade_display
            if student not in structured:
                structured[student] = OrderedDict()
        for a_s in a_ss:
            if a_s.student not in structured:
                continue  # student isn't enrolled
            structured[a_s.student][a_s.assignment] = a_s.grade

        header = viewvalues(structured)
        header = next(iter(header)).keys()
        for _, by_assignment in structured.items():
            # we should check for "assignment consistency": that all
            # assignments are similar for all students in particular
            # course offering
            assert by_assignment.keys() == header

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename \
            = "{}-{}.csv".format(kwargs['course_slug'],
                                 kwargs['semester_slug'])
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)
        writer.writerow(['Фамилия'.encode('utf8'),
                         'Имя'.encode('utf8'),
                         'Яндекс ID'.encode('utf8')]
                        + [smart_text(a.title).encode('utf8')
                           for a in header]
                        + ['Итоговая оценка'.encode('utf8')])
        for student, by_assignment in structured.items():
            writer.writerow([(smart_text(x if x is not None else '')
                              .encode('utf8'))
                             for x in
                             ([student.last_name, student.first_name, student.yandex_id]
                              + by_assignment.values()
                              + [enrollment_grades[student]])])
        return response


class MarksSheetTeacherImportCSVFromStepicView(TeacherOnlyMixin, generic.View):
    """Import students grades from stepic platform"""
    def post(self, request, *args, **kwargs):
        filter = dict(pk=self.kwargs.get('course_offering_pk'))
        if not request.user.is_authenticated() or not request.user.is_curator:
            filter['teachers__in'] = [request.user.pk]
        co = get_object_or_404(CourseOffering, **filter)
        url = reverse('markssheet_teacher',
                      args=[co.course.slug, co.semester.year, co.semester.type])
        form = MarksSheetTeacherImportGradesForm(
            request.POST, request.FILES, c_slug = co.course.slug)
        if form.is_valid():
            ImportGradesByStepicID(request,
                                         form.cleaned_data[
                                             'assignment']).process()
        else:
            # TODO: provide better description
            messages.info(request, _('Invalid form.'))
        return HttpResponseRedirect(url)


class MarksSheetTeacherImportCSVFromYandexView(TeacherOnlyMixin, generic.View):
    """Import students grades by yandex login"""
    def post(self, request, *args, **kwargs):
        filter = dict(pk=self.kwargs.get('course_offering_pk'))
        if not request.user.is_authenticated() or not request.user.is_curator:
            filter['teachers__in'] = [request.user.pk]
        co = get_object_or_404(CourseOffering, **filter)
        url = reverse('markssheet_teacher',
                      args=[co.course.slug, co.semester.year, co.semester.type])
        form = MarksSheetTeacherImportGradesForm(
            request.POST, request.FILES, c_slug = co.course.slug)
        if form.is_valid():
            ImportGradesByYandexLogin(request,
                                      form.cleaned_data['assignment']).process()
        else:
            # TODO: provide better description
            messages.info(request, _('Invalid form.'))
        return HttpResponseRedirect(url)


class NonCourseEventDetailView(generic.DetailView):
    model = NonCourseEvent
    context_object_name = 'event'
    template_name = "learning/noncourseevent_detail.html"


class OnlineCoursesListView(generic.ListView):
    context_object_name = 'courses'
    model = OnlineCourse

    def get_context_data(self, **kwargs):
        context = super(OnlineCoursesListView, self).get_context_data(**kwargs)
        context["recent_courses"] = filter(
            lambda c: not c.is_self_paced and (not c.end or c.end > now()),
            context[self.context_object_name])
        context["self_paced_courses"] = sorted(filter(
            lambda c: c.is_self_paced,
            context[self.context_object_name]), key=lambda c: c.name)
        context["archive_courses"] = filter(lambda c: c.end and c.end <= now(),
                                   context[self.context_object_name])
        return context

    def get_queryset(self):
        return OnlineCourse.objects.order_by("is_self_paced", "-start", "name")


class InternationalSchoolsListView(generic.ListView):
    model = InternationalSchool
    context_object_name = 'schools'
    template_name = "learning/international_schools.html"

    def get_queryset(self):
        return InternationalSchool.objects.order_by("-deadline")


class AssignmentAttachmentDownloadView(LoginRequiredMixin, generic.View):

    def get(self, request, *args, **kwargs):
        try:
            attachment_type, pk = hashids.decode(kwargs['sid'])
        except IndexError:
            raise Http404
        if attachment_type == ASSIGNMENT_TASK_ATTACHMENT:
            qs = AssignmentAttachment.objects.filter(pk=pk)
            assignment_attachment = get_object_or_404(qs)
            file_name = assignment_attachment.file_name
            file_url = assignment_attachment.attachment.url
        elif attachment_type == ASSIGNMENT_COMMENT_ATTACHMENT:
            qs = AssignmentComment.objects.filter(pk=pk)
            if not request.user.is_teacher and not request.user.is_curator:
                qs = qs.filter(student_assignment__student_id=request.user.pk)
            comment = get_object_or_404(qs)
            file_name = comment.attached_file_name
            file_url = comment.attached_file.url

        response = HttpResponse()
        del response['Content-Type']
        response['Content-Disposition'] = \
            "attachment; filename={}".format(file_name)
        response['X-Accel-Redirect'] = file_url
        return response
