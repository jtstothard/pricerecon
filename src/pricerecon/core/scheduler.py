"""APScheduler-based watch scheduler with timezone and time-window support."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobEvent

from pricerecon.core.schedule import ParsedSchedule, ScheduleParseError

logger = logging.getLogger(__name__)


class WatchScheduler:
    """Scheduler for running watches at configured intervals.

    Uses APScheduler's AsyncIOScheduler with timezone-aware interval triggers.
    Supports time-window filtering to skip executions outside configured windows.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self._watch_jobs: dict[int, str] = {}  # watch_id -> job_id mapping
        self._watch_check_fn: Optional[Callable] = None

    def set_watch_check_function(self, fn: Callable) -> None:
        """Set the function to call when a watch check is triggered.

        Args:
            fn: Async function that takes watch_id and performs the check
        """
        self._watch_check_fn = fn

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            logger.info("Starting watch scheduler")
            self.scheduler.start()
            # Log scheduler events for debugging
            self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if self.scheduler.running:
            logger.info("Stopping watch scheduler")
            self.scheduler.shutdown(wait=False)

    def add_watch(
        self,
        watch_id: int,
        interval: str,
        timezone: str = "UTC",
        time_window: Optional[dict] = None,
    ) -> str:
        """Add a watch to the scheduler.

        Args:
            watch_id: Database ID of the watch
            interval: Interval string (e.g., "4h", "30m", "1d")
            timezone: Timezone string (e.g., "Europe/London", "UTC")
            time_window: Optional time window dict (start, end, days)

        Returns:
            APScheduler job ID

        Raises:
            ScheduleParseError: If schedule configuration is invalid
        """
        # Parse schedule
        try:
            schedule = ParsedSchedule.parse(interval, timezone, time_window)
        except ScheduleParseError as e:
            logger.error(f"Failed to parse schedule for watch {watch_id}: {e}")
            raise

        # Create job ID
        job_id = f"watch_{watch_id}"

        # Remove existing job if present
        if watch_id in self._watch_jobs:
            self.remove_watch(watch_id)

        # Add job to scheduler
        import datetime as _dt

        now = _dt.datetime.now(_dt.timezone.utc)
        self.scheduler.add_job(
            func=self._execute_watch,
            trigger=IntervalTrigger(
                seconds=schedule.interval_seconds,
                timezone=schedule.timezone,
                start_date=now,
            ),
            id=job_id,
            args=[watch_id, schedule],
            name=f"Watch {watch_id}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )

        # Fire the first run immediately in a background task
        asyncio.create_task(self._execute_watch(watch_id, schedule))

        self._watch_jobs[watch_id] = job_id
        logger.info(
            f"Added watch {watch_id} to scheduler: "
            f"interval={interval}, timezone={timezone}, "
            f"time_window={'enabled' if schedule.time_window else 'disabled'}"
        )

        return job_id

    def remove_watch(self, watch_id: int) -> None:
        """Remove a watch from the scheduler.

        Args:
            watch_id: Database ID of the watch
        """
        if watch_id not in self._watch_jobs:
            logger.warning(f"Watch {watch_id} not in scheduler")
            return

        job_id = self._watch_jobs[watch_id]
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed watch {watch_id} from scheduler")
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
        finally:
            del self._watch_jobs[watch_id]

    def pause_watch(self, watch_id: int) -> None:
        """Pause a watch job (keeps it registered but doesn't execute).

        Args:
            watch_id: Database ID of the watch
        """
        if watch_id not in self._watch_jobs:
            logger.warning(f"Watch {watch_id} not in scheduler")
            return

        job_id = self._watch_jobs[watch_id]
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused watch {watch_id}")
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")

    def resume_watch(self, watch_id: int) -> None:
        """Resume a paused watch job.

        Args:
            watch_id: Database ID of the watch
        """
        if watch_id not in self._watch_jobs:
            logger.warning(f"Watch {watch_id} not in scheduler")
            return

        job_id = self._watch_jobs[watch_id]
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed watch {watch_id}")
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")

    def get_next_run_time(self, watch_id: int) -> Optional[str]:
        """Get the next scheduled run time for a watch.

        Args:
            watch_id: Database ID of the watch

        Returns:
            ISO-formatted datetime string or None if watch not scheduled
        """
        if watch_id not in self._watch_jobs:
            return None

        job_id = self._watch_jobs[watch_id]
        job = self.scheduler.get_job(job_id)
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return None

    def list_watches(self) -> list[dict]:
        """List all scheduled watches with their status.

        Returns:
            List of dicts with watch_id, job_id, next_run_time, paused status
        """
        watches = []
        for watch_id, job_id in self._watch_jobs.items():
            job = self.scheduler.get_job(job_id)
            if job:
                watches.append(
                    {
                        "watch_id": watch_id,
                        "job_id": job_id,
                        "next_run_time": (
                            job.next_run_time.isoformat() if job.next_run_time else None
                        ),
                        "paused": not job.next_run_time,
                    }
                )
        return watches

    async def _execute_watch(self, watch_id: int, schedule: ParsedSchedule) -> None:
        """Execute a watch check (called by APScheduler).

        Args:
            watch_id: Database ID of the watch
            schedule: Parsed schedule configuration
        """
        # Check time window
        if not schedule.should_execute_now():
            logger.debug(f"Watch {watch_id} skipped (outside time window)")
            return

        logger.info(f"Executing watch {watch_id}")

        # Call the watch check function
        if self._watch_check_fn:
            try:
                await self._watch_check_fn(watch_id)
            except Exception as e:
                logger.error(f"Watch {watch_id} check failed: {e}", exc_info=True)
        else:
            logger.warning(f"No watch check function set for watch {watch_id}")

    def _on_job_executed(self, event: JobEvent) -> None:
        """Log job execution events for monitoring.

        Args:
            event: APScheduler job event
        """
        if event.exception:
            watch_id = event.job_id.replace("watch_", "")
            logger.error(f"Watch {watch_id} job failed: {event.exception}")
        else:
            logger.debug(f"Watch job {event.job_id} executed successfully")


# Global scheduler instance (singleton pattern for FastAPI lifespan)
_global_scheduler: Optional[WatchScheduler] = None


def get_scheduler() -> WatchScheduler:
    """Get the global scheduler instance.

    Returns:
        WatchScheduler instance (creates if doesn't exist)

    Raises:
        RuntimeError: If called before lifespan initialization
    """
    global _global_scheduler
    if _global_scheduler is None:
        raise RuntimeError(
            "Scheduler not initialized. "
            "Use the scheduler_lifespan context manager or call init_scheduler() first."
        )
    return _global_scheduler


def init_scheduler() -> WatchScheduler:
    """Initialize the global scheduler instance.

    Returns:
        WatchScheduler instance
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = WatchScheduler()
    return _global_scheduler


@asynccontextmanager
async def scheduler_lifespan():
    """FastAPI lifespan context manager for the scheduler.

    Usage in FastAPI app:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with scheduler_lifespan():
                yield
    """
    scheduler = init_scheduler()
    scheduler.start()
    try:
        yield scheduler
    finally:
        scheduler.stop()
