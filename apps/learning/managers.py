from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import Q, query
from django.utils import timezone

from core.db.models import LiveManager
from django.db.models import OuterRef, Exists
from core.utils import is_club_site
from courses.constants import AssignmentStatus
from learning.settings import EnrollmentTypes, GradeTypes


class StudentAssignmentQuerySet(query.QuerySet):
    def for_student(self, user):
        return (self.filter(student=user)
                .select_related('assignment',
                                'assignment__course',
                                'assignment__course__main_branch',
                                'assignment__course__meta_course',
                                'assignment__course__semester'))

    def in_term(self, term):
        return self.filter(assignment__course__semester_id=term.id)

    def with_future_deadline(self):
        """
        Returns individual assignments with unexpired deadlines.
        """
        return self.filter(assignment__deadline_at__gt=timezone.now())

    def can_be_submitted(self):
        # Have to do so to avoid cercular import:
        # learning.managers (this) -> learning.models(with Enrollment) -> learning.managers (with AssignmentCommentPublishedManager)
        Enrollment = apps.get_model('learning', 'Enrollment')
        enrollment_subquery = Enrollment.active.can_submit_assignments().filter(
                            student=OuterRef('student'),
                            course=OuterRef('assignment__course')
                            )
        return self.filter(Exists(enrollment_subquery))

    def for_teachers(self):
        Enrollment = apps.get_model('learning', 'Enrollment')
        enrollment_subquery = Enrollment.active.can_submit_assignments().filter(
                            student=OuterRef('student'),
                            course=OuterRef('assignment__course')
                            )
        return self.filter(Q(Exists(enrollment_subquery)) | Q(status__in=[AssignmentStatus.NEED_FIXES, AssignmentStatus.COMPLETED]))


class _StudentAssignmentDefaultManager(LiveManager):
    """On compsciclub.ru always restrict by open readings"""
    def get_queryset(self):
        qs = super().get_queryset()
        if is_club_site():
            return qs.filter(assignment__course__main_branch__site_id=settings.CLUB_SITE_ID)
        return qs


StudentAssignmentManager = _StudentAssignmentDefaultManager.from_queryset(
    StudentAssignmentQuerySet)


class EventQuerySet(query.QuerySet):
    pass


class _EnrollmentDefaultManager(models.Manager):
    """On compsciclub.ru always restrict selection by open readings"""
    def get_queryset(self):
        if is_club_site():
            return (super().get_queryset()
                    .filter(course__main_branch__site_id=settings.CLUB_SITE_ID))
        else:
            return super().get_queryset()


class _EnrollmentActiveManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        if is_club_site():
            qs = qs.filter(course__main_branch__site_id=settings.CLUB_SITE_ID)
        return qs


class EnrollmentQuerySet(models.QuerySet):
    
    def can_submit_assignments(self):
        return self.filter(
                    grade__ne=GradeTypes.RE_CREDIT,
                    is_grade_recredited=False,
                    type__ne=EnrollmentTypes.LECTIONS_ONLY
                    )


EnrollmentDefaultManager = _EnrollmentDefaultManager.from_queryset(
    EnrollmentQuerySet)
EnrollmentActiveManager = _EnrollmentActiveManager.from_queryset(
    EnrollmentQuerySet)


class _GraduateProfileActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class GraduateProfileQuerySet(models.QuerySet):
    def for_site(self, site):
        return self.filter(student_profile__branch__site=site)

    def with_official_diploma(self):
        return self.exclude(diploma_issued_on__isnull=True)

    def with_testimonial(self):
        return self.exclude(testimonial='')

    def get_only_required_fields(self):
        return (self.select_related("student_profile",
                                    "student_profile__branch",
                                    "student_profile__user", )
                .only("pk",
                      "student_profile_id",
                      "modified",
                      "graduation_year",
                      "photo",
                      "testimonial",
                      "student_profile__user_id",
                      "student_profile__branch__code",
                      "student_profile__branch__name_ru",
                      "student_profile__branch__name_en",
                      "student_profile__branch__order",
                      "student_profile__user__photo",
                      "student_profile__user__cropbox_data",
                      "student_profile__user__first_name",
                      "student_profile__user__last_name",
                      "student_profile__user__patronymic",
                      "student_profile__user__gender", ))


GraduateProfileDefaultManager = models.Manager.from_queryset(GraduateProfileQuerySet)
GraduateProfileActiveManager = _GraduateProfileActiveManager.from_queryset(
    GraduateProfileQuerySet)


class AssignmentCommentQuerySet(models.QuerySet):
    pass


class _AssignmentCommentPublishedManager(LiveManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


AssignmentCommentPublishedManager = _AssignmentCommentPublishedManager.from_queryset(
    AssignmentCommentQuerySet)
