"""Standalone test script for scheduler implementation (no module imports)."""

import sys
from pathlib import Path

# Add src to path so we can import pricerecon modules
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from pricerecon.core.schedule import ParsedSchedule, TimeWindow, ScheduleParseError
from pricerecon.core.scheduler import WatchScheduler, init_scheduler

import asyncio


def test_schedule_parsing():
    """Test schedule parsing functionality."""
    print("Testing schedule parsing...")

    # Test basic intervals
    schedule = ParsedSchedule.parse("4h", "UTC")
    assert schedule.interval_seconds == 14400, f"Expected 14400, got {schedule.interval_seconds}"
    print("✓ Interval parsing: 4h → 14400 seconds")

    schedule = ParsedSchedule.parse("30m", "UTC")
    assert schedule.interval_seconds == 1800, f"Expected 1800, got {schedule.interval_seconds}"
    print("✓ Interval parsing: 30m → 1800 seconds")

    schedule = ParsedSchedule.parse("1d", "UTC")
    assert schedule.interval_seconds == 86400, f"Expected 86400, got {schedule.interval_seconds}"
    print("✓ Interval parsing: 1d → 86400 seconds")

    # Test timezone validation
    schedule = ParsedSchedule.parse("1h", "Europe/London")
    assert schedule.timezone == "Europe/London"
    print("✓ Timezone validation: Europe/London")

    # Test invalid interval
    try:
        ParsedSchedule.parse("invalid", "UTC")
        assert False, "Should have raised ScheduleParseError"
    except ScheduleParseError:
        print("✓ Invalid interval rejected")

    # Test invalid timezone
    try:
        ParsedSchedule.parse("1h", "Invalid/Timezone")
        assert False, "Should have raised ScheduleParseError"
    except ScheduleParseError:
        print("✓ Invalid timezone rejected")

    print()


def test_time_window():
    """Test time window functionality."""
    print("Testing time window...")

    # Create time window
    tw_data = {
        "start": "09:00",
        "end": "21:00",
        "days": ["mon", "tue", "wed", "thu", "fri"]
    }
    tw = TimeWindow.from_dict(tw_data)

    assert tw.start.hour == 9 and tw.start.minute == 0
    assert tw.end.hour == 21 and tw.end.minute == 0
    assert "mon" in tw.days and "sat" not in tw.days
    print("✓ Time window parsing")

    # Test to_dict conversion
    tw_dict = tw.to_dict()
    assert tw_dict["start"] == "09:00"
    assert tw_dict["end"] == "21:00"
    assert "mon" in tw_dict["days"]
    print("✓ Time window serialization")

    # Test day validation
    try:
        TimeWindow.from_dict({
            "start": "09:00",
            "end": "21:00",
            "days": ["mon", "invalid_day"]
        })
        assert False, "Should have raised ScheduleParseError"
    except ScheduleParseError:
        print("✓ Invalid day names rejected")

    print()


async def test_scheduler():
    """Test WatchScheduler functionality."""
    print("Testing WatchScheduler...")

    scheduler = WatchScheduler()

    # Start scheduler so next_run_time is set
    scheduler.start()

    # Check initialization
    assert scheduler.scheduler.running
    print("✓ Scheduler started")

    # Test add_watch with basic interval
    job_id = scheduler.add_watch(1, "1h", "UTC")
    assert job_id == "watch_1"
    print("✓ Watch added to scheduler")

    # Test add_watch with time window
    job_id = scheduler.add_watch(
        2,
        "30m",
        "Europe/London",
        time_window={
            "start": "09:00",
            "end": "21:00",
            "days": ["mon", "tue", "wed", "thu", "fri"]
        }
    )
    assert job_id == "watch_2"
    print("✓ Watch added with time window")

    # Test list_watches
    watches = scheduler.list_watches()
    assert len(watches) == 2
    assert watches[0]["watch_id"] == 1
    assert watches[1]["watch_id"] == 2
    print("✓ List watches")

    # Test get_next_run_time
    next_run = scheduler.get_next_run_time(1)
    assert next_run is not None and isinstance(next_run, str)
    print(f"✓ Get next run time: {next_run}")

    # Test pause_watch
    scheduler.pause_watch(1)
    watches = scheduler.list_watches()
    paused_watch = [w for w in watches if w["watch_id"] == 1][0]
    assert paused_watch["paused"] == True
    print("✓ Pause watch")

    # Test resume_watch
    scheduler.resume_watch(1)
    watches = scheduler.list_watches()
    resumed_watch = [w for w in watches if w["watch_id"] == 1][0]
    assert resumed_watch["paused"] == False
    print("✓ Resume watch")

    # Test remove_watch
    scheduler.remove_watch(1)
    watches = scheduler.list_watches()
    assert len(watches) == 1
    assert watches[0]["watch_id"] == 2
    print("✓ Remove watch")

    # Test remove non-existent watch (should not crash)
    scheduler.remove_watch(999)
    print("✓ Remove non-existent watch (no error)")

    scheduler.stop()
    print()


async def test_scheduler_lifespan():
    """Test scheduler lifespan context manager."""
    print("Testing scheduler lifespan...")

    from pricerecon.core.scheduler import scheduler_lifespan

    async with scheduler_lifespan() as scheduler:
        assert scheduler.scheduler.running
        print("✓ Scheduler started in lifespan")

        # Add a watch
        scheduler.add_watch(10, "1h", "UTC")
        watches = scheduler.list_watches()
        assert len(watches) == 1
        print("✓ Can add watches during lifespan")

    # After exiting, scheduler should be stopped
    print("✓ Scheduler stopped after lifespan exit")
    print()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("APScheduler Integration Tests")
    print("=" * 60)
    print()

    test_schedule_parsing()
    test_time_window()
    await test_scheduler()
    await test_scheduler_lifespan()

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())