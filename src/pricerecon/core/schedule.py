"""Schedule parsing and validation for watch scheduling."""

from dataclasses import dataclass
from datetime import time
from typing import Optional

import pytz
from zoneinfo import ZoneInfo


class ScheduleParseError(Exception):
    """Raised when schedule configuration is invalid."""
    pass


@dataclass
class TimeWindow:
    """Time window constraint for watch execution."""
    start: time  # Start time (e.g., 09:00)
    end: time    # End time (e.g., 21:00)
    days: set[str]  # Days of week (e.g., {"mon", "tue", "wed", "thu", "fri"})

    @classmethod
    def from_dict(cls, data: dict) -> "TimeWindow":
        """Create TimeWindow from JSON dict."""
        try:
            start_str = data.get("start", "00:00")
            end_str = data.get("end", "23:59")
            days = data.get("days", ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])

            # Parse times (HH:MM format)
            start = time.fromisoformat(start_str)
            end = time.fromisoformat(end_str)

            # Normalize days to lowercase
            normalized_days = {d.lower() for d in days}

            # Validate day names
            valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
            invalid_days = normalized_days - valid_days
            if invalid_days:
                raise ScheduleParseError(f"Invalid day names: {invalid_days}")

            return cls(start=start, end=end, days=normalized_days)
        except ValueError as e:
            raise ScheduleParseError(f"Invalid time format: {e}")

    def to_dict(self) -> dict:
        """Convert TimeWindow to JSON dict."""
        return {
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
            "days": sorted(list(self.days))
        }

    def is_allowed_now(self, timezone_str: str) -> bool:
        """Check if current time falls within the time window."""
        import datetime as dt

        tz = ZoneInfo(timezone_str)
        now = dt.datetime.now(tz)
        return self.is_allowed_at(now, timezone_str)

    def is_allowed_at(self, now, timezone_str: str) -> bool:
        """Check if a specific localized datetime falls within the time window."""
        if now.tzinfo is None:
            tz = ZoneInfo(timezone_str)
            now = now.replace(tzinfo=tz)
        else:
            now = now.astimezone(ZoneInfo(timezone_str))

        day_map = {
            0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"
        }
        current_day = day_map[now.weekday()]
        if current_day not in self.days:
            return False

        current_time = now.time()
        return self.start <= current_time <= self.end


@dataclass
class ParsedSchedule:
    """Parsed schedule configuration ready for APScheduler."""
    interval_seconds: int
    timezone: str
    time_window: Optional[TimeWindow] = None

    @classmethod
    def parse(cls, interval_str: str, timezone_str: str = "UTC", 
              time_window_data: Optional[dict] = None) -> "ParsedSchedule":
        """Parse schedule configuration from strings.

        Args:
            interval_str: Interval string (e.g., "4h", "30m", "1d")
            timezone_str: Timezone string (e.g., "Europe/London", "UTC")
            time_window_data: Optional time window dict (start, end, days)

        Returns:
            ParsedSchedule with parsed values

        Raises:
            ScheduleParseError: If configuration is invalid
        """
        # Parse interval
        interval_seconds = cls._parse_interval(interval_str)

        # Validate timezone
        try:
            pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ScheduleParseError(f"Unknown timezone: {timezone_str}")

        # Parse time window if provided
        time_window = None
        if time_window_data:
            time_window = TimeWindow.from_dict(time_window_data)

        return cls(
            interval_seconds=interval_seconds,
            timezone=timezone_str,
            time_window=time_window
        )

    @staticmethod
    def _parse_interval(interval_str: str) -> int:
        """Parse interval string to seconds.

        Supports: 'Xh' (hours), 'Xm' (minutes), 'Xd' (days)
        """
        interval_str = interval_str.strip().lower()

        if not interval_str:
            raise ScheduleParseError("Interval cannot be empty")

        # Extract number and unit
        unit = interval_str[-1]
        try:
            number = int(interval_str[:-1])
        except ValueError:
            raise ScheduleParseError(f"Invalid interval number: {interval_str}")

        if number <= 0:
            raise ScheduleParseError(f"Interval must be positive: {interval_str}")

        # Convert to seconds
        multipliers = {
            's': 1,        # seconds
            'm': 60,       # minutes
            'h': 3600,     # hours
            'd': 86400,    # days
        }

        if unit not in multipliers:
            raise ScheduleParseError(
                f"Invalid interval unit: {unit} (use s, m, h, d)"
            )

        return number * multipliers[unit]

    def should_execute_now(self) -> bool:
        """Check if watch should execute now based on time window."""
        if not self.time_window:
            return True
        return self.time_window.is_allowed_now(self.timezone)