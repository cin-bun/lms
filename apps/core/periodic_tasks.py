from typing import Any, Dict, List, Optional

import django_rq
from django_rq.queues import get_queue
from apps.core.tasks import send_project_notifications, clear_sessions, course_notifications, clear_notifications, \
    send_queued_mail, project_notifications


def register_periodic_tasks():
    scheduler = django_rq.get_scheduler('default')

    jobs = list(scheduler.get_jobs())
    for job in jobs:
        scheduler.cancel(job)

    _register_clear_sessions(scheduler)
    _register_course_notifications(scheduler)
    _register_clear_notifications(scheduler)
    _register_send_queued_mail(scheduler)
    _register_project_notifications(scheduler)
    _register_send_project_notifications(scheduler)

def _register_clear_sessions(scheduler):
    scheduler.cron(
        "7 0 * * *",  # каждый день в 00:07
        func=clear_sessions,
        args=[],
        kwargs={},
        repeat=None,
        meta = {'description': 'Clear outdated user sessions (daily at 00:07)'}
    )


def _register_course_notifications(scheduler):
    scheduler.cron(
        "*/5 * * * *",  # каждые 5 минут
        func=course_notifications,
        args=[],
        kwargs={},
        repeat=None,
        meta={'description': 'Send course notifications (every 5 minutes)'}
    )


def _register_clear_notifications(scheduler):
    scheduler.cron(
        "0 4 1 * *",  # в 4:00 первого числа каждого месяца
        func=clear_notifications,
        args=[],
        kwargs={},
        repeat=None,
        meta={'description': 'Clear old notifications (at 4:00 on the first day of each month)'}
    )


def _register_send_queued_mail(scheduler):
    scheduler.cron(
        "* * * * *",  # каждую минуту
        func=send_queued_mail,
        args=[],
        kwargs={},
        repeat=None,
        meta={'description': 'Send mail from the queue (every minute)'}
    )


def _register_project_notifications(scheduler):
    scheduler.cron(
        "7 1,13 * * *",  # каждый день в 01:07 и 13:07
        func=project_notifications,
        args=[],
        kwargs={},
        repeat=None,
        meta={'description': 'Create notifications about projects (daily at 01:07 and 13:07)'}
    )


def _register_send_project_notifications(scheduler):
    scheduler.cron(
        "*/5 * * * *",  # каждые 5 минут
        func=send_project_notifications,
        args=[],
        kwargs={},
        repeat=None,
        meta={'description': 'Send notifications about projects (every 5 minutes)'}
    )
