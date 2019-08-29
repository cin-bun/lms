from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Count, Case, When, Q, Value, F
from django.forms import SelectMultiple, forms
from django_filters import MultipleChoiceFilter
from django_filters.constants import EMPTY_VALUES
from django_filters.fields import MultipleChoiceField
from django_filters.rest_framework import BaseInFilter, NumberFilter, \
    FilterSet, CharFilter

from learning.settings import StudentStatuses, GradeTypes
from users.constants import Roles
from users.models import User


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class SelectMultipleCSVSupport(SelectMultiple):
    """
    1. Values can be provided as csv string:  ?foo=bar,baz
    2. Values can be provided as query array: ?foo=bar&foo=baz

    Note: Duplicate and empty values are skipped from results
    """

    def value_from_datadict(self, data, files, name):
        value = super().value_from_datadict(data, files, name)
        if isinstance(value, str):
            ret = {x.strip() for x in value.rstrip(',').split(',') if x}
        elif value is not None and len(value) > 0:
            ret = set()
            for csv in value:
                ret.update({x.strip() for x in
                           csv.rstrip(',').split(',') if x})
        else:
            ret = []
        return list(ret)


class MultipleChoiceCSVField(MultipleChoiceField):
    widget = SelectMultipleCSVSupport


class RolesInFilter(MultipleChoiceFilter):
    field_class = MultipleChoiceCSVField

    choices = [
        (Roles.STUDENT, Roles.values[Roles.STUDENT]),
        (Roles.VOLUNTEER, Roles.values[Roles.VOLUNTEER]),
        (Roles.INVITED, Roles.values[Roles.INVITED]),
        (Roles.GRADUATE, Roles.values[Roles.GRADUATE]),
        (Roles.MASTERS_DEGREE, Roles.values[Roles.MASTERS_DEGREE]),
    ]

    def __init__(self, choices=None, *args, **kwargs):
        if choices is not None:
            self.choices = choices
        super().__init__(choices=self.choices, *args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        return (qs
                .filter(group__site_id=settings.SITE_ID,
                        group__role__in=value)
                .distinct())


class UserFilterForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        if ("studying" in cleaned_data["status"] and
                cleaned_data['groups'] == [str(Roles.GRADUATE)]):
            raise ValidationError("Graduates are not studying")
        if "groups" not in self.changed_data and len(self.changed_data):
            groups = [v for v, _ in RolesInFilter.choices]
            if "studying" in cleaned_data["status"]:
                groups.remove(Roles.GRADUATE)
            cleaned_data['groups'] = groups


class UserFilter(FilterSet):
    ENROLLMENTS_MAX = 12

    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

    name = CharFilter(method='name_filter')
    branches = CharInFilter(field_name='branch_id')
    curriculum_year = NumberInFilter(field_name='curriculum_year')
    groups = RolesInFilter(label='Roles', field_name='group__role',
                           distinct=True)
    # FIXME: choice validation
    status = CharFilter(label='Student Status', method='status_filter')
    cnt_enrollments = CharFilter(label='Enrollments',
                                 method='cnt_enrollments_filter')

    class Meta:
        form = UserFilterForm
        model = User
        fields = ("name", "branches", "curriculum_year", "groups", "status",
                  "cnt_enrollments",)

    @property
    def qs(self):
        if not self.form.changed_data:
            return self.queryset.none()
        return super().qs

    def cnt_enrollments_filter(self, queryset, name, value):
        value_list = value.split(u',')
        try:
            value_list = [int(v) for v in value_list if v]
            if not value_list:
                return queryset
        except ValueError:
            return queryset

        queryset = queryset.annotate(
            courses_cnt=
            # Remove unsuccessful grades, then distinctly count by pk
            Count(Case(
                When(Q(enrollment__grade=GradeTypes.NOT_GRADED) |
                     Q(enrollment__grade=GradeTypes.UNSATISFACTORY),
                     then=Value(None)),
                default=F("enrollment__course__meta_course_id")
            ), distinct=True) +
            Count(Case(
                When(Q(shadcourserecord__grade=GradeTypes.NOT_GRADED) |
                     Q(shadcourserecord__grade=GradeTypes.UNSATISFACTORY),
                     then=Value(None)),
                default=F("shadcourserecord")
            ), distinct=True) +
            # No need to filter online courses by grade
            Count("onlinecourserecord", distinct=True)
        )
        condition = Q(courses_cnt__in=value_list)
        if any(value > self.ENROLLMENTS_MAX for value in value_list):
            condition |= Q(courses_cnt__gt=self.ENROLLMENTS_MAX)

        return queryset.filter(condition)

    def status_filter(self, queryset, name, value):
        value_list = value.split(u',')
        value_list = [v for v in value_list if v]
        if "studying" in value_list and StudentStatuses.EXPELLED in value_list:
            return queryset
        elif "studying" in value_list:
            return queryset.exclude(status=StudentStatuses.EXPELLED)
        for value in value_list:
            if value not in StudentStatuses.values:
                raise ValueError(
                    "UserFilter: unrecognized status_filter choice")
        return queryset.filter(status__in=value_list).distinct()

    # FIXME: Can I rewrite it with new __search lookup expr?
    def name_filter(self, queryset, name, value):
        qstr = value.strip()
        tsquery = self._form_name_tsquery(qstr)
        if tsquery is None:
            return queryset
        else:
            qs = (queryset
                    .extra(where=["to_tsvector(first_name || ' ' || last_name) "
                                  "@@ to_tsquery(%s)"],
                           params=[tsquery])
                    .exclude(first_name__exact='',
                             last_name__exact=''))
            return qs

    def _form_name_tsquery(self, qstr):
        if qstr is None or not (2 <= len(qstr) < 100):
            return
        lexems = []
        for s in qstr.split(' '):
            lexeme = s.translate(self._lexeme_trans_map).strip()
            if len(lexeme) > 0:
                lexems.append(lexeme)
        if len(lexems) > 3:
            return
        return " & ".join("{}:*".format(l) for l in lexems)
