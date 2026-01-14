# TimeTrack CLI

A minimal, local-first time tracking application. No cloud, no accounts, no telemetry—just a SQLite database in the same folder as the app.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run commands
python cli.py start "Project Name"    # Start tracking
python cli.py stop                     # Stop tracking
python cli.py status                   # See current state
```

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

# Build the executable
pyinstaller --onefile cli.py --name tt

# The executable will be in dist/tt (or dist/tt.exe on Windows)
```

After building, move `dist/tt` to somewhere in your PATH for easy access.

## Data Storage

All data is stored in `timetrack.db` in the same directory as the script. This is a standard SQLite database file. You can:

- Back it up by copying the file
- Inspect it with any SQLite browser (like DB Browser for SQLite)
- Move it between machines

## Project Structure

```
timetrack/
├── cli.py           # Command definitions and entry point
├── db.py            # Database operations (SQLite)
├── models.py        # Data structures (Session, Project)
├── requirements.txt # Python dependencies
├── README.md        # This file
└── timetrack.db     # Created on first run (your data)
```

## Extending This

Some ideas for future features:
- **GUI wrapper**: Add a CustomTkinter interface that calls the same db.py functions
- **Idle detection**: A background process that auto-pauses after inactivity
- **Tags**: Add a tags column to sessions for more granular categorization
- **Pomodoro mode**: Auto-stop after 25 minutes with a break timer
- **Daily goals**: Set target hours per project and track progress
