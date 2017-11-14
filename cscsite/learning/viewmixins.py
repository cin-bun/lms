from braces.views import UserPassesTestMixin

from learning.settings import STUDENT_STATUS


class ParticipantOnlyMixin(UserPassesTestMixin):
    """Used on assignment detail page"""
    raise_exception = False

    def test_func(self, user):
        return (user.is_teacher or user.is_curator or user.is_graduate or
                user.is_student)


class TeacherOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_teacher or user.is_curator


class InterviewerOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_interviewer or user.is_curator


class ProjectReviewerGroupOnlyMixin(UserPassesTestMixin):
    """Curator must have this group"""
    raise_exception = False

    def test_func(self, user):
        return user.is_project_reviewer or user.is_curator


class StudentOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_active_student or user.is_curator


class StudentCenterAndVolunteerOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        is_active_student = ((user.is_student_center or user.is_volunteer) and
                             user.status != STUDENT_STATUS.expelled)
        return is_active_student or user.is_curator


class CuratorOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_curator
