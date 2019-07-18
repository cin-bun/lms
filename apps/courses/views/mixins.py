import logging
from typing import Dict

from django.http import HttpResponseBadRequest

from courses.models import Course
from courses.utils import semester_slug_re


logger = logging.getLogger(__name__)


class CourseURLParamsMixin:
    """
    Validates URL params from the `courses.urls.RE_COURSE_URI`.
    Provides a basic queryset for the course.
    """
    def setup(self, request, *args, **kwargs):
        if not kwargs['city_aware']:
            logger.warning("For this view `request.city_code` should be "
                           "populated from the GET-parameters")
            return HttpResponseBadRequest()
        super().setup(request, *args, **kwargs)

    def get_course_queryset(self):
        """Returns queryset for the course based on view kwargs"""
        return (Course.objects
                .in_city(self.request.city_code)
                .filter(semester__type=self.kwargs['semester_type'],
                        semester__year=self.kwargs['semester_year'],
                        meta_course__slug=self.kwargs['course_slug']))
