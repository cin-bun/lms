import os
import signal
import sys
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django_rq import get_scheduler
from redis.exceptions import ConnectionError

from apps.core.periodic_tasks import register_periodic_tasks


class Command(BaseCommand):
    help = "Runs Custom RQ scheduler for periodic tasks (cron)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--queue', '-q', dest='queue', default='default',
            help='Periodic tasks queue name'
        )
        parser.add_argument(
            '--interval', '-i', type=int, dest='interval', default=60,
            help='How often to check for scheduled tasks (in seconds)'
        )

    def handle(self, *args, **options):
        try:
            scheduler = get_scheduler(
                name=options.get('queue'),
                interval=options.get('interval')
            )

            self.register_scheduled_jobs(scheduler)

            self.stdout.write(
                self.style.SUCCESS("RQ Scheduler started for queue: %s" % options.get('queue'))
            )

            def signal_handler(signum, frame):
                self.stdout.write(self.style.WARNING("Stop signal received, shutting down..."))
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            scheduler.run()


        except ConnectionError as e:
            self.stdout.write(self.style.ERROR("Redis connection error: %s" % e))
            sys.exit(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Scheduler stopped."))
            sys.exit(0)

    def register_scheduled_jobs(self, scheduler):
        self.stdout.write("Registering periodic tasks...")

        try:
            register_periodic_tasks()

            jobs = list(scheduler.get_jobs())
            if jobs:
                self.stdout.write(
                    self.style.SUCCESS(f"Registered {len(jobs)} periodic tasks")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("No periodic tasks registered")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error registering periodic tasks: {e}")
            )
