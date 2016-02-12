# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import io
from abc import ABCMeta, abstractmethod

import six
import unicodecsv
from collections import OrderedDict, defaultdict

from django.core.urlresolvers import reverse
from django.db.models import F, Count, Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_str, smart_unicode, smart_text, \
    force_unicode
from django.views import generic
from django.http import HttpResponse, JsonResponse, Http404
from braces.views import LoginRequiredMixin, JSONResponseMixin
from xlsxwriter import Workbook

from core.views import SuperUserOnlyMixin
from learning.viewmixins import CuratorOnlyMixin
from learning.models import StudentProject, Semester
from learning.utils import get_current_semester_pair, get_semester_index
from learning.settings import STUDENT_STATUS
from users.models import CSCUser, CSCUserFilter, CSCUserStatusLog


class StudentSearchJSONView(CuratorOnlyMixin, JSONResponseMixin, generic.View):
    content_type = u"application/javascript; charset=utf-8"
    limit = 1000

    def get(self, request, *args, **kwargs):
        qs = CSCUser.objects.values('first_name', 'last_name', 'pk')
        filter = CSCUserFilter(request.GET, qs)
        # FIXME: move to CSCUserFilter
        if filter.empty_query:
            return JsonResponse(dict(users=[], there_is_more=False))
        filtered_users = filter.qs[:self.limit + 1]
        for u in filtered_users:
            u['url'] = reverse('user_detail', args=[u['pk']])
        # return HttpResponse("<html><body>body tag should be returned</body></html>", content_type='text/html; charset=utf-8')
        # TODO: JsonResponse returns unicode. Hard to debug.
        return self.render_json_response({
            "total": len(filtered_users[:self.limit]),
            "users": filtered_users[:self.limit],
            "there_is_more": len(filtered_users) > self.limit
        })


class StudentSearchView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/student_search.html"

    def get_context_data(self, **kwargs):
        context = super(StudentSearchView, self).get_context_data(**kwargs)
        context['json_api_uri'] = reverse('student_search_json')
        context['enrollment_years'] = (CSCUser.objects
                                       .values_list('enrollment_year', flat=True)
                                       .filter(enrollment_year__isnull=False)
                                       .order_by('enrollment_year')
                                       .distinct())
        context['groups'] = CSCUserFilter.FILTERING_GROUPS
        context['groups'] = {gid: CSCUser.group_pks[gid] for gid in
                             context["groups"]}
        context['status'] = CSCUser.STATUS
        context["status"] = {sid: name for sid, name in context["status"]}
        context["cnt_enrollments"] = range(CSCUserFilter.ENROLLMENTS_CNT_LIMIT + 1)
        return context

class StudentsDiplomasView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas.html"

    def get_context_data(self, **kwargs):
        context = super(StudentsDiplomasView, self).get_context_data(**kwargs)
        context['students'] = CSCUser.objects.students_info(filter={
            "status": CSCUser.STATUS.will_graduate
        })
        for student in context['students']:
            student.projects = StudentProject.sorted(student.projects)

        return context


class StudentsDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        students = CSCUser.objects.students_info(filter={
            "status": CSCUser.STATUS.will_graduate
        })

        # Prepare courses and student projects data
        courses_headers = OrderedDict()
        shads_max = 0
        projects_max = 0
        for s in students:
            student_courses = defaultdict(lambda: {'teachers': '', 'grade': ''})
            for e in s.enrollments:
                courses_headers[e.course_offering.course.id] = \
                    e.course_offering.course.name
                teachers = [t.get_full_name() for t
                            in e.course_offering.teachers.all()]
                student_courses[e.course_offering.course.id] = dict(
                    grade=e.grade_display.lower(),
                    teachers=", ".join(teachers)
                )
            s.courses = student_courses

            if len(s.shads) > shads_max:
                shads_max = len(s.shads)

            if len(s.projects) > projects_max:
                projects_max = len(s.projects)
            s.projects = StudentProject.sorted(s.projects)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = "diplomas_{}.csv".format(datetime.datetime.now().year)
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)
        w = unicodecsv.writer(response, encoding='utf-8')

        headers = ['Фамилия', 'Имя', 'Отчество', 'Университет', 'Направления']
        for course_id, course_name in six.iteritems(courses_headers):
            headers.append(course_name + ', оценка')
            headers.append(course_name + ', преподаватели')
        for i in xrange(1, shads_max + 1):
            headers.append('ШАД, курс {}, название'.format(i))
            headers.append('ШАД, курс {}, оценка'.format(i))
        for i in xrange(1, projects_max + 1):
            headers.append('Проект {}, оценка'.format(i))
            headers.append('Проект {}, руководитель(и)'.format(i))
            headers.append('Проект {}, семестр'.format(i))
        w.writerow(headers)

        for s in students:
            row = [s.last_name, s.first_name, s.patronymic, s.university,
                   " и ".join((s.name for s in s.study_programs.all()))]
            for course_id in courses_headers:
                sc = s.courses[course_id]
                row.extend([sc['grade'], sc['teachers']])

            s.shads.extend([None] * (shads_max - len(s.shads)))
            for shad in s.shads:
                if shad is not None:
                    row.extend([shad.name, shad.grade])
                else:
                    row.extend(['', ''])

            s.projects.extend([None] * (projects_max - len(s.projects)))
            for p in s.projects:
                if p is not None:
                    row.extend([p.name, p.supervisor, p.semester])
                else:
                    row.extend(['', '', ''])
            w.writerow(row)

        return response


class ExportsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/exports.html"


class StudentsAllSheetCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        students = CSCUser.objects.students_info()

        # Prepare courses and student projects data
        courses_headers = OrderedDict()
        shads_max = 0
        online_courses_max = 0
        projects_max = 0
        for s in students:
            student_courses = defaultdict(lambda: {'teachers': '', 'grade': ''})
            for e in s.enrollments:
                courses_headers[e.course_offering.course.id] = \
                    e.course_offering.course.name
                teachers = [t.get_full_name() for t
                            in e.course_offering.teachers.all()]
                student_courses[e.course_offering.course.id] = dict(
                    grade=e.grade_display.lower(),
                    teachers=", ".join(teachers)
                )
            s.courses = student_courses

            if len(s.shads) > shads_max:
                shads_max = len(s.shads)

            if len(s.online_courses) > online_courses_max:
                online_courses_max = len(s.online_courses)

            if len(s.projects) > projects_max:
                projects_max = len(s.projects)
            s.projects = StudentProject.sorted(s.projects)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        now = datetime.datetime.now()
        filename = "sheet_{}.csv".format(now.strftime("%d.%m.%Y"))
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)
        w = unicodecsv.writer(response, encoding='utf-8')

        headers = [
            'Фамилия',
            'Имя',
            'Отчество',
            'Вольнослушатель',
            'ВУЗ',
            'Курс (на момент поступления)',
            'Год поступления',
            'Год выпуска',
            'Почта',
            'Яндекс ID',
            'Телефон',
            'Направления обучения',
            'Статус',
            'Дата статуса или итога (изменения)',
            'Комментарий',
            'Дата последнего изменения комментария',
            'Работа',
            'Сдано курсов',
            'Ссылка на профиль',
        ]
        for course_id, course_name in six.iteritems(courses_headers):
            headers.append(course_name + ', оценка')
            headers.append(course_name + ', преподаватели')
        for i in xrange(1, projects_max + 1):
            headers.append('Проект {}, оценка'.format(i))
            headers.append('Проект {}, руководитель(и)'.format(i))
            headers.append('Проект {}, семестр(ы)'.format(i))
        for i in xrange(1, shads_max + 1):
            headers.append('ШАД, курс {}, название'.format(i))
            headers.append('ШАД, курс {}, преподаватели'.format(i))
            headers.append('ШАД, курс {}, оценка'.format(i))
        for i in xrange(1, online_courses_max + 1):
            headers.append('Онлайн-курс {}, название'.format(i))
        w.writerow(headers)

        for s in students:
            row = [
                s.last_name,
                s.first_name,
                s.patronymic,
                "+" if s.is_volunteer else "",
                s.university,
                s.uni_year_at_enrollment,
                s.enrollment_year,
                s.graduation_year,
                s.email,
                s.yandex_id,
                s.phone,
                " и ".join((s.name for s in s.study_programs.all())),
                s.status_display,
                '',
                s.comment,
                s.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
                s.workplace,
                len(s.courses) + len(s.shads) + len(s.online_courses),
                request.build_absolute_uri(s.get_absolute_url())
            ]

            for course_id in courses_headers:
                sc = s.courses[course_id]
                row.extend([sc['grade'], sc['teachers']])

            s.projects.extend([None] * (projects_max - len(s.projects)))
            for p in s.projects:
                if p is not None:
                    row.extend([p.name, p.supervisor, p.semester])
                else:
                    row.extend(['', '', ''])

            s.shads.extend([None] * (shads_max - len(s.shads)))
            for shad in s.shads:
                if shad is not None:
                    row.extend([shad.name, shad.teachers, shad.grade_display])
                else:
                    row.extend(['', '', ''])

            s.online_courses.extend([None] * (online_courses_max -
                                              len(s.online_courses)))
            for online_course in s.online_courses:
                if online_course is not None:
                    row.extend([online_course.name])
                else:
                    row.extend([''])

            w.writerow(row)
        return response


class StudentSummaryBySemesterMixin(object):
    def get(self, request, *args, **kwargs):
        try:
            semester_year = int(self.kwargs['semester_year'])
            semester_type = self.kwargs['semester_type']
            filter = {
                "year": semester_year,
                "type": semester_type
            }
            semester = get_object_or_404(Semester, **filter)
        except KeyError:
            semester = Semester.get_current()

        students = CSCUser.objects.students_info(
            filter={
                "groups__in": [
                    CSCUser.group_pks.STUDENT_CENTER,
                    CSCUser.group_pks.VOLUNTEER
                ],
            },
            exclude={
                "status": STUDENT_STATUS.expelled
            },
            semester=semester
        )

        # Prepare courses and student projects data
        courses_headers = OrderedDict()
        for s in students:
            student_courses = defaultdict(lambda: {'teachers': '', 'grade': ''})
            for e in s.enrollments:
                courses_headers[e.course_offering.course.id] = \
                    e.course_offering.course.name
                teachers = [t.get_full_name() for t
                            in e.course_offering.teachers.all()]
                student_courses[e.course_offering.course.id] = dict(
                    grade=e.grade_display.lower(),
                    teachers=", ".join(teachers)
                )
            s.courses = student_courses

        headers = [
            'Фамилия',
            'Имя',
            'Отчество',
            'Вольнослушатель',
            'ВУЗ',
            'Курс (на момент поступления)',
            'Год поступления',
            'Год выпуска',
            'Почта',
            'Яндекс ID',
            'Телефон',
            'Направления обучения',
            'Статус',
            'Дата статуса или итога (изменения)',
            'Комментарий',
            'Дата последнего изменения комментария',
            'Работа',
            'Сдано курсов (Центр/Клуб/ШАД)',
            'Ссылка на профиль',
        ]
        for course_id, course_name in six.iteritems(courses_headers):
            headers.append(course_name + ', оценка')
            headers.append(course_name + ', преподаватели')

        return self.get_response(headers,
                                 self.students_iter(students, courses_headers),
                                 semester)

    def students_iter(self, students, courses_headers):
        for s in students:
            row = [
                s.last_name,
                s.first_name,
                s.patronymic,
                "+" if s.is_volunteer else "",
                s.university,
                s.uni_year_at_enrollment,
                s.enrollment_year,
                s.graduation_year,
                s.email,
                s.yandex_id,
                s.phone,
                " и ".join((s.name for s in s.study_programs.all())),
                s.status_display,
                '',
                s.comment,
                s.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
                s.workplace,
                len(s.courses) + len(s.shads),
                self.request.build_absolute_uri(s.get_absolute_url())
            ]
            for course_id in courses_headers:
                sc = s.courses[course_id]
                row.extend([sc['grade'], sc['teachers']])

            yield row

    def get_response(self, headers, data, semester):
        raise NotImplemented("StudentSummaryBySemesterMixin: not implemented")



class StudentSummaryBySemesterCSVView(CuratorOnlyMixin,
                                      StudentSummaryBySemesterMixin,
                                      generic.base.View):
    http_method_names = ['get']

    def get_response(self, headers, data_iter, semester):
        output = io.BytesIO()
        w = unicodecsv.writer(output, encoding='utf-8')

        w.writerow(headers)
        for row in data_iter:
            w.writerow(row)

        output.seek(0)
        response = HttpResponse(output.read(),
                                content_type='text/csv; charset=utf-8')
        filename = "sheet_{}_{}.csv".format(semester.year, semester.type)
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response


class StudentSummaryBySemesterExcel2010View(CuratorOnlyMixin,
                                            StudentSummaryBySemesterMixin,
                                            generic.base.View):
    http_method_names = ['get']

    def get_response(self, headers, data_iter, semester):
        output = io.BytesIO()
        workbook = Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        bold = workbook.add_format({'bold': True})
        for index, header in enumerate(headers):
            worksheet.write(0, index, header, bold)

        for row_index, row in enumerate(data_iter, start=1):
            for col_index, value in enumerate(row):
                value = "" if value is None else force_unicode(value)
                worksheet.write(row_index, col_index, force_unicode(value))

        workbook.close()
        output.seek(0)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "sheet_{}_{}.xlsx".format(semester.year, semester.type)
        response = HttpResponse(output.read(), content_type=content_type)
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response







class TotalStatisticsView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        current_year, season = get_current_semester_pair()
        start_semester_index = get_semester_index(2011, Semester.TYPES.autumn)
        end_semester_index = get_semester_index(current_year, season)
        semesters = Semester.objects.filter(index__gte=start_semester_index, index__lte=end_semester_index)
        # Ok, additional query for counting acceptances due to no FK on enrollment_year field. Append it to autumn season
        query = (CSCUser.objects.exclude(enrollment_year__isnull=True)
                       .values("enrollment_year")
                       .annotate(acceptances=Count("enrollment_year"))
                       .order_by("enrollment_year"))
        acceptances = defaultdict(int)
        for row in query:
            acceptances[row["enrollment_year"]] = row["acceptances"]

        query = (CSCUser.objects.exclude(graduation_year__isnull=True)
                       .values("graduation_year")
                       .annotate(graduated=Count("graduation_year"))
                       .order_by("graduation_year"))
        graduated = defaultdict(int)
        for row in query:
            graduated[row["graduation_year"]] = row["graduated"]
        # TODO: graduated and acceptances in 1 query with Django ORM?

        # FIXME: Expressional conditions don't group by items?
        # Stats for expelled students
        query = (CSCUserStatusLog.objects.values("semester")
                 .annotate(expelled=Count("student", distinct=True))
                 .filter(status=STUDENT_STATUS.expelled)
                 .order_by("status"))
        expelled = defaultdict(int)
        for row in query:
            expelled[row["semester"]] = row["expelled"]
        # TODO: Investigate how to aggregate stats for expelled and will_graduate in 1 query

        # Stats for expelled students
        query = (CSCUserStatusLog.objects
                 .values("semester")
                 .annotate(will_graduate=Count("student", distinct=True))
                 .filter(status=STUDENT_STATUS.will_graduate)
                 .order_by("status"))
        will_graduate = defaultdict(int)
        for row in query:
            will_graduate[row["semester"]] = row["will_graduate"]

        statistics = OrderedDict()
        for semester in semesters:
            acceptances_cnt, graduated_cnt = 0, 0
            if semester.type == Semester.TYPES.autumn:
                acceptances_cnt = acceptances[semester.year]
            elif semester.type == Semester.TYPES.spring:
                graduated_cnt = graduated[semester.year]
            statistics[semester.pk] = {
                "semester": semester,
                "acceptances": acceptances_cnt,
                "graduated": graduated_cnt,
                "expelled": expelled[semester.pk],
                "will_graduate": will_graduate[semester.pk],
            }
        print(statistics)


        return HttpResponse("<html><body>body tag should be returned</body></html>", content_type='text/html; charset=utf-8')
