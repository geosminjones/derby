"""
models.py - Data structures for the time tracker

Dataclasses are Python's clean way to define "just data" objects.
Think of them like structs in C, but with automatic __init__, __repr__, etc.
The @dataclass decorator writes boilerplate for you.
"""

# dataclasses: Python 3.7+ feature for clean data containers
# datetime: Standard library for timestamp handling
# Optional: Type hint meaning "this can be None"
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Tag:
    """
    Represents a tag that can be applied to projects.
    """
    id: Optional[int] = None
    name: str = ""
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Project:
    """
    Represents a named project/category for time tracking.

    Examples: "Job Search", "Brewing", "Exercise", "Reading"

    Background tasks are a special type of project that:
    - Don't have priority levels (always None)
    - Don't have tags
    - Are tracked separately in summaries
    """

    # Each field is: name: type = default_value
    # Fields without defaults must come before fields with defaults

    id: Optional[int] = None          # None until saved to DB (DB assigns ID)
    name: str = ""                     # Human-readable project name
    created_at: Optional[datetime] = None  # When this project was first created
    priority: int = 3                  # Priority 1-5 (1=highest, 5=lowest), ignored for background tasks
    tags: list[str] = field(default_factory=list)  # List of tag names, empty for background tasks
    is_background: bool = False        # True if this is a background task

    def __post_init__(self):
        """
        __post_init__ runs after the auto-generated __init__.
        Good place for validation or setting derived values.
        """
        # If no creation time provided, use current time
        if self.created_at is None:
            self.created_at = datetime.now()
        # Validate priority only for regular projects (not background tasks)
        if not self.is_background and not 1 <= self.priority <= 5:
            raise ValueError("Priority must be between 1 and 5")


@dataclass
class Session:
    """
    Represents a single tracked time block.
    
    A session has a start time, optionally an end time (None if still running),
    and belongs to a project.
    """
    
    id: Optional[int] = None          # None until saved to DB
    project_name: str = ""            # Which project this session belongs to
    start_time: Optional[datetime] = None  # When the timer started
    end_time: Optional[datetime] = None    # When the timer stopped (None = still active)
    notes: str = ""                   # Optional description of what you did
    
    # field(default_factory=...) is needed for mutable defaults
    # If you wrote `tags: list = []`, ALL instances would share the same list object
    # default_factory creates a NEW empty list for each instance
    # (Not using tags yet, but leaving this pattern here for future reference)
    
    @property
    def is_active(self) -> bool:
        """
        Properties let you access computed values like attributes.
        session.is_active instead of session.is_active()
        
        A session is "active" if it has started but not ended.
        """
        return self.start_time is not None and self.end_time is None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """
        Calculate how long this session lasted (or has lasted so far).
        
        Returns:
            timedelta object if session has started, None otherwise
            
        timedelta is Python's way of representing a span of time.
        You can do math with it: timedelta + datetime = datetime
        """
        # Can't have duration without a start time
        if self.start_time is None:
            return None
        
        # If session is still active, measure against current time
        # Otherwise, measure against end time
        end = self.end_time if self.end_time else datetime.now()
        
        return end - self.start_time
    
    @property
    def duration_seconds(self) -> int:
        """
        Duration as integer seconds.
        Useful for aggregation and database storage.
        """
        d = self.duration
        if d is None:
            return 0
        # total_seconds() returns a float, we cast to int
        return int(d.total_seconds())
    
    def format_duration(self) -> str:
        """
        Human-readable duration string.
        
        Returns strings like "1h 23m 45s" or "0h 05m 12s"
        """
        d = self.duration
        if d is None:
            return "0h 00m 00s"
        
        # Extract components from total seconds
        total_secs = int(d.total_seconds())
        
        # // is integer division (floor division)
        # % is modulo (remainder)
        hours = total_secs // 3600           # 3600 seconds in an hour
        minutes = (total_secs % 3600) // 60  # Remaining seconds, divided by 60
        seconds = total_secs % 60            # Remaining seconds after minutes
        
        # f-string with :02d means "pad to 2 digits with zeros"
        return f"{hours}h {minutes:02d}m {seconds:02d}s"


def parse_duration_string(duration_str: str) -> timedelta:
    """
    Parse human-friendly duration strings into timedelta objects.
    
    Supports formats like:
        "1h30m"     -> 1 hour, 30 minutes
        "45m"       -> 45 minutes
        "2h"        -> 2 hours
        "1h 30m"    -> 1 hour, 30 minutes (with space)
        "90"        -> 90 minutes (bare number = minutes)
    
    This is a module-level function, not a method, because it creates
    Sessions rather than operating on an existing one.
    """
    import re  # Regular expressions - pattern matching for strings
    
    # Strip whitespace and convert to lowercase for consistent parsing
    duration_str = duration_str.strip().lower()
    
    # Initialize components
    hours = 0
    minutes = 0
    
    # Try to match hours component: one or more digits followed by 'h'
    # r"..." is a raw string - backslashes aren't escape characters
    # \d+ means "one or more digits"
    # (h) captures the 'h' literally
    hour_match = re.search(r'(\d+)h', duration_str)
    if hour_match:
        # group(1) gets the first captured group (the digits)
        hours = int(hour_match.group(1))
    
    # Try to match minutes component: digits followed by 'm'
    min_match = re.search(r'(\d+)m', duration_str)
    if min_match:
        minutes = int(min_match.group(1))
    
    # If no h or m found, treat bare number as minutes
    # This is a usability convenience
    if not hour_match and not min_match:
        # re.fullmatch checks if ENTIRE string matches pattern
        bare_number = re.fullmatch(r'(\d+)', duration_str)
        if bare_number:
            minutes = int(bare_number.group(1))
    
    # Construct and return timedelta
    # timedelta(hours=1, minutes=30) represents 1:30:00
    return timedelta(hours=hours, minutes=minutes)
