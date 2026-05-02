"""
Scheduled data-refresh jobs for the financial analysis module.

Uses APScheduler's BackgroundScheduler to run periodic tasks that keep
market data fresh. The scheduler is started/stopped with FastAPI lifespan.
"""

from __future__ import annotations

import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from app.models_finance import Industry, SchedulerStatus
from app.services.data_sources import fetch_market_data, get_last_fetch_timestamp

_scheduler = BackgroundScheduler(timezone="UTC")
_last_refresh: dict[str, datetime.datetime] = {}


def _refresh_industry(industry: Industry) -> None:
    """Fetch and cache the latest market data for a single industry."""
    try:
        data = fetch_market_data(industry)
        _last_refresh[industry.value] = get_last_fetch_timestamp()
        logger.info(
            "Scheduled refresh complete",
            industry=industry.value,
            rows=data.get("rows", "stub"),
        )
    except (ImportError, ConnectionError, OSError, ValueError) as exc:
        logger.error("Scheduled refresh failed", industry=industry.value, error=str(exc))


def _daily_refresh_all() -> None:
    """Refresh market data for every tracked industry."""
    logger.info("Starting daily market data refresh for all industries")
    for industry in Industry:
        _refresh_industry(industry)
    logger.info("Daily market data refresh complete")


def start_scheduler() -> None:
    """Register jobs and start the background scheduler at application startup."""
    if _scheduler.running:
        return

    # Daily full refresh at 08:00 UTC (pre-market open)
    _scheduler.add_job(
        _daily_refresh_all,
        trigger="cron",
        hour=8,
        minute=0,
        id="daily_refresh_all",
        replace_existing=True,
    )

    # Per-industry weekly deep refresh (Saturday 06:00 UTC)
    for industry in Industry:
        _scheduler.add_job(
            _refresh_industry,
            trigger="cron",
            day_of_week="sat",
            hour=6,
            minute=0,
            args=[industry],
            id=f"weekly_refresh_{industry.value}",
            replace_existing=True,
        )

    _scheduler.start()
    logger.info("APScheduler started with {} jobs", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Stop the background scheduler gracefully."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


def get_scheduler_status() -> SchedulerStatus:
    """Return the current status of the scheduler and its registered jobs."""
    jobs = _scheduler.get_jobs()
    job_list = [
        {
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        }
        for job in jobs
    ]
    return SchedulerStatus(
        running=_scheduler.running,
        jobs=job_list,
        next_run_times={job["id"]: job["next_run_time"] for job in job_list},
    )
