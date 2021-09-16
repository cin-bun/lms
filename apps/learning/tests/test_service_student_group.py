import pytest

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.tests.factories import BranchFactory, SiteFactory
from core.tests.settings import ANOTHER_DOMAIN, ANOTHER_DOMAIN_ID, TEST_DOMAIN
from courses.models import CourseBranch, CourseGroupModes, StudentGroupTypes
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from learning.models import StudentGroup, StudentGroupAssignee
from learning.services import (
    EnrollmentService, GroupEnrollmentKeyError, StudentGroupError, StudentGroupService
)
from learning.tests.factories import (
    EnrollmentFactory, StudentGroupAssigneeFactory, StudentGroupFactory
)
from users.tests.factories import StudentFactory


@pytest.mark.django_db
def test_student_group_service_create_no_groups_mode(settings):
    course = CourseFactory(group_mode=CourseGroupModes.NO_GROUPS)
    with pytest.raises(StudentGroupError) as e:
        StudentGroupService.create(course, branch=course.main_branch)


@pytest.mark.django_db
def test_student_group_service_create_with_branch_mode(settings):
    branch1, branch2 = BranchFactory.create_batch(2)
    course = CourseFactory(main_branch=branch1,
                           group_mode=CourseGroupModes.BRANCH)
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course)
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course, branch=branch2)
    assert e.value.code == 'malformed'
    student_group1 = StudentGroupService.create(course, branch=branch1)
    assert list(StudentGroup.objects.all()) == [student_group1]
    StudentGroupService.create(course, branch=branch1)  # repeat
    assert StudentGroup.objects.count() == 1


@pytest.mark.django_db
def test_student_group_service_create_manual_group(settings):
    course1, course2 = CourseFactory.create_batch(2, group_mode=CourseGroupModes.MANUAL)
    # Empty group name
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course1)
    assert e.value.code == 'required'
    student_group = StudentGroupService.create(course1, name='test')
    assert list(StudentGroup.objects.all()) == [student_group]
    # Non unique student group name for the course
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course1, name='test')
    StudentGroupService.create(course2, name='test')


@pytest.mark.django_db
def test_student_group_service_resolve(settings):
    branch_spb = BranchFactory(code="spb")
    branch_nsk = BranchFactory(code="nsk")
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH)
    assert StudentGroup.objects.filter(course=course).count() == 1
    student_group = StudentGroup.objects.get(course=course)
    sg_other = StudentGroupFactory(course=course)
    student_spb = StudentFactory(branch=branch_spb)
    student_nsk = StudentFactory(branch=branch_nsk)
    assert StudentGroupService.resolve(course, student_spb, settings.SITE_ID) == student_group
    assert StudentGroupService.resolve(course, student_spb, settings.SITE_ID,
                                       enrollment_key='wrong_key') == student_group
    found = StudentGroupService.resolve(
        course, student_spb, settings.SITE_ID,
        enrollment_key=sg_other.enrollment_key)
    assert found == student_group
    student_group = StudentGroupService.resolve(course, student_nsk, settings.SITE_ID)
    assert student_group.type == StudentGroupTypes.SYSTEM
    course.group_mode = CourseGroupModes.MANUAL
    assert StudentGroupService.resolve(
        course, student_spb, settings.SITE_ID,
        enrollment_key=sg_other.enrollment_key) == sg_other
    with pytest.raises(GroupEnrollmentKeyError):
        StudentGroupService.resolve(course, student_spb, settings.SITE_ID, enrollment_key='wrong')
    student_group = StudentGroupService.resolve(course, student_spb, settings.SITE_ID, enrollment_key=None)
    assert student_group.type == StudentGroupTypes.SYSTEM
    course.group_mode = 'unknown'
    with pytest.raises(GroupEnrollmentKeyError):
        StudentGroupService.resolve(course, student_spb, settings.SITE_ID, enrollment_key='wrong')


@pytest.mark.django_db
def test_student_group_service_get_choices(settings):
    branch_spb = BranchFactory(code="spb")
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH)
    assert StudentGroup.objects.filter(course=course).count() == 1
    groups = list(StudentGroup.objects.filter(course=course).order_by('pk'))
    choices = StudentGroupService.get_choices(course)
    assert len(choices) == 1
    assert choices[0] == (str(groups[0].pk), groups[0].name)
    branch_nsk = BranchFactory(code="nsk",
                               site=SiteFactory(domain=ANOTHER_DOMAIN))
    assert branch_nsk.site_id == ANOTHER_DOMAIN_ID
    CourseBranch(course=course, branch=branch_nsk).save()
    assert StudentGroup.objects.filter(course=course).count() == 2
    sg1, sg2 = list(StudentGroup.objects.filter(course=course).order_by('pk'))
    choices = StudentGroupService.get_choices(course)
    assert choices[0] == (str(sg1.pk), f"{sg1.name} [{TEST_DOMAIN}]")
    assert choices[1] == (str(sg2.pk), f"{sg2.name} [{ANOTHER_DOMAIN}]")


@pytest.mark.django_db
def test_student_group_service_get_student_profiles():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)
    enrollments = EnrollmentFactory.create_batch(3, course=course, student_group=student_group1)
    enrollment1, enrollment2, enrollment3 = enrollments
    student_profiles = StudentGroupService.get_student_profiles(student_group2)
    assert len(student_profiles) == 0
    EnrollmentFactory(course=course, student_group=student_group2)
    student_profiles = StudentGroupService.get_student_profiles(student_group1)
    assert len(student_profiles) == 3
    EnrollmentService.leave(enrollment1, reason_leave='cause')
    student_profiles = StudentGroupService.get_student_profiles(student_group1)
    assert len(student_profiles) == 2


@pytest.mark.django_db
def test_student_group_service_get_groups_available_for_student_transfer():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2, student_group3 = StudentGroupFactory.create_batch(3, course=course)
    student_group4 = StudentGroupFactory(course__group_mode=StudentGroupTypes.MANUAL)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 2
    assert student_group2 in student_groups
    assert student_group3 in student_groups
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group4)
    assert len(student_groups) == 0
    assignment1, assignment2 = AssignmentFactory.create_batch(2, course=course)
    assignment1.restricted_to.add(student_group2, student_group3)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 0
    assignment1.restricted_to.add(student_group1)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 2
    assert student_group2 in student_groups
    assert student_group3 in student_groups
    assignment2.restricted_to.add(student_group2)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 1
    assert student_group3 in student_groups
    assignment2.restricted_to.add(student_group1)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 1
    assert student_group2 in student_groups


@pytest.mark.django_db
def test_student_group_add_assignees(settings):
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1 = StudentGroupFactory(course=course)
    student_group2 = StudentGroupFactory()
    course_teacher1, course_teacher2 = CourseTeacherFactory.create_batch(2, course=course)
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assigned = StudentGroupAssignee.objects.get()
    assert assigned.assignee_id == course_teacher1.pk
    # Student group does not match course of the course teacher
    with pytest.raises(ValidationError):
        StudentGroupService.add_assignees(student_group2, teachers=[course_teacher1])
    # Can't add the same course teacher twice
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assignment = AssignmentFactory(course=course)
    # Customize list of responsible teachers for the assignment
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)
    assert StudentGroupAssignee.objects.count() == 2
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)


@pytest.mark.django_db
def test_student_group_update_assignees(settings):
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1 = StudentGroupFactory(course=course)
    course_teacher1, course_teacher2, course_teacher3 = CourseTeacherFactory.create_batch(3, course=course)
    student_group2 = StudentGroupFactory()
    course_teacher2_1 = CourseTeacherFactory(course=student_group2.course)
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assigned = StudentGroupAssignee.objects.get()
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assert StudentGroupAssignee.objects.get() == assigned
    StudentGroupService.update_assignees(student_group2, teachers=[course_teacher2_1])
    assert StudentGroupAssignee.objects.count() == 2
    assert assigned in StudentGroupAssignee.objects.all()
    # Add the second course teacher and try to update list of responsible
    # teachers again
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher2])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 1
    assert StudentGroupAssignee.objects.count() == 2
    # Assign responsible teachers for the assignment
    assignment = AssignmentFactory(course=course)
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher2], assignment=assignment)
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    assert StudentGroupService.get_assignees(student_group1) == [course_teacher1]
    assert StudentGroupService.get_assignees(student_group1, assignment=assignment) == [course_teacher2]
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)
    assert StudentGroupService.get_assignees(student_group1, assignment=assignment) == [course_teacher1]
    # Reset list of teachers
    StudentGroupService.update_assignees(student_group1, teachers=[], assignment=assignment)
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 1
    assert StudentGroupAssignee.objects.filter(student_group=student_group1, assignment=assignment).count() == 0
    assert assigned in StudentGroupAssignee.objects.filter(student_group=student_group1).all()
    # Add and delete at the same time
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher3])
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1, course_teacher2])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    assigned_teachers = [sga.assignee for sga in StudentGroupAssignee.objects.filter(student_group=student_group1)]
    assert course_teacher1 in assigned_teachers
    assert course_teacher2 in assigned_teachers
    assert StudentGroupAssignee.objects.filter(student_group=student_group2).count() == 1


@pytest.mark.django_db
def test_student_group_get_assignees():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    assignment1 = AssignmentFactory(course=course)
    assignment2 = AssignmentFactory(course=course)
    assert StudentGroup.objects.filter(course=course).count() == 0
    student_group1 = StudentGroupFactory(course=course)
    student_group2 = StudentGroupFactory(course=course)
    sga1 = StudentGroupAssigneeFactory(student_group=student_group1)
    sga2 = StudentGroupAssigneeFactory(student_group=student_group1)
    sga3 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment1)
    sga4 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment1)
    sga5 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment2)
    assert StudentGroupService.get_assignees(student_group2) == []
    assignees = StudentGroupService.get_assignees(student_group1)
    assert len(assignees) == 2
    assert sga1.assignee in assignees
    assert sga2.assignee in assignees
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment1)
    assert len(assignees) == 2
    assert sga3.assignee in assignees
    assert sga4.assignee in assignees
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga5.assignee == assignees[0]
    sga6 = StudentGroupAssigneeFactory(student_group=student_group2,
                                       assignment=assignment2)
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga5.assignee == assignees[0]
    assignees = StudentGroupService.get_assignees(student_group2,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga6.assignee == assignees[0]
