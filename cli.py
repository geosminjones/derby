#!/usr/bin/env python3
"""
cli.py - Command-line interface for the time tracker

This is the entry point for the application. It defines all the commands
you can run from the terminal.

Typer is a CLI framework that uses Python type hints to automatically:
- Parse command-line arguments
- Generate help text
- Validate input types
- Handle errors gracefully

The #!/usr/bin/env python3 line (shebang) tells Unix-like systems to
run this file with Python. It's ignored on Windows.
"""

# Typer: Modern CLI framework (install with: pip install typer[all])
# The [all] includes Rich for pretty output
import typer

# Rich: Library for beautiful terminal output (comes with typer[all])
# Console: Main interface for printing styled text
# Table: Creates formatted tables
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Standard library imports
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

# Our local modules
import db
from models import Session, parse_duration_string


# =============================================================================
# APP SETUP
# =============================================================================

# Create the Typer app instance
# This object collects all our commands and handles routing
app = typer.Typer(
    name="tt",                          # Name shown in help text
    help="A simple time tracker CLI",   # Description in help
    add_completion=False                # Disable shell completion (simpler)
)

# Create Rich console for formatted output
# All our printing goes through this for consistent styling
console = Console()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_time(dt: datetime) -> str:
    """
    Format a datetime nicely for display.
    
    strftime() formats datetime using format codes:
    %Y = 4-digit year, %m = 2-digit month, %d = 2-digit day
    %H = 24-hour hour, %M = minute, %S = second
    %I = 12-hour hour, %p = AM/PM
    """
    return dt.strftime("%Y-%m-%d %I:%M %p")


def format_duration_short(seconds: int) -> str:
    """
    Format seconds as a compact duration string.
    Examples: "1:23:45" or "0:05:30"
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"


def format_duration_human(seconds: int) -> str:
    """
    Format seconds as human-readable duration.
    Examples: "1h 23m" or "5m" or "2h 0m"
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def get_today_range() -> tuple[datetime, datetime]:
    """
    Get datetime range for "today" (midnight to midnight).
    
    Returns:
        Tuple of (start_of_today, start_of_tomorrow)
        
    Using start of tomorrow as the end bound makes the range exclusive,
    which is standard for date ranges and avoids off-by-one issues.
    """
    now = datetime.now()
    
    # replace() creates a copy with some fields changed
    # Setting hour/minute/second/microsecond to 0 gives midnight
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Add one day to get tomorrow's midnight
    start_of_tomorrow = start_of_today + timedelta(days=1)
    
    return start_of_today, start_of_tomorrow


def get_week_range() -> tuple[datetime, datetime]:
    """
    Get datetime range for "this week" (Monday to Sunday).
    
    weekday() returns 0 for Monday, 6 for Sunday.
    """
    now = datetime.now()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Go back to Monday by subtracting the weekday number
    start_of_week = start_of_today - timedelta(days=now.weekday())
    
    # Week ends 7 days after it starts
    end_of_week = start_of_week + timedelta(days=7)
    
    return start_of_week, end_of_week


# =============================================================================
# COMMANDS
# =============================================================================

@app.command()
def start(
    project: str = typer.Argument(..., help="Name of the project to track")
):
    """
    Start tracking time for a project.

    You can track multiple projects simultaneously.
    Starting a project that's already being tracked will show a warning.
    """
    # Initialize database tables if this is first run
    db.init_database()

    # Check if THIS specific project already has an active session
    active_for_project = db.get_active_session_by_project(project)

    if active_for_project:
        console.print(
            f"[yellow]⚠[/yellow]  [bold]{project}[/bold] is already being tracked "
            f"(started {format_time(active_for_project.start_time)})"
        )
        raise typer.Exit(code=1)

    # Show other active sessions as info (not blocking)
    other_active = db.get_active_sessions()
    if other_active:
        console.print(
            f"[dim]Note: {len(other_active)} other session(s) are also active[/dim]"
        )

    # Start the new session
    session = db.start_session(project)

    console.print(
        f"[green]▶[/green]  Started tracking [bold]{project}[/bold] "
        f"at {format_time(session.start_time)}"
    )


@app.command()
def stop(
    project: Optional[str] = typer.Argument(
        None,
        help="Project name to stop (optional - stops most recent if omitted)"
    ),
    notes: Optional[str] = typer.Option(
        None,
        "--notes", "-n",
        help="Notes about what you worked on"
    )
):
    """
    Stop a tracking session.

    If PROJECT is provided, stops that specific project.
    Otherwise, stops the most recently started active session.
    """
    db.init_database()

    # Try to stop the session
    session = db.stop_session(project_name=project, notes=notes or "")

    if session is None:
        if project:
            console.print(f"[yellow]⚠[/yellow]  No active session for [bold]{project}[/bold]")
        else:
            console.print("[yellow]⚠[/yellow]  No active session to stop")
        raise typer.Exit(code=1)

    console.print(
        f"[red]■[/red]  Stopped [bold]{session.project_name}[/bold] — "
        f"Duration: [bold]{session.format_duration()}[/bold]"
    )


@app.command()
def stopall(
    notes: Optional[str] = typer.Option(
        None,
        "--notes", "-n",
        help="Notes to apply to all stopped sessions"
    ),
    yes: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompt"
    )
):
    """
    Stop ALL active tracking sessions.
    """
    db.init_database()

    active = db.get_active_sessions()

    if not active:
        console.print("[yellow]⚠[/yellow]  No active sessions to stop")
        return

    # Show what will be stopped
    console.print(f"[bold]Active sessions ({len(active)}):[/bold]")
    for s in active:
        console.print(f"  - {s.project_name} ({s.format_duration()})")

    # Confirm unless -y flag
    if not yes:
        if not typer.confirm("\nStop all these sessions?"):
            console.print("[dim]Cancelled[/dim]")
            return

    stopped = db.stop_all_sessions(notes=notes or "")

    console.print(f"\n[red]■[/red]  Stopped {len(stopped)} session(s)")


@app.command()
def switch(
    project: str = typer.Argument(..., help="Project to switch to"),
    from_project: Optional[str] = typer.Option(
        None,
        "--from", "-f",
        help="Specific project to switch from (default: most recent)"
    )
):
    """
    Stop one session and start a new one.

    By default, stops the most recently started session.
    Use --from to specify which project to stop.
    """
    db.init_database()

    # Prevent switching to same project
    if from_project and from_project == project:
        console.print(f"[yellow]⚠[/yellow]  Already tracking [bold]{project}[/bold]")
        raise typer.Exit(code=1)

    # Check if target project is already active
    if db.get_active_session_by_project(project):
        console.print(f"[yellow]⚠[/yellow]  [bold]{project}[/bold] is already being tracked")
        console.print(f"   Use [bold]tt stop {from_project or '<project>'}[/bold] instead")
        raise typer.Exit(code=1)

    # Stop the source session
    stopped = db.stop_session(project_name=from_project)

    if stopped:
        console.print(
            f"[red]■[/red]  Stopped [bold]{stopped.project_name}[/bold] — "
            f"Duration: [bold]{stopped.format_duration()}[/bold]"
        )

    # Start new session
    session = db.start_session(project)
    console.print(f"[green]▶[/green]  Started tracking [bold]{project}[/bold]")


@app.command()
def status():
    """
    Show current tracking status.

    Displays all active sessions with their durations.
    """
    db.init_database()

    active_sessions = db.get_active_sessions()

    if not active_sessions:
        console.print("[dim]●[/dim]  No active sessions — you're idle")
        return

    # Create table for multiple sessions
    table = Table(title=f"[green]● Active Sessions ({len(active_sessions)})[/green]")
    table.add_column("Project", style="bold")
    table.add_column("Started", style="cyan")
    table.add_column("Duration", justify="right", style="green")

    for s in active_sessions:
        table.add_row(
            s.project_name,
            format_time(s.start_time),
            s.format_duration()
        )

    console.print(table)


@app.command()
def log(
    project: str = typer.Argument(..., help="Project name"),
    duration: str = typer.Argument(
        ...,
        help="Duration (e.g., '1h30m', '45m', '2h')"
    ),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Session notes"),
    date: Optional[str] = typer.Option(
        None,
        "--date", "-d",
        help="Date for the session (YYYY-MM-DD), defaults to today"
    )
):
    """
    Log a completed session retroactively.
    
    Use this when you forgot to start the timer but want to record
    time you spent on something.
    
    Examples:
        tt log "Job Search" 1h30m
        tt log Reading 45m --notes "Finished chapter 3"
        tt log Exercise 1h --date 2024-01-15
    """
    db.init_database()
    
    # Parse the duration string into a timedelta
    try:
        td = parse_duration_string(duration)
    except Exception:
        console.print(f"[red]✗[/red]  Invalid duration format: {duration}")
        console.print("   Use formats like: 1h30m, 45m, 2h")
        raise typer.Exit(code=1)
    
    # Parse optional date
    session_date = None
    if date:
        try:
            # strptime() parses a string into datetime (opposite of strftime)
            # We parse just the date, then set time to end of day
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            # Set to 5 PM so the session "happened during the day"
            session_date = parsed_date.replace(hour=17, minute=0, second=0)
        except ValueError:
            console.print(f"[red]✗[/red]  Invalid date format: {date}")
            console.print("   Use YYYY-MM-DD format (e.g., 2024-01-15)")
            raise typer.Exit(code=1)
    
    # Create the session
    session = db.log_session(
        project_name=project,
        duration=td,
        notes=notes or "",
        date=session_date
    )
    
    console.print(
        f"[green]✓[/green]  Logged [bold]{session.format_duration()}[/bold] "
        f"for [bold]{project}[/bold]"
    )


@app.command(name="list")
def list_sessions(
    project: Optional[str] = typer.Option(
        None, "--project", "-p",
        help="Filter by project"
    ),
    limit: int = typer.Option(
        10, "--limit", "-l",
        help="Number of sessions to show"
    )
):
    """
    List recent sessions.
    
    Shows a table of completed sessions, newest first.
    
    Note: The function is named list_sessions because 'list' is a
    Python built-in. The name="list" in the decorator sets the
    actual command name.
    """
    db.init_database()
    
    sessions = db.get_sessions(project_name=project, limit=limit)
    
    if not sessions:
        console.print("[dim]No sessions found[/dim]")
        return
    
    # Create a Rich table
    table = Table(title="Recent Sessions")
    
    # Add columns with styling
    table.add_column("Date", style="cyan")
    table.add_column("Project", style="bold")
    table.add_column("Duration", justify="right", style="green")
    table.add_column("Notes", style="dim", max_width=30)
    
    # Add rows
    for s in sessions:
        table.add_row(
            s.start_time.strftime("%Y-%m-%d %H:%M") if s.start_time else "",
            s.project_name,
            s.format_duration(),
            # Truncate long notes
            (s.notes[:27] + "...") if len(s.notes) > 30 else s.notes
        )
    
    console.print(table)


@app.command()
def summary(
    period: str = typer.Option(
        "today",
        "--period", "-p",
        help="Time period: today, week, or all"
    ),
    weekd: bool = typer.Option(
        False,
        "--weekd",
        help="Show time per day of week (Mon-Sun columns)"
    )
):
    """
    Show time summary by project.

    Displays total time tracked per project for the specified period.
    Results are grouped by priority and sorted by time within each group.
    """
    db.init_database()

    # Determine date range based on period
    start_date = None
    end_date = None
    period_label = period.capitalize()

    if period.lower() == "today":
        start_date, end_date = get_today_range()
    elif period.lower() == "week":
        start_date, end_date = get_week_range()
    elif period.lower() == "all":
        pass  # No date filter
    else:
        console.print(f"[red]✗[/red]  Unknown period: {period}")
        console.print("   Use: today, week, or all")
        raise typer.Exit(code=1)

    priority_colors = {1: "red", 2: "yellow", 3: "white", 4: "blue", 5: "dim"}
    priority_labels = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Very Low"}

    if weekd:
        # Weekly day breakdown view
        if start_date is None or end_date is None:
            # For --weekd with "all" period, use current week
            start_date, end_date = get_week_range()
            period_label = "Week"

        data = db.get_summary_by_day(start_date=start_date, end_date=end_date)

        if not data:
            console.print(f"[dim]No sessions found for {period_label.lower()}[/dim]")
            return

        # Build list of day dates (Mon-Sun)
        day_dates = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        current = start_date
        while current < end_date and len(day_dates) < 7:
            day_dates.append(current.strftime("%Y-%m-%d"))
            current = current + timedelta(days=1)

        # Create table with day columns
        table = Table(title=f"Summary — {period_label}")
        table.add_column("Project", style="bold")
        table.add_column("Priority", justify="center")
        for day_name in day_names[:len(day_dates)]:
            table.add_column(day_name, justify="right", style="cyan")
        table.add_column("Total", justify="right", style="green")

        total_seconds = 0
        day_totals = {d: 0 for d in day_dates}
        last_priority = None

        for project_name, info in data.items():
            priority = info["priority"]
            days = info["days"]
            project_total = info["total"]
            total_seconds += project_total

            # Add section separator between priority groups
            if last_priority is not None and priority != last_priority:
                table.add_section()
            last_priority = priority

            # Build row with day values
            color = priority_colors.get(priority, "white")
            priority_str = f"[{color}]{priority} ({priority_labels.get(priority, 'Medium')})[/{color}]"

            row = [project_name, priority_str]
            for day_date in day_dates:
                day_secs = days.get(day_date, 0)
                day_totals[day_date] += day_secs
                if day_secs > 0:
                    row.append(f"{day_secs / 3600:.2f}")
                else:
                    row.append("[dim]-[/dim]")
            row.append(f"{project_total / 3600:.2f}")

            table.add_row(*row)

        # Add total row
        table.add_section()
        total_row = ["[bold]TOTAL[/bold]", ""]
        for day_date in day_dates:
            day_total = day_totals[day_date]
            if day_total > 0:
                total_row.append(f"[bold]{day_total / 3600:.2f}[/bold]")
            else:
                total_row.append("[dim]-[/dim]")
        total_row.append(f"[bold]{total_seconds / 3600:.2f}[/bold]")
        table.add_row(*total_row)

        console.print(table)
    else:
        # Standard view with priority column
        data = db.get_summary_with_priority(start_date=start_date, end_date=end_date)

        if not data:
            console.print(f"[dim]No sessions found for {period_label.lower()}[/dim]")
            return

        # Create summary table
        table = Table(title=f"Summary — {period_label}")
        table.add_column("Project", style="bold")
        table.add_column("Priority", justify="center")
        table.add_column("Time", justify="right", style="green")
        table.add_column("Hours", justify="right", style="cyan")

        total_seconds = 0
        last_priority = None

        for project_name, info in data.items():
            seconds = info["seconds"]
            priority = info["priority"]
            total_seconds += seconds

            # Add section separator between priority groups
            if last_priority is not None and priority != last_priority:
                table.add_section()
            last_priority = priority

            hours = round(seconds / 3600, 2)
            color = priority_colors.get(priority, "white")
            priority_str = f"[{color}]{priority} ({priority_labels.get(priority, 'Medium')})[/{color}]"

            table.add_row(
                project_name,
                priority_str,
                format_duration_human(seconds),
                f"{hours:.2f}"
            )

        # Add total row
        table.add_section()
        total_hours = round(total_seconds / 3600, 2)
        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            f"[bold]{format_duration_human(total_seconds)}[/bold]",
            f"[bold]{total_hours:.2f}[/bold]"
        )

        console.print(table)


@app.command()
def projects(
    filter_tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    filter_priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Filter by max priority (1-5)")
):
    """
    List all projects with their priority and tags.
    """
    db.init_database()

    project_list = db.list_projects(tag=filter_tag, min_priority=filter_priority)

    if not project_list:
        console.print("[dim]No projects found[/dim]")
        return

    table = Table(title="Projects")
    table.add_column("Name", style="bold")
    table.add_column("Priority", justify="center")
    table.add_column("Tags", style="cyan")

    priority_colors = {1: "red", 2: "yellow", 3: "white", 4: "blue", 5: "dim"}
    priority_labels = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Very Low"}

    for p in project_list:
        color = priority_colors.get(p.priority, "white")
        priority_str = f"[{color}]{p.priority} ({priority_labels.get(p.priority, 'Medium')})[/{color}]"
        tags_str = ", ".join(p.tags) if p.tags else "[dim]-[/dim]"
        table.add_row(p.name, priority_str, tags_str)

    console.print(table)


@app.command()
def export(
    output: str = typer.Option(
        "timetrack_export.csv",
        "--output", "-o",
        help="Output file path"
    )
):
    """
    Export all sessions to a CSV file.
    
    The CSV can be opened in Excel, Google Sheets, or any spreadsheet app.
    """
    db.init_database()
    
    # Resolve to absolute path for clarity
    filepath = Path(output).resolve()
    
    db.export_sessions_csv(str(filepath))
    
    console.print(f"[green]✓[/green]  Exported to: {filepath}")


@app.command()
def cancel(
    project: Optional[str] = typer.Argument(
        None,
        help="Project to cancel (optional - cancels most recent if omitted)"
    )
):
    """
    Cancel an active session without saving.

    Use this when you started tracking by mistake.
    """
    db.init_database()

    if project:
        active = db.get_active_session_by_project(project)
    else:
        active = db.get_active_session()

    if active is None:
        if project:
            console.print(f"[yellow]⚠[/yellow]  No active session for [bold]{project}[/bold]")
        else:
            console.print("[yellow]⚠[/yellow]  No active session to cancel")
        return

    # Confirm before deleting (data loss protection)
    confirm = typer.confirm(
        f"Cancel session for '{active.project_name}' "
        f"({active.format_duration()})?"
    )

    if not confirm:
        console.print("[dim]Cancelled[/dim]")
        return

    # Delete the session from database
    db.delete_session(active.id)

    console.print(f"[yellow]✗[/yellow]  Cancelled session for [bold]{active.project_name}[/bold]")


@app.command()
def delete(
    session_id: int = typer.Argument(..., help="ID of the session to delete")
):
    """
    Delete a specific session by ID.
    
    Use `tt list` to see session IDs (they're shown in the Date column).
    """
    db.init_database()
    
    # Get the session first to show details in confirmation
    sessions = db.get_sessions(limit=100)
    target = None
    for s in sessions:
        if s.id == session_id:
            target = s
            break
    
    if target is None:
        console.print(f"[red]✗[/red]  Session {session_id} not found")
        raise typer.Exit(code=1)
    
    # Confirm deletion
    console.print(
        f"Session: [bold]{target.project_name}[/bold] on "
        f"{target.start_time.strftime('%Y-%m-%d')} ({target.format_duration()})"
    )
    
    if not typer.confirm("Delete this session?"):
        console.print("[dim]Cancelled[/dim]")
        return
    
    db.delete_session(session_id)
    console.print(f"[green]✓[/green]  Deleted session {session_id}")


# =============================================================================
# TAG AND PRIORITY COMMANDS
# =============================================================================

@app.command()
def tag(
    project: str = typer.Argument(..., help="Project name"),
    add: Optional[List[str]] = typer.Option(None, "--add", "-a", help="Tag(s) to add"),
    remove: Optional[List[str]] = typer.Option(None, "--remove", "-r", help="Tag(s) to remove")
):
    """
    Manage tags for a project.

    Examples:
        tt tag "Job Search" --add urgent --add work
        tt tag "Job Search" --remove urgent
    """
    db.init_database()

    p = db.get_project(project)
    if p is None:
        console.print(f"[red]✗[/red]  Project [bold]{project}[/bold] not found")
        raise typer.Exit(code=1)

    if add:
        for t in add:
            if db.add_tag_to_project(p.id, t):
                console.print(f"[green]+[/green]  Added tag [cyan]{t}[/cyan]")
            else:
                console.print(f"[dim]Tag {t} already exists[/dim]")

    if remove:
        for t in remove:
            if db.remove_tag_from_project(p.id, t):
                console.print(f"[red]-[/red]  Removed tag [cyan]{t}[/cyan]")
            else:
                console.print(f"[dim]Tag {t} not found[/dim]")

    # Show current state
    p = db.get_project(project)
    console.print(f"\n[bold]{p.name}[/bold] tags: {', '.join(p.tags) if p.tags else '[dim]none[/dim]'}")


@app.command()
def priority(
    project: str = typer.Argument(..., help="Project name"),
    level: int = typer.Argument(..., help="Priority level (1-5, where 1 is highest)")
):
    """
    Set priority for a project.

    Priority levels:
      1 = Critical
      2 = High
      3 = Medium (default)
      4 = Low
      5 = Very Low
    """
    db.init_database()

    if not 1 <= level <= 5:
        console.print("[red]✗[/red]  Priority must be between 1 and 5")
        raise typer.Exit(code=1)

    p = db.update_project_priority(project, level)

    if p is None:
        console.print(f"[red]✗[/red]  Project [bold]{project}[/bold] not found")
        raise typer.Exit(code=1)

    priority_labels = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Very Low"}
    console.print(
        f"[green]✓[/green]  Set [bold]{project}[/bold] priority to "
        f"{level} ({priority_labels[level]})"
    )


@app.command()
def tags():
    """
    List all tags and their usage.
    """
    db.init_database()

    all_tags = db.list_tags()

    if not all_tags:
        console.print("[dim]No tags created yet[/dim]")
        return

    table = Table(title="Tags")
    table.add_column("Tag", style="cyan")
    table.add_column("Projects", justify="right")

    for t in all_tags:
        projects = db.get_projects_by_tag(t.name)
        table.add_row(t.name, str(len(projects)))

    console.print(table)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    """
    This block runs when the script is executed directly.
    
    `python cli.py start Project` calls app() which parses arguments
    and routes to the appropriate command function.
    
    The if __name__ == "__main__" pattern prevents this code from
    running when the module is imported rather than executed.
    """
    app()
