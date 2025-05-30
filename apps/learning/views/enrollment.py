from typing import Any

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.generic import FormView
from django.conf import settings
from django.contrib.sites.models import Site

from auth.mixins import PermissionRequiredMixin
from core.exceptions import Redirect
from core.http import HttpRequest
from core.urls import reverse
from courses.views.mixins import CourseURLParamsMixin
from learning.forms import CourseEnrollmentForm
from learning.models import CourseInvitation, Enrollment
from learning.permissions import (
    EnrollInCourse, EnrollInCourseByInvitation, EnrollPermissionObject,
    InvitationEnrollPermissionObject
)
from learning.services import EnrollmentService
from learning.services.enrollment_service import AlreadyEnrolled, CourseCapacityFull
from learning.services.student_group_service import (
    StudentGroupError, StudentGroupService
)
from learning.settings import EnrollmentTypes, InvitationEnrollmentTypes


class CourseEnrollView(CourseURLParamsMixin, PermissionRequiredMixin, FormView):
    form_class = CourseEnrollmentForm
    template_name = "learning/enrollment/enrollment_enter.html"
    permission_required = EnrollInCourse.name

    def get_permission_object(self):
        site = Site.objects.get(pk=settings.SITE_ID)
        student_profile = self.request.user.get_student_profile(site)
        return EnrollPermissionObject(self.course, student_profile)

    def has_permission(self):
        has_perm = super().has_permission()
        # FIXME: remove?
        if not has_perm and not self.course.places_left:
            msg = _("No places available, sorry")
            messages.error(self.request, msg, extra_tags='timeout')
            raise Redirect(to=self.course.get_absolute_url())
        return has_perm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ask_enrollment_reason'] = self.course.ask_enrollment_reason
        if self.course.enrollment_type == InvitationEnrollmentTypes.ANY:
            if self.course.is_learners_capacity_limited and not self.course.learners_places_left:
                kwargs['enrollment_type'] = EnrollmentTypes.LECTIONS_ONLY
            elif self.course.is_listeners_capacity_limited and not self.course.listeners_places_left:
                kwargs['enrollment_type'] = EnrollmentTypes.REGULAR
            else:
                kwargs['enrollment_type'] = InvitationEnrollmentTypes.ANY
        else:
            kwargs['enrollment_type'] = self.course.enrollment_type
        return kwargs

    def form_valid(self, form):
        reason_entry = form.cleaned_data.get("reason", "").strip()
        type = form.cleaned_data["type"].strip()
        user = self.request.user
        student_profile = user.get_student_profile(Site.objects.get(pk=settings.SITE_ID))
        try:
            student_group = StudentGroupService.resolve(self.course,
                                                        student_profile=student_profile)
        except StudentGroupError as e:
            messages.error(self.request, str(e), extra_tags='timeout')
            raise Redirect(to=self.course.get_absolute_url())
        try:
            EnrollmentService.enroll(student_profile, self.course,
                                     reason_entry=reason_entry,
                                     type=type,
                                     student_group=student_group)
            msg = _("You are successfully enrolled in the course")
            messages.success(self.request, msg, extra_tags='timeout')
        except AlreadyEnrolled:
            msg = _("You are already enrolled in the course")
            messages.warning(self.request, msg, extra_tags='timeout')
        except CourseCapacityFull:
            msg = _("No places available, sorry")
            messages.error(self.request, msg, extra_tags='timeout')
            raise Redirect(to=self.course.get_absolute_url())
        if self.request.POST.get('back') == 'study:course_list':
            return_to = reverse('study:course_list')
        else:
            return_to = self.course.get_absolute_url()
        return HttpResponseRedirect(return_to)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        return context


class CourseUnenrollView(PermissionRequiredMixin, CourseURLParamsMixin,
                         generic.DeleteView):
    template_name = "learning/enrollment/enrollment_leave.html"
    context_object_name = "enrollment"
    permission_required = 'learning.leave_course'

    def get_permission_object(self):
        return self.course

    def delete(self, request, *args, **kwargs):
        enrollment = self.get_object()
        reason_leave = request.POST.get("reason", "").strip()
        EnrollmentService.leave(enrollment, reason_leave=reason_leave)
        if self.request.GET.get('back') == 'study:course_list':
            redirect_to = reverse('study:course_list')
        else:
            redirect_to = enrollment.course.get_absolute_url()
        return HttpResponseRedirect(redirect_to)

    def get_object(self, queryset=None):
        enrollment = get_object_or_404(
            Enrollment.active
            .filter(student=self.request.user, course_id=self.course.pk)
            .select_related("course", "course__semester"))
        return enrollment


class CourseInvitationEnrollView(PermissionRequiredMixin,
                                 CourseURLParamsMixin, FormView):
    form_class = CourseEnrollmentForm
    template_name = "learning/enrollment/enrollment_enter.html"
    course_invitation: CourseInvitation
    permission_required = EnrollInCourseByInvitation.name

    def get_permission_object(self):
        site = Site.objects.get(pk=settings.SITE_ID)
        student_profile = self.request.user.get_student_profile(site)
        return InvitationEnrollPermissionObject(self.course_invitation,
                                                student_profile)

    def has_permission(self) -> bool:
        has_perm = super().has_permission()
        if not has_perm and not self.course_invitation.places_left:
            msg = _("No places available, sorry")
            messages.error(self.request, msg, extra_tags='timeout')
            invitation = self.course_invitation.invitation
            raise Redirect(to=invitation.get_absolute_url())
        return has_perm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['enrollment_type'] = self.course_invitation.enrollment_type
        kwargs['ask_enrollment_reason'] = self.course.ask_enrollment_reason
        return kwargs


    def setup(self, request: HttpRequest, **kwargs: Any) -> None:
        super().setup(request, **kwargs)
        qs = (CourseInvitation.objects
              .select_related('invitation')
              .filter(token=kwargs['course_token'],
                      course=self.course))
        self.course_invitation = get_object_or_404(qs)


    def form_valid(self, form):
        reason_entry = form.cleaned_data.get("reason", "").strip()
        type = form.cleaned_data["type"].strip()
        invitation = self.course_invitation.invitation
        user = self.request.user
        student_profile = user.get_student_profile(Site.objects.get(pk=settings.SITE_ID))
        try:
            resolved_group = StudentGroupService.resolve(self.course,
                                                         student_profile=student_profile,
                                                         invitation=invitation)
        except StudentGroupError as e:
            messages.error(self.request, str(e), extra_tags='timeout')
            raise Redirect(to=self.course.get_absolute_url())
        try:
            EnrollmentService.enroll(student_profile, self.course,
                                     reason_entry=reason_entry,
                                     type=type,
                                     invitation=invitation,
                                     student_group=resolved_group)
            self.course_invitation.enrolled_students.add(student_profile)
            msg = _("You are successfully enrolled in the course")
            messages.success(self.request, msg, extra_tags='timeout')
            redirect_to = self.course.get_absolute_url()
        except AlreadyEnrolled:
            msg = _("You are already enrolled in the course")
            messages.warning(self.request, msg, extra_tags='timeout')
            redirect_to = self.course.get_absolute_url()
        except CourseCapacityFull:
            msg = _("No places available, sorry")
            messages.error(self.request, msg, extra_tags='timeout')
            redirect_to = invitation.get_absolute_url()
        return HttpResponseRedirect(redirect_to)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        return context
