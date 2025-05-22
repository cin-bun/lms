from django_rq import job

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from logging import getLogger

logger = getLogger(__name__)

@job('default')
def compute_model_fields(content_type_id, object_id, compute_fields):
    from core.db.mixins import DerivableFieldsMixin

    content_type = ContentType.objects.get_for_id(content_type_id)
    model = content_type.model_class()

    if model is None:
        return

    if issubclass(model, DerivableFieldsMixin):
        queryset = model._base_manager  # type: ignore

        prefetch_fields = model.prefetch_before_compute(*compute_fields)
        if prefetch_fields:
            queryset = queryset.prefetch_related(*prefetch_fields)

        obj = queryset.get(id=object_id)
        obj.compute_fields(*compute_fields)


@job('default')
def clear_sessions():
    call_command('clearsessions')


@job('default')
def course_notifications():
    call_command('notify')


@job('default')
def clear_notifications():
    call_command('notification_cleanup')


@job('default')
def send_queued_mail():
    call_command('send_queued_mail')


@job('default')
def project_notifications():
    call_command('projects_notifications')


@job('default')
def send_project_notifications():
    call_command('send_notifications')
