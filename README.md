# Derby

A minimal, local-first time tracking application with both CLI and GUI interfaces. No cloud, no accounts, no telemetry—just a SQLite database stored locally.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2a. Run the GUI
python gui.py

# 2b. Or use the CLI
python cli.py start "Project Name"    # Start tracking
python cli.py stop                     # Stop tracking
python cli.py status                   # See current state

# Build the executable for GUI use
pyinstaller --onefile gui.py --name derby --icon=jockey.ico --noconsole

```

## GUI Features

The GUI (`python gui.py`) provides a tabbed interface:

- **Timer Tab**: Start/stop sessions for regular projects and background tasks, view active sessions with live duration updates
- **History Tab**: View past sessions with filtering by project and time period, delete sessions
- **Summary Tab**: Time aggregations by period (Today/This Week/All Time) with weekly day-by-day breakdown
- **Projects Tab**: Manage projects and background tasks—add, rename, edit priority (1-5), and manage tags

## Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `start <project>` | Begin tracking time | `python cli.py start "Job Search"` |
| `stop` | End the current session | `python cli.py stop --notes "Applied to 3 jobs"` |
| `switch <project>` | Stop current, start new | `python cli.py switch "Reading"` |
| `status` | Show current session | `python cli.py status` |
| `log <project> <duration>` | Add time retroactively | `python cli.py log Exercise 45m` |
| `list` | Show recent sessions | `python cli.py list --limit 20` |
| `summary` | Time totals by project | `python cli.py summary --period week` |
| `projects` | List all projects | `python cli.py projects` |
| `export` | Save to CSV | `python cli.py export --output tracking.csv` |
| `cancel` | Discard active session | `python cli.py cancel` |
| `delete <id>` | Remove a session | `python cli.py delete 42` |

## Duration Formats

When using `log`, you can specify durations like:
- `1h30m` — 1 hour 30 minutes  
- `2h` — 2 hours
- `45m` — 45 minutes
- `90` — 90 minutes (bare numbers = minutes)

## Building a Standalone Executable

To create a single file you can run without Python installed:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable for command-line interface use
pyinstaller --onefile cli.py --name tt

# Build the executable for GUI use
pyinstaller --onefile gui.py --name derby --icon=jockey.ico

# The executable will be in dist/tt (or dist/tt.exe on Windows)
```

After building, move `dist/tt` to somewhere in your PATH for easy access.

## Data Storage

All data is stored in `~/.timetrack/timetrack.db`. This is a standard SQLite database file. You can:

- Back it up by copying the file
- Inspect it with any SQLite browser (like DB Browser for SQLite)
- Move it between machines

## Project Structure

```
derby/
├── cli.py           # CLI entry point (Typer-based)
├── gui.py           # GUI entry point (Tkinter-based)
├── db.py            # Database operations (SQLite)
├── models.py        # Data structures (Session, Project, Tag)
├── requirements.txt # Python dependencies
├── README.md        # This file
└── CLAUDE.md        # Development guidelines
```

## Features

- **Projects**: Regular time-tracked projects with priority levels (1-5) and tags
- **Background Tasks**: Separate category for ongoing background activities
- **Tags**: Organize projects with tags for filtering and categorization
- **Priority Levels**: 1 (Critical) to 5 (Very Low) for project organization
- **Manual Logging**: Add time retroactively with the `log` command or GUI dialog
- **CSV Export**: Export session data for external analysis

## Future Ideas

- **Idle detection**: A background process that auto-pauses after inactivity
- **Pomodoro mode**: Auto-stop after 25 minutes with a break timer
- **Daily goals**: Set target hours per project and track progress
