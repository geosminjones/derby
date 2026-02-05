"""
db.py - Database layer for the time tracker

This module handles all SQLite interactions. By isolating DB logic here,
the CLI (and future GUI) don't need to know anything about SQL.

SQLite stores the entire database in a single file. No server process,
no configuration, no network—just a file. Python's sqlite3 module is
part of the standard library, so zero external dependencies.

Key concepts:
- Connection: An open link to the database file
- Cursor: An object that executes queries and fetches results
- Transaction: A group of operations that succeed or fail together
"""

import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Import our data models
from models import Project, Session, Tag, PauseEvent

# Default data directory in user's home
DEFAULT_DATA_DIR = Path.home() / ".timetrack"

# Config file to store the data directory location
# This is stored in the default location so we can always find it
CONFIG_DIR = Path.home() / ".timetrack"
CONFIG_FILE = CONFIG_DIR / "config.txt"


def _load_data_directory() -> Path:
    """
    Load the configured data directory from config file.
    Falls back to default if not configured.
    """
    if CONFIG_FILE.exists():
        try:
            config_path = Path(CONFIG_FILE.read_text().strip())
            if config_path.exists() and config_path.is_dir():
                return config_path
        except Exception:
            pass
    return DEFAULT_DATA_DIR


def _save_data_directory(path: Path):
    """Save the data directory path to config file."""
    CONFIG_DIR.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(str(path))


def get_data_directory() -> Path:
    """Get the current data directory."""
    return DATA_DIR


def get_database_path() -> Path:
    """Get the full path to the database file."""
    return DATABASE_PATH


def set_data_directory(new_path: Path, copy_existing: bool = False) -> bool:
    """
    Set a new data directory for the database.

    Args:
        new_path: The new directory to use for storing the database
        copy_existing: If True, copy the current database to the new location

    Returns:
        True if successful, False otherwise
    """
    global DATA_DIR, DATABASE_PATH

    try:
        new_path = Path(new_path)
        new_path.mkdir(parents=True, exist_ok=True)

        new_db_path = new_path / "timetrack.db"

        if copy_existing and DATABASE_PATH.exists():
            shutil.copy2(DATABASE_PATH, new_db_path)

        # Update the module-level variables
        DATA_DIR = new_path
        DATABASE_PATH = new_db_path

        # Save the new path to config
        _save_data_directory(new_path)

        # Initialize the database at the new location
        init_database()

        return True
    except Exception as e:
        print(f"Error setting data directory: {e}")
        return False


def backup_database(backup_path: Path) -> bool:
    """
    Create a backup of the current database.

    Args:
        backup_path: Directory to save the backup file

    Returns:
        True if successful, False otherwise
    """
    try:
        backup_path = Path(backup_path)
        backup_path.mkdir(parents=True, exist_ok=True)

        # Create a timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"timetrack_backup_{timestamp}.db"

        if DATABASE_PATH.exists():
            shutil.copy2(DATABASE_PATH, backup_file)
            return True
        return False
    except Exception as e:
        print(f"Error backing up database: {e}")
        return False


def get_backup_filename() -> str:
    """Get a timestamped backup filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"timetrack_backup_{timestamp}.db"


# Load the configured data directory on module import
DATA_DIR = _load_data_directory()
DATA_DIR.mkdir(exist_ok=True)  # Create folder if it doesn't exist
DATABASE_PATH = DATA_DIR / "timetrack.db"


# =============================================================================
# SCHEMA MIGRATION
# =============================================================================

def _get_schema_version(conn: sqlite3.Connection) -> int:
    """Get current schema version from database."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        return row["version"] if row else 0
    except sqlite3.OperationalError:
        return 0


def _set_schema_version(conn: sqlite3.Connection, version: int):
    """Update schema version."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("DELETE FROM schema_version")
    cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def _migrate_database(conn: sqlite3.Connection):
    """Run necessary migrations."""
    current_version = _get_schema_version(conn)

    if current_version < 1:
        cursor = conn.cursor()

        # Add priority column to projects (default 3 = medium)
        try:
            cursor.execute("""
                ALTER TABLE projects
                ADD COLUMN priority INTEGER DEFAULT 3
            """)
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")

        # Create project_tags junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_tags (
                project_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, tag_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_tags_project ON project_tags(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_tags_tag ON project_tags(tag_id)")

        _set_schema_version(conn, 1)
        conn.commit()

    if current_version < 2:
        cursor = conn.cursor()

        # Add is_background column to projects (default 0 = regular project)
        try:
            cursor.execute("""
                ALTER TABLE projects
                ADD COLUMN is_background INTEGER DEFAULT 0
            """)
        except sqlite3.OperationalError:
            pass  # Column already exists

        _set_schema_version(conn, 2)
        conn.commit()

    if current_version < 3:
        cursor = conn.cursor()

        # Add pause-related columns to sessions
        try:
            cursor.execute("""
                ALTER TABLE sessions
                ADD COLUMN is_paused INTEGER DEFAULT 0
            """)
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("""
                ALTER TABLE sessions
                ADD COLUMN paused_seconds INTEGER DEFAULT 0
            """)
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("""
                ALTER TABLE sessions
                ADD COLUMN pause_started_at TEXT
            """)
        except sqlite3.OperationalError:
            pass  # Column already exists

        _set_schema_version(conn, 3)
        conn.commit()

    if current_version < 4:
        cursor = conn.cursor()

        # Create settings table for app preferences (e.g., theme)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        _set_schema_version(conn, 4)
        conn.commit()

    if current_version < 5:
        cursor = conn.cursor()

        # Create pause_events table to track individual pause/resume events
        # This enables splitting sessions into discrete segments when stopped
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pause_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_time TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pause_events_session ON pause_events(session_id)")

        _set_schema_version(conn, 5)
        conn.commit()


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

@contextmanager
def get_connection():
    """
    Context manager for database connections.
    Ensures connection is closed even if an exception occurs.

    sqlite3.connect() creates the file if it doesn't exist.
    The row_factory setting makes query results behave like dictionaries
    instead of plain tuples, so you can access columns by name.

    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            # ... do stuff
    """
    conn = sqlite3.connect(DATABASE_PATH)
    # Row factory controls how rows are returned
    # sqlite3.Row allows both index access (row[0]) and name access (row["column"])
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """
    Create tables if they don't already exist.

    Called once at app startup. The IF NOT EXISTS clause makes this
    idempotent—safe to call multiple times without errors or data loss.

    SQL primer for the syntax below:
    - INTEGER PRIMARY KEY: Auto-incrementing unique ID
    - TEXT: String data
    - NOT NULL: This column cannot be empty
    - UNIQUE: No two rows can have the same value
    - DEFAULT: Value used if none provided
    """
    with get_connection() as conn:
        # cursor() creates a cursor object for executing SQL
        cursor = conn.cursor()

        # Triple-quoted strings for multi-line SQL
        # executescript() runs multiple SQL statements separated by semicolons
        cursor.executescript("""
            -- Projects table: named categories for time tracking
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            -- Sessions table: individual time blocks
            -- Note: We store times as TEXT in ISO format
            -- SQLite doesn't have a native datetime type, but TEXT works fine
            -- ISO format (YYYY-MM-DD HH:MM:SS) sorts correctly as text
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                notes TEXT DEFAULT ''
            );

            -- Index speeds up queries that filter by project_name
            -- Like a book index—lets the database jump to relevant rows
            CREATE INDEX IF NOT EXISTS idx_sessions_project
                ON sessions(project_name);

            -- Index for time-range queries (today, this week, etc.)
            CREATE INDEX IF NOT EXISTS idx_sessions_start_time
                ON sessions(start_time);
        """)

        # commit() saves changes to disk
        # Without this, changes exist only in memory and are lost on close
        conn.commit()

        # Run migrations for new features
        _migrate_database(conn)

    # Split any existing sessions that span midnight
    split_sessions_at_midnight()


# =============================================================================
# SETTINGS OPERATIONS
# =============================================================================

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a setting value from the database.

    Args:
        key: Setting key name
        default: Value to return if key not found

    Returns:
        Setting value or default
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    """
    Set a setting value in the database.

    Args:
        key: Setting key name
        value: Value to store
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        """, (key, value))
        conn.commit()


# =============================================================================
# PROJECT OPERATIONS
# =============================================================================

def create_project(name: str, priority: int = 3, tags: list[str] = None, is_background: bool = False) -> Project:
    """
    Create a new project with the given name.

    Args:
        name: Human-readable project name (e.g., "Job Search")
        priority: Priority level 1-5 (default 3), ignored for background tasks
        tags: List of tag names to apply, ignored for background tasks
        is_background: If True, create as a background task (no priority/tags)

    Returns:
        Project object with the assigned database ID

    Raises:
        sqlite3.IntegrityError: If project name already exists
        ValueError: If priority is not between 1 and 5 (for regular projects)
    """
    # Background tasks don't have priority or tags
    if is_background:
        priority = 3  # Default, but not displayed/used
        tags = None
    elif not 1 <= priority <= 5:
        raise ValueError("Priority must be between 1 and 5")

    with get_connection() as conn:
        cursor = conn.cursor()

        # The ? is a parameter placeholder
        # NEVER use f-strings or string concatenation for SQL values
        # That creates SQL injection vulnerabilities
        # ? placeholders are automatically escaped and safe
        cursor.execute(
            "INSERT INTO projects (name, priority, is_background) VALUES (?, ?, ?)",
            (name, priority, 1 if is_background else 0)
        )

        conn.commit()

        # lastrowid gives us the auto-generated ID of the inserted row
        project_id = cursor.lastrowid

    # Add tags if provided (only for regular projects)
    if tags and not is_background:
        for tag_name in tags:
            add_tag_to_project(project_id, tag_name)

    return Project(id=project_id, name=name, priority=priority, tags=tags or [], is_background=is_background)


def get_project(name: str) -> Optional[Project]:
    """
    Fetch a project by name, including tags.

    Returns None if no project with that name exists.
    The Optional type hint means "Project or None".
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, created_at, priority, is_background FROM projects WHERE name = ?",
            (name,)
        )

        # fetchone() returns one row or None if no results
        row = cursor.fetchone()

        if row is None:
            return None

        is_background = bool(row["is_background"]) if row["is_background"] is not None else False
        tags = get_project_tags(row["id"]) if not is_background else []

        # Convert the database row to a Project object
        # row["column"] works because we set row_factory earlier
        return Project(
            id=row["id"],
            name=row["name"],
            # Parse the ISO timestamp string back into a datetime object
            created_at=datetime.fromisoformat(row["created_at"]),
            priority=row["priority"] if row["priority"] is not None else 3,
            tags=tags,
            is_background=is_background
        )


def get_or_create_project(name: str) -> Project:
    """
    Get existing project or create it if it doesn't exist.
    
    This is a convenience function—you don't have to manually check
    if a project exists before using it.
    """
    project = get_project(name)
    if project is None:
        project = create_project(name)
    return project


def list_projects(tag: Optional[str] = None, min_priority: Optional[int] = None, is_background: Optional[bool] = None) -> list[Project]:
    """
    Get all projects, with optional filtering.

    Args:
        tag: Filter to projects with this tag (only applies to regular projects)
        min_priority: Filter to projects with priority <= this value (1 is highest)
        is_background: If True, only background tasks; if False, only regular projects; if None, all

    Returns:
        List of Project objects (may be empty)
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        query = "SELECT id, name, created_at, priority, is_background FROM projects"
        params: list = []

        conditions = []
        if min_priority:
            conditions.append("priority <= ?")
            params.append(min_priority)

        if is_background is not None:
            conditions.append("is_background = ?")
            params.append(1 if is_background else 0)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY is_background ASC, priority ASC, name COLLATE NOCASE"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Fetch ALL project-tag associations in a single query
        cursor.execute("""
            SELECT pt.project_id, t.name
            FROM project_tags pt
            JOIN tags t ON t.id = pt.tag_id
        """)
        tag_rows = cursor.fetchall()

    # Build a dictionary mapping project_id -> list of tag names
    project_tags_map: dict[int, list[str]] = {}
    for tag_row in tag_rows:
        project_id = tag_row["project_id"]
        if project_id not in project_tags_map:
            project_tags_map[project_id] = []
        project_tags_map[project_id].append(tag_row["name"])

    projects = []
    for row in rows:
        row_is_background = bool(row["is_background"]) if row["is_background"] is not None else False
        # Background tasks have empty tag lists; regular projects look up from the map
        tags = [] if row_is_background else project_tags_map.get(row["id"], [])

        # Filter by tag if specified (only applies to regular projects)
        if tag and not row_is_background and tag.lower() not in [t.lower() for t in tags]:
            continue

        projects.append(Project(
            id=row["id"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            priority=row["priority"] if row["priority"] is not None else 3,
            tags=tags,
            is_background=row_is_background
        ))

    return projects


# =============================================================================
# TAG OPERATIONS
# =============================================================================

def create_tag(name: str) -> Tag:
    """Create a new tag."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("INSERT INTO tags (name) VALUES (?)", (name.strip(),))
        conn.commit()

        tag_id = cursor.lastrowid

    return Tag(id=tag_id, name=name.strip())


def get_tag(name: str) -> Optional[Tag]:
    """Get tag by name (case-insensitive)."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, created_at FROM tags WHERE name = ? COLLATE NOCASE",
            (name,)
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return Tag(
            id=row["id"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"])
        )


def get_or_create_tag(name: str) -> Tag:
    """Get existing tag or create if doesn't exist."""
    tag = get_tag(name)
    if tag is None:
        tag = create_tag(name)
    return tag


def list_tags() -> list[Tag]:
    """Get all tags, sorted alphabetically."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, created_at FROM tags ORDER BY name COLLATE NOCASE"
        )

        rows = cursor.fetchall()

        return [
            Tag(
                id=row["id"],
                name=row["name"],
                created_at=datetime.fromisoformat(row["created_at"])
            )
            for row in rows
        ]


def get_project_tags(project_id: int) -> list[str]:
    """Get all tag names for a project."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.name
            FROM tags t
            JOIN project_tags pt ON t.id = pt.tag_id
            WHERE pt.project_id = ?
            ORDER BY t.name COLLATE NOCASE
        """, (project_id,))

        rows = cursor.fetchall()

        return [row["name"] for row in rows]


def add_tag_to_project(project_id: int, tag_name: str) -> bool:
    """
    Add a tag to a project. Creates tag if it doesn't exist.

    Returns True if tag was added, False if already existed.
    """
    tag = get_or_create_tag(tag_name)

    with get_connection() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO project_tags (project_id, tag_id) VALUES (?, ?)",
                (project_id, tag.id)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already tagged


def remove_tag_from_project(project_id: int, tag_name: str) -> bool:
    """
    Remove a tag from a project.

    Returns True if tag was removed, False if project didn't have that tag.
    """
    tag = get_tag(tag_name)
    if tag is None:
        return False

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM project_tags WHERE project_id = ? AND tag_id = ?",
            (project_id, tag.id)
        )

        conn.commit()
        return cursor.rowcount > 0


def get_projects_by_tag(tag_name: str) -> list[Project]:
    """Get all projects that have a specific tag (excludes background tasks)."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.id, p.name, p.created_at, p.priority, p.is_background
            FROM projects p
            JOIN project_tags pt ON p.id = pt.project_id
            JOIN tags t ON pt.tag_id = t.id
            WHERE t.name = ? COLLATE NOCASE AND (p.is_background = 0 OR p.is_background IS NULL)
            ORDER BY p.name COLLATE NOCASE
        """, (tag_name,))

        rows = cursor.fetchall()

    projects = []
    for row in rows:
        tags = get_project_tags(row["id"])
        projects.append(Project(
            id=row["id"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            priority=row["priority"] if row["priority"] is not None else 3,
            tags=tags,
            is_background=False
        ))

    return projects


def update_project_priority(project_name: str, priority: int) -> Optional[Project]:
    """
    Update a project's priority.

    Returns updated Project or None if project not found.
    """
    if not 1 <= priority <= 5:
        raise ValueError("Priority must be between 1 and 5")

    project = get_project(project_name)
    if project is None:
        return None

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE projects SET priority = ? WHERE id = ?",
            (priority, project.id)
        )

        conn.commit()

    project.priority = priority
    return project


def rename_project(old_name: str, new_name: str) -> Optional[Project]:
    """
    Rename a project and update all associated sessions.

    Args:
        old_name: Current name of the project
        new_name: New name for the project

    Returns:
        Updated Project or None if project not found.

    Raises:
        sqlite3.IntegrityError: If new_name already exists
    """
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Project name cannot be empty")

    project = get_project(old_name)
    if project is None:
        return None

    with get_connection() as conn:
        cursor = conn.cursor()

        # Update project name
        cursor.execute(
            "UPDATE projects SET name = ? WHERE id = ?",
            (new_name, project.id)
        )

        # Update all sessions that reference this project
        cursor.execute(
            "UPDATE sessions SET project_name = ? WHERE project_name = ?",
            (new_name, old_name)
        )

        conn.commit()

    project.name = new_name
    return project


def delete_project(project_name: str, delete_sessions: bool = False) -> bool:
    """
    Delete a project by name.

    Args:
        project_name: Name of the project to delete
        delete_sessions: If True, also delete all sessions associated with the project.
                        If False, sessions are kept but become orphaned.

    Returns:
        True if project was deleted, False if project not found.
    """
    project = get_project(project_name)
    if project is None:
        return False

    with get_connection() as conn:
        cursor = conn.cursor()

        # Delete associated sessions if requested
        if delete_sessions:
            cursor.execute(
                "DELETE FROM sessions WHERE project_name = ?",
                (project_name,)
            )

        # Delete project-tag associations (handled by CASCADE, but explicit for clarity)
        cursor.execute(
            "DELETE FROM project_tags WHERE project_id = ?",
            (project.id,)
        )

        # Delete the project
        cursor.execute(
            "DELETE FROM projects WHERE id = ?",
            (project.id,)
        )

        conn.commit()
        return cursor.rowcount > 0


# =============================================================================
# SESSION OPERATIONS
# =============================================================================

def start_session(project_name: str) -> Session:
    """
    Begin a new tracking session for the given project.

    This creates the project if it doesn't exist (convenience behavior).

    Args:
        project_name: Which project to track time for

    Returns:
        The newly created Session object
    """
    # Ensure project exists (creates if needed)
    get_or_create_project(project_name)

    # Record current time as the start
    now = datetime.now()

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO sessions (project_name, start_time) VALUES (?, ?)",
            (project_name, now.isoformat())  # isoformat() converts datetime to string
        )

        conn.commit()
        session_id = cursor.lastrowid

    return Session(
        id=session_id,
        project_name=project_name,
        start_time=now
    )


def get_active_session() -> Optional[Session]:
    """
    Find the currently running session, if any.

    A session is "active" if end_time is NULL (not yet stopped).
    We only expect one active session at a time, but if somehow
    there are multiple, we return the most recent one.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # WHERE end_time IS NULL finds sessions that haven't been stopped
        # ORDER BY start_time DESC + LIMIT 1 gets the most recent one
        cursor.execute("""
            SELECT id, project_name, start_time, end_time, notes,
                   is_paused, paused_seconds, pause_started_at
            FROM sessions
            WHERE end_time IS NULL
            ORDER BY start_time DESC
            LIMIT 1
        """)

        row = cursor.fetchone()

        if row is None:
            return None

        return Session(
            id=row["id"],
            project_name=row["project_name"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=None,
            notes=row["notes"] or "",
            is_paused=bool(row["is_paused"]) if row["is_paused"] is not None else False,
            paused_seconds=row["paused_seconds"] or 0,
            pause_started_at=datetime.fromisoformat(row["pause_started_at"]) if row["pause_started_at"] else None
        )


def get_active_sessions() -> list[Session]:
    """
    Get ALL currently running sessions.

    Returns:
        List of Session objects with end_time IS NULL, ordered by start_time DESC
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_name, start_time, end_time, notes,
                   is_paused, paused_seconds, pause_started_at
            FROM sessions
            WHERE end_time IS NULL
            ORDER BY start_time DESC
        """)

        rows = cursor.fetchall()

        return [
            Session(
                id=row["id"],
                project_name=row["project_name"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=None,
                notes=row["notes"] or "",
                is_paused=bool(row["is_paused"]) if row["is_paused"] is not None else False,
                paused_seconds=row["paused_seconds"] or 0,
                pause_started_at=datetime.fromisoformat(row["pause_started_at"]) if row["pause_started_at"] else None
            )
            for row in rows
        ]


def get_active_session_by_project(project_name: str) -> Optional[Session]:
    """
    Find active session for a specific project.

    Args:
        project_name: Project to search for (case-sensitive)

    Returns:
        Session if found, None otherwise
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_name, start_time, end_time, notes,
                   is_paused, paused_seconds, pause_started_at
            FROM sessions
            WHERE end_time IS NULL AND project_name = ?
            ORDER BY start_time DESC
            LIMIT 1
        """, (project_name,))

        row = cursor.fetchone()

        if row is None:
            return None

        return Session(
            id=row["id"],
            project_name=row["project_name"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=None,
            notes=row["notes"] or "",
            is_paused=bool(row["is_paused"]) if row["is_paused"] is not None else False,
            paused_seconds=row["paused_seconds"] or 0,
            pause_started_at=datetime.fromisoformat(row["pause_started_at"]) if row["pause_started_at"] else None
        )


def get_session_by_id(session_id: int) -> Optional[Session]:
    """
    Fetch a single session by its ID.

    Args:
        session_id: The session ID to look up

    Returns:
        Session object if found, None otherwise
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_name, start_time, end_time, notes,
                   is_paused, paused_seconds, pause_started_at
            FROM sessions
            WHERE id = ?
        """, (session_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        return Session(
            id=row["id"],
            project_name=row["project_name"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            notes=row["notes"] or "",
            is_paused=bool(row["is_paused"]) if row["is_paused"] is not None else False,
            paused_seconds=row["paused_seconds"] or 0,
            pause_started_at=datetime.fromisoformat(row["pause_started_at"]) if row["pause_started_at"] else None
        )


def stop_session(project_name: Optional[str] = None, notes: str = "") -> list[Session]:
    """
    Stop an active session, splitting into multiple sessions for each active period.

    When a session has been paused and resumed multiple times, this function
    creates separate session records for each active work period. Notes are
    applied only to the final segment.

    Args:
        project_name: If provided, stop session for this specific project.
                     If None, stop the most recent active session.
        notes: Optional description of what you worked on (applied to final segment)

    Returns:
        List of created Session objects (one per active period), or empty list
        if no matching session was active
    """
    # Find the target session
    if project_name:
        active = get_active_session_by_project(project_name)
    else:
        active = get_active_session()

    if active is None:
        return []

    now = datetime.now()

    # Get pause events to determine if we need to split
    events = get_pause_events(active.id)

    # If no pause events, use simple behavior (single session)
    if not events:
        # If session was paused (but no events - legacy), accumulate final paused time
        final_paused_seconds = active.paused_seconds
        if active.is_paused and active.pause_started_at:
            additional_paused = int((now - active.pause_started_at).total_seconds())
            final_paused_seconds += additional_paused

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET end_time = ?, notes = ?, is_paused = 0, pause_started_at = NULL, paused_seconds = ?
                WHERE id = ?
            """, (now.isoformat(), notes, final_paused_seconds, active.id))
            conn.commit()

        active.end_time = now
        active.notes = notes
        active.is_paused = False
        active.pause_started_at = None
        active.paused_seconds = final_paused_seconds

        split_sessions_at_midnight()
        return [active]

    # Compute active periods from pause events
    periods = get_active_periods(active, end_time=now)

    # If session was paused at stop time (currently paused), the last period
    # already ends at the pause time, which is correct behavior

    # For sessions with a single period (paused but never resumed)
    if len(periods) <= 1:
        # Single period or no periods - simple update
        period_end = periods[0][1] if periods else now

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET end_time = ?, notes = ?, is_paused = 0, pause_started_at = NULL, paused_seconds = 0
                WHERE id = ?
            """, (period_end.isoformat(), notes, active.id))

            # Clean up pause events
            cursor.execute("DELETE FROM pause_events WHERE session_id = ?", (active.id,))
            conn.commit()

        active.end_time = period_end
        active.notes = notes
        active.is_paused = False
        active.pause_started_at = None
        active.paused_seconds = 0

        split_sessions_at_midnight()
        return [active]

    # Multiple periods - create separate sessions for each
    created_sessions = []

    with get_connection() as conn:
        cursor = conn.cursor()

        for i, (period_start, period_end) in enumerate(periods):
            is_final = (i == len(periods) - 1)
            segment_notes = notes if is_final else ""

            if i == 0:
                # Update original session to be first period
                cursor.execute("""
                    UPDATE sessions
                    SET end_time = ?, notes = ?, is_paused = 0,
                        pause_started_at = NULL, paused_seconds = 0
                    WHERE id = ?
                """, (period_end.isoformat(), segment_notes, active.id))

                created_sessions.append(Session(
                    id=active.id,
                    project_name=active.project_name,
                    start_time=period_start,
                    end_time=period_end,
                    notes=segment_notes,
                    is_paused=False,
                    paused_seconds=0,
                    pause_started_at=None
                ))
            else:
                # Create new session for subsequent periods
                cursor.execute("""
                    INSERT INTO sessions (project_name, start_time, end_time, notes,
                                          is_paused, paused_seconds, pause_started_at)
                    VALUES (?, ?, ?, ?, 0, 0, NULL)
                """, (active.project_name, period_start.isoformat(),
                      period_end.isoformat(), segment_notes))

                new_session_id = cursor.lastrowid
                created_sessions.append(Session(
                    id=new_session_id,
                    project_name=active.project_name,
                    start_time=period_start,
                    end_time=period_end,
                    notes=segment_notes,
                    is_paused=False,
                    paused_seconds=0,
                    pause_started_at=None
                ))

        # Clean up pause events
        cursor.execute("DELETE FROM pause_events WHERE session_id = ?", (active.id,))
        conn.commit()

    split_sessions_at_midnight()
    return created_sessions


def stop_all_sessions(notes: str = "") -> list[Session]:
    """
    Stop ALL currently active sessions, splitting each into segments if needed.

    Args:
        notes: Optional notes applied to final segment of each stopped session

    Returns:
        List of all created Session objects (may be more than active sessions
        if some sessions were split into multiple segments)
    """
    active_sessions = get_active_sessions()

    if not active_sessions:
        return []

    all_created_sessions = []

    # Stop each session using stop_session to handle splitting
    for session in active_sessions:
        created = stop_session(project_name=session.project_name, notes=notes)
        all_created_sessions.extend(created)

    return all_created_sessions


def pause_session(session_id: int) -> Optional[Session]:
    """
    Pause an active session.

    Args:
        session_id: ID of the session to pause

    Returns:
        The paused Session, or None if session not found or already paused
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # First check if session exists and is active (not ended) and not already paused
        cursor.execute("""
            SELECT id, project_name, start_time, end_time, notes,
                   is_paused, paused_seconds, pause_started_at
            FROM sessions
            WHERE id = ? AND end_time IS NULL
        """, (session_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        # Already paused
        if row["is_paused"]:
            return Session(
                id=row["id"],
                project_name=row["project_name"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=None,
                notes=row["notes"] or "",
                is_paused=True,
                paused_seconds=row["paused_seconds"] or 0,
                pause_started_at=datetime.fromisoformat(row["pause_started_at"]) if row["pause_started_at"] else None
            )

        now = datetime.now()

        # Record the pause event for segment splitting
        record_pause_event(session_id, 'pause')

        cursor.execute("""
            UPDATE sessions
            SET is_paused = 1, pause_started_at = ?
            WHERE id = ?
        """, (now.isoformat(), session_id))

        conn.commit()

        return Session(
            id=row["id"],
            project_name=row["project_name"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=None,
            notes=row["notes"] or "",
            is_paused=True,
            paused_seconds=row["paused_seconds"] or 0,
            pause_started_at=now
        )


def resume_session(session_id: int) -> Optional[Session]:
    """
    Resume a paused session.

    Args:
        session_id: ID of the session to resume

    Returns:
        The resumed Session, or None if session not found or not paused
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # First check if session exists and is paused
        cursor.execute("""
            SELECT id, project_name, start_time, end_time, notes,
                   is_paused, paused_seconds, pause_started_at
            FROM sessions
            WHERE id = ? AND end_time IS NULL
        """, (session_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        # Not paused
        if not row["is_paused"]:
            return Session(
                id=row["id"],
                project_name=row["project_name"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=None,
                notes=row["notes"] or "",
                is_paused=False,
                paused_seconds=row["paused_seconds"] or 0,
                pause_started_at=None
            )

        now = datetime.now()

        # Record the resume event for segment splitting
        record_pause_event(session_id, 'resume')

        pause_started = datetime.fromisoformat(row["pause_started_at"]) if row["pause_started_at"] else now
        additional_paused = int((now - pause_started).total_seconds())
        new_paused_seconds = (row["paused_seconds"] or 0) + additional_paused

        cursor.execute("""
            UPDATE sessions
            SET is_paused = 0, pause_started_at = NULL, paused_seconds = ?
            WHERE id = ?
        """, (new_paused_seconds, session_id))

        conn.commit()

        return Session(
            id=row["id"],
            project_name=row["project_name"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=None,
            notes=row["notes"] or "",
            is_paused=False,
            paused_seconds=new_paused_seconds,
            pause_started_at=None
        )


# =============================================================================
# PAUSE EVENT OPERATIONS
# =============================================================================

def record_pause_event(session_id: int, event_type: str) -> PauseEvent:
    """
    Record a pause or resume event for a session.

    Args:
        session_id: ID of the session
        event_type: Either 'pause' or 'resume'

    Returns:
        The created PauseEvent object
    """
    now = datetime.now()

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO pause_events (session_id, event_type, event_time)
            VALUES (?, ?, ?)
        """, (session_id, event_type, now.isoformat()))

        conn.commit()
        event_id = cursor.lastrowid

    return PauseEvent(
        id=event_id,
        session_id=session_id,
        event_type=event_type,
        event_time=now
    )


def get_pause_events(session_id: int) -> list[PauseEvent]:
    """
    Get all pause/resume events for a session, ordered by event time.

    Args:
        session_id: ID of the session

    Returns:
        List of PauseEvent objects in chronological order
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, session_id, event_type, event_time
            FROM pause_events
            WHERE session_id = ?
            ORDER BY event_time ASC
        """, (session_id,))

        rows = cursor.fetchall()

        return [
            PauseEvent(
                id=row["id"],
                session_id=row["session_id"],
                event_type=row["event_type"],
                event_time=datetime.fromisoformat(row["event_time"])
            )
            for row in rows
        ]


def get_active_periods(session: Session, end_time: Optional[datetime] = None) -> list[tuple[datetime, datetime]]:
    """
    Compute active work periods from session start_time and pause_events.

    Args:
        session: The session to compute periods for
        end_time: The end time to use (defaults to now if session is active)

    Returns:
        List of (start, end) tuples representing active work periods
    """
    if session.start_time is None:
        return []

    events = get_pause_events(session.id)
    final_end = end_time or (session.end_time if session.end_time else datetime.now())

    if not events:
        # No pause events - single continuous period
        return [(session.start_time, final_end)]

    periods = []
    current_start = session.start_time

    for event in events:
        if event.event_type == 'pause':
            # End current active period at pause time
            if current_start is not None:
                periods.append((current_start, event.event_time))
                current_start = None
        elif event.event_type == 'resume':
            # Start new active period at resume time
            current_start = event.event_time

    # If we're still in an active period (not paused at the end), close it
    if current_start is not None:
        periods.append((current_start, final_end))

    return periods


def delete_pause_events(session_id: int) -> int:
    """
    Delete all pause events for a session.

    Args:
        session_id: ID of the session

    Returns:
        Number of events deleted
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM pause_events WHERE session_id = ?", (session_id,))
        deleted = cursor.rowcount

        conn.commit()

    return deleted


def log_session(
    project_name: str,
    duration: timedelta,
    notes: str = "",
    date: Optional[datetime] = None
) -> Session:
    """
    Add a completed session retroactively.

    Use this when you forgot to start the timer but want to log time anyway.

    Args:
        project_name: Which project to attribute time to
        duration: How long you worked (as timedelta)
        notes: What you worked on
        date: When the session ended (defaults to now)

    Returns:
        The created Session object
    """
    get_or_create_project(project_name)

    # Default to current time if no date specified
    end_time = date if date else datetime.now()

    # Calculate start time by subtracting duration from end time
    start_time = end_time - duration

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sessions (project_name, start_time, end_time, notes)
            VALUES (?, ?, ?, ?)
        """, (project_name, start_time.isoformat(), end_time.isoformat(), notes))

        conn.commit()
        session_id = cursor.lastrowid

    session = Session(
        id=session_id,
        project_name=project_name,
        start_time=start_time,
        end_time=end_time,
        notes=notes
    )

    # Split any sessions that crossed midnight boundaries
    split_sessions_at_midnight()

    return session


def get_sessions(
    project_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50
) -> list[Session]:
    """
    Query sessions with optional filters.

    All filters are optional and can be combined:
    - project_name: Only sessions for this project
    - start_date: Only sessions that started on or after this time
    - end_date: Only sessions that started before this time
    - limit: Maximum number of results

    Returns sessions in reverse chronological order (newest first).
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Build query dynamically based on which filters are provided
        # Start with base query
        query = """
            SELECT id, project_name, start_time, end_time, notes
            FROM sessions
            WHERE end_time IS NOT NULL
        """
        # We exclude active sessions (end_time IS NOT NULL) because
        # they're incomplete and would skew reports

        # Params list holds values for ? placeholders
        params: list = []

        # Add filter clauses conditionally
        if project_name:
            query += " AND project_name = ?"
            params.append(project_name)

        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND start_time < ?"
            params.append(end_date.isoformat())

        # Order by most recent first, cap results
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            Session(
                id=row["id"],
                project_name=row["project_name"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                notes=row["notes"] or ""
            )
            for row in rows
        ]


def get_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> dict[str, int]:
    """
    Get total seconds tracked per project within a date range.

    Args:
        start_date: Count sessions starting on or after this time
        end_date: Count sessions starting before this time

    Returns:
        Dictionary mapping project names to total seconds
        Example: {"Job Search": 7200, "Brewing": 3600}
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # This query does the aggregation in SQL, which is more efficient
        # than fetching all sessions and summing in Python
        #
        # strftime('%s', ...) converts timestamp to Unix epoch seconds
        # Subtracting start from end gives duration in seconds
        # SUM() adds up all durations for each project
        # GROUP BY creates one row per project
        query = """
            SELECT
                project_name,
                SUM(
                    strftime('%s', end_time) - strftime('%s', start_time)
                ) as total_seconds
            FROM sessions
            WHERE end_time IS NOT NULL
        """

        params: list = []

        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND start_time < ?"
            params.append(end_date.isoformat())

        query += " GROUP BY project_name ORDER BY total_seconds DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to dictionary
        # dict comprehension: {key: value for item in iterable}
        return {
            row["project_name"]: int(row["total_seconds"])
            for row in rows
        }


def get_summary_with_priority(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    is_background: Optional[bool] = None
) -> dict[str, dict]:
    """
    Get total seconds tracked per project with priority info.

    Args:
        start_date: Count sessions starting on or after this time
        end_date: Count sessions starting before this time
        is_background: If True, only background tasks; if False, only regular projects; if None, all

    Returns:
        Dictionary mapping project names to {seconds, priority, is_background}
        Example: {"Job Search": {"seconds": 7200, "priority": 2, "is_background": False}}
        Results are ordered by priority ASC, then total_seconds DESC.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                s.project_name,
                COALESCE(p.priority, 3) as priority,
                COALESCE(p.is_background, 0) as is_background,
                SUM(
                    strftime('%s', s.end_time) - strftime('%s', s.start_time)
                ) as total_seconds
            FROM sessions s
            LEFT JOIN projects p ON s.project_name = p.name
            WHERE s.end_time IS NOT NULL
        """

        params: list = []

        if start_date:
            query += " AND s.start_time >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND s.start_time < ?"
            params.append(end_date.isoformat())

        if is_background is not None:
            query += " AND (p.is_background = ? OR (p.is_background IS NULL AND ? = 0))"
            params.append(1 if is_background else 0)
            params.append(1 if is_background else 0)

        query += " GROUP BY s.project_name ORDER BY priority ASC, total_seconds DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Use a regular dict to preserve order (Python 3.7+)
        result = {}
        for row in rows:
            result[row["project_name"]] = {
                "seconds": int(row["total_seconds"]),
                "priority": row["priority"],
                "is_background": bool(row["is_background"])
            }
        return result


def get_summary_by_day(
    start_date: datetime,
    end_date: datetime,
    is_background: Optional[bool] = None
) -> dict[str, dict]:
    """
    Get per-project, per-day breakdown of time tracked.

    Args:
        start_date: Count sessions starting on or after this time
        end_date: Count sessions starting before this time
        is_background: If True, only background tasks; if False, only regular projects; if None, all

    Returns:
        Dictionary with structure:
        {project_name: {"priority": int, "days": {date_str: seconds}, "total": int, "is_background": bool}}
        Results are ordered by priority ASC, then total time DESC.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                s.project_name,
                COALESCE(p.priority, 3) as priority,
                COALESCE(p.is_background, 0) as is_background,
                date(s.start_time) as session_date,
                SUM(
                    strftime('%s', s.end_time) - strftime('%s', s.start_time)
                ) as total_seconds
            FROM sessions s
            LEFT JOIN projects p ON s.project_name = p.name
            WHERE s.end_time IS NOT NULL
              AND s.start_time >= ?
              AND s.start_time < ?
        """

        params: list = [start_date.isoformat(), end_date.isoformat()]

        if is_background is not None:
            query += " AND (p.is_background = ? OR (p.is_background IS NULL AND ? = 0))"
            params.append(1 if is_background else 0)
            params.append(1 if is_background else 0)

        query += " GROUP BY s.project_name, date(s.start_time)"

        cursor.execute(query, params)
        rows = cursor.fetchall()

    # Build nested structure
    result: dict[str, dict] = {}
    for row in rows:
        project = row["project_name"]
        if project not in result:
            result[project] = {
                "priority": row["priority"],
                "is_background": bool(row["is_background"]),
                "days": {},
                "total": 0
            }
        result[project]["days"][row["session_date"]] = int(row["total_seconds"])
        result[project]["total"] += int(row["total_seconds"])

    # Sort by priority ASC, then total DESC
    sorted_result = dict(
        sorted(result.items(), key=lambda x: (x[1]["priority"], -x[1]["total"]))
    )

    return sorted_result


def get_summary_by_tag(
    start_date: datetime,
    end_date: datetime
) -> dict[str, dict]:
    """
    Get per-tag, per-project, per-day breakdown of time tracked.

    Projects with multiple tags will appear under each tag group.
    Untagged projects appear under "Untagged" at the end.

    Args:
        start_date: Count sessions starting on or after this time
        end_date: Count sessions starting before this time

    Returns:
        Dictionary with structure:
        {
            tag_name: {
                "projects": {
                    project_name: {
                        "days": {date_str: seconds},
                        "total": int,
                        "has_multiple_tags": bool
                    }
                },
                "total": int
            }
        }
        Results are ordered by tag name alphabetically, with "Untagged" at the end.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Get all projects that are NOT background tasks with their tags
        cursor.execute("""
            SELECT p.id, p.name
            FROM projects p
            WHERE p.is_background = 0 OR p.is_background IS NULL
        """)
        project_rows = cursor.fetchall()

        # Get all tags for each project
        cursor.execute("""
            SELECT pt.project_id, t.name as tag_name
            FROM project_tags pt
            JOIN tags t ON t.id = pt.tag_id
        """)
        tag_rows = cursor.fetchall()

        # Build project -> tags mapping
        project_tags: dict[int, list[str]] = {}
        for row in tag_rows:
            pid = row["project_id"]
            if pid not in project_tags:
                project_tags[pid] = []
            project_tags[pid].append(row["tag_name"])

        # Build project_id -> name mapping
        project_id_to_name: dict[int, str] = {row["id"]: row["name"] for row in project_rows}

        # Get per-day session data for regular projects
        cursor.execute("""
            SELECT
                s.project_name,
                date(s.start_time) as session_date,
                SUM(
                    strftime('%s', s.end_time) - strftime('%s', s.start_time)
                ) as total_seconds
            FROM sessions s
            LEFT JOIN projects p ON s.project_name = p.name
            WHERE s.end_time IS NOT NULL
              AND s.start_time >= ?
              AND s.start_time < ?
              AND (p.is_background = 0 OR p.is_background IS NULL)
            GROUP BY s.project_name, date(s.start_time)
        """, (start_date.isoformat(), end_date.isoformat()))

        session_rows = cursor.fetchall()

    # Build project data structure
    project_data: dict[str, dict] = {}
    for row in session_rows:
        project_name = row["project_name"]
        if project_name not in project_data:
            project_data[project_name] = {"days": {}, "total": 0}
        project_data[project_name]["days"][row["session_date"]] = int(row["total_seconds"])
        project_data[project_name]["total"] += int(row["total_seconds"])

    # Build result grouped by tag
    result: dict[str, dict] = {}

    # Get name -> id mapping for looking up tags
    name_to_id = {v: k for k, v in project_id_to_name.items()}

    for project_name, pdata in project_data.items():
        project_id = name_to_id.get(project_name)
        tags = project_tags.get(project_id, []) if project_id else []
        has_multiple_tags = len(tags) > 1

        if not tags:
            # Untagged
            tag_name = "Untagged"
            if tag_name not in result:
                result[tag_name] = {"projects": {}, "total": 0}
            result[tag_name]["projects"][project_name] = {
                "days": pdata["days"].copy(),
                "total": pdata["total"],
                "has_multiple_tags": False
            }
            result[tag_name]["total"] += pdata["total"]
        else:
            # Add to each tag group
            for tag_name in tags:
                if tag_name not in result:
                    result[tag_name] = {"projects": {}, "total": 0}
                result[tag_name]["projects"][project_name] = {
                    "days": pdata["days"].copy(),
                    "total": pdata["total"],
                    "has_multiple_tags": has_multiple_tags
                }
                result[tag_name]["total"] += pdata["total"]

    # Sort tags alphabetically, with Untagged at the end
    sorted_result = {}
    for tag_name in sorted(result.keys(), key=lambda t: (t == "Untagged", t.lower())):
        tag_data = result[tag_name]
        # Sort projects within each tag by total time DESC
        sorted_projects = dict(
            sorted(tag_data["projects"].items(), key=lambda x: -x[1]["total"])
        )
        sorted_result[tag_name] = {
            "projects": sorted_projects,
            "total": tag_data["total"]
        }

    return sorted_result


def split_sessions_at_midnight() -> int:
    """
    Split any completed sessions that span midnight into separate day sessions.

    For each session that starts on day N and ends on day N+1 (or later),
    this function:
    1. Ends the original session at 23:59:59 of day N
    2. Creates new sessions for each subsequent day, starting at 00:00:00

    Returns:
        Number of new sessions created from splits
    """
    splits_created = 0

    with get_connection() as conn:
        cursor = conn.cursor()

        # Find all completed sessions that span midnight
        # date(start_time) != date(end_time) means session crosses at least one midnight
        cursor.execute("""
            SELECT id, project_name, start_time, end_time, notes
            FROM sessions
            WHERE end_time IS NOT NULL
              AND date(start_time) != date(end_time)
        """)

        sessions_to_split = cursor.fetchall()

        for row in sessions_to_split:
            session_id = row["id"]
            project_name = row["project_name"]
            start_time = datetime.fromisoformat(row["start_time"])
            end_time = datetime.fromisoformat(row["end_time"])
            notes = row["notes"] or ""

            # Calculate the end of the first day (23:59:59)
            first_day_end = start_time.replace(hour=23, minute=59, second=59, microsecond=0)

            # Update original session to end at midnight of the first day
            cursor.execute("""
                UPDATE sessions
                SET end_time = ?
                WHERE id = ?
            """, (first_day_end.isoformat(), session_id))

            # Create sessions for each subsequent day
            current_day_start = (start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                                + timedelta(days=1))

            while current_day_start.date() <= end_time.date():
                # Determine the end time for this day's segment
                if current_day_start.date() == end_time.date():
                    # This is the final day - use the actual end time
                    segment_end = end_time
                else:
                    # Not the final day - end at 23:59:59
                    segment_end = current_day_start.replace(hour=23, minute=59, second=59, microsecond=0)

                # Insert new session for this day
                cursor.execute("""
                    INSERT INTO sessions (project_name, start_time, end_time, notes)
                    VALUES (?, ?, ?, ?)
                """, (project_name, current_day_start.isoformat(), segment_end.isoformat(), notes))

                splits_created += 1

                # Move to next day
                current_day_start += timedelta(days=1)

        conn.commit()

    return splits_created


def delete_session(session_id: int) -> bool:
    """
    Delete a session by ID.

    Returns True if a session was deleted, False if ID not found.
    Use with caution—there's no undo.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

        conn.commit()

        # rowcount tells us how many rows were affected
        return cursor.rowcount > 0


def export_sessions_csv(filepath: str):
    """
    Export all completed sessions to a CSV file.

    CSV (Comma-Separated Values) is a simple text format that
    spreadsheet programs like Excel can open.
    """
    import csv  # Standard library CSV writer

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT project_name, start_time, end_time, notes,
                   (strftime('%s', end_time) - strftime('%s', start_time)) as duration_seconds
            FROM sessions
            WHERE end_time IS NOT NULL
            ORDER BY start_time
        """)

        rows = cursor.fetchall()

    # Open file for writing
    # newline='' is required for csv module on Windows to avoid blank rows
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header row
        writer.writerow([
            "Project",
            "Start Time",
            "End Time",
            "Duration (seconds)",
            "Duration (hours)",
            "Notes"
        ])

        # Write data rows
        for row in rows:
            secs = int(row["duration_seconds"])
            hours = round(secs / 3600, 2)  # Convert to hours, 2 decimal places
            writer.writerow([
                row["project_name"],
                row["start_time"],
                row["end_time"],
                secs,
                hours,
                row["notes"]
            ])
