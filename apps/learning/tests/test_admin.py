import pytest

from core.admin import get_admin_url
from core.urls import reverse
from courses.tests.factories import AssignmentFactory, CourseFactory
from learning.models import (
    AssignmentScoreAuditLog, AssignmentStatuses, StudentAssignment
)
from learning.settings import AssignmentScoreUpdateSource
from learning.tests.factories import EnrollmentFactory
from users.tests.factories import CuratorFactory


def _student_assignment_form(assignment, enrollment, **overwrite):
    data = {
        "status": AssignmentStatuses.NEW,
        "assignment": assignment.pk,
        "student": enrollment.student_profile.user_id,
        "score": "",
        "StudentAssignment_watchers-TOTAL_FORMS": 0,
        "StudentAssignment_watchers-INITIAL_FORMS": 0,
        "score_history-TOTAL_FORMS": 0,
        "score_history-INITIAL_FORMS": 0
    }
    for key, value in overwrite.items():
        data[key] = value
    return data


@pytest.mark.django_db
def test_admin_student_assignment_score_audit_log(client):
    add_url = reverse('admin:learning_studentassignment_add')
    curator = CuratorFactory()
    client.login(curator)
    course = CourseFactory()
    assignment = AssignmentFactory(course=course, maximum_score=10)
    enrollment = EnrollmentFactory(course=course)
    StudentAssignment.objects.filter(assignment=assignment).delete()
    form_data = _student_assignment_form(assignment, enrollment)
    response = client.post(add_url, form_data)
    assert response.status_code == 302

    def get_student_assignment():
        return (StudentAssignment.objects
                .get(assignment=assignment,
                     student=enrollment.student_profile.user_id))

    student_assignment = get_student_assignment()
    # New record without score value
    assert AssignmentScoreAuditLog.objects.filter(student_assignment=student_assignment).count() == 0
    # New record with predefined score value
    StudentAssignment.objects.filter(assignment=assignment).delete()
    form_data = _student_assignment_form(assignment, enrollment, score=4)
    response = client.post(add_url, form_data)
    assert response.status_code == 302
    student_assignment = get_student_assignment()
    assert AssignmentScoreAuditLog.objects.filter(student_assignment=student_assignment).count() == 1
    log_record = AssignmentScoreAuditLog.objects.get(student_assignment=student_assignment)
    assert log_record.source == AssignmentScoreUpdateSource.FORM_ADMIN
    assert log_record.score_old is None
    assert log_record.score_new == 4
    assert log_record.changed_by == curator
    # Update existing record
    change_url = get_admin_url(student_assignment)
    form_data['score'] = 2
    response = client.post(change_url, form_data)
    assert response.status_code == 302
    assert AssignmentScoreAuditLog.objects.filter(student_assignment=student_assignment).count() == 2
    log_record = AssignmentScoreAuditLog.objects.filter(student_assignment=student_assignment).order_by('-pk').first()
    assert log_record.score_old == 4
    assert log_record.score_new == 2
    # Score has not changed
    response = client.post(change_url, form_data)
    assert response.status_code == 302
    assert AssignmentScoreAuditLog.objects.filter(student_assignment=student_assignment).count() == 2
