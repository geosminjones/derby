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

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Import our data models
from models import Project, Session, Tag

# Use a dedicated folder in the user's home directory
DATA_DIR = Path.home() / ".timetrack"
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


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

def get_connection() -> sqlite3.Connection:
    """
    Create and return a database connection.
    
    sqlite3.connect() creates the file if it doesn't exist.
    This is called at the start of most operations.
    
    The row_factory setting makes query results behave like dictionaries
    instead of plain tuples, so you can access columns by name.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    
    # Row factory controls how rows are returned
    # sqlite3.Row allows both index access (row[0]) and name access (row["column"])
    conn.row_factory = sqlite3.Row
    
    return conn


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
    conn = get_connection()
    
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

    # Always close connections when done
    # Leaving connections open can cause locking issues
    conn.close()


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

    conn = get_connection()
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

    conn.close()

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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, created_at, priority, is_background FROM projects WHERE name = ?",
        (name,)
    )

    # fetchone() returns one row or None if no results
    row = cursor.fetchone()
    conn.close()

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
    conn = get_connection()
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
    conn.close()

    projects = []
    for row in rows:
        row_is_background = bool(row["is_background"]) if row["is_background"] is not None else False
        tags = get_project_tags(row["id"]) if not row_is_background else []

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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO tags (name) VALUES (?)", (name.strip(),))
    conn.commit()

    tag_id = cursor.lastrowid
    conn.close()

    return Tag(id=tag_id, name=name.strip())


def get_tag(name: str) -> Optional[Tag]:
    """Get tag by name (case-insensitive)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, created_at FROM tags WHERE name = ? COLLATE NOCASE",
        (name,)
    )

    row = cursor.fetchone()
    conn.close()

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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, created_at FROM tags ORDER BY name COLLATE NOCASE"
    )

    rows = cursor.fetchall()
    conn.close()

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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.name
        FROM tags t
        JOIN project_tags pt ON t.id = pt.tag_id
        WHERE pt.project_id = ?
        ORDER BY t.name COLLATE NOCASE
    """, (project_id,))

    rows = cursor.fetchall()
    conn.close()

    return [row["name"] for row in rows]


def add_tag_to_project(project_id: int, tag_name: str) -> bool:
    """
    Add a tag to a project. Creates tag if it doesn't exist.

    Returns True if tag was added, False if already existed.
    """
    tag = get_or_create_tag(tag_name)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO project_tags (project_id, tag_id) VALUES (?, ?)",
            (project_id, tag.id)
        )
        conn.commit()
        added = True
    except sqlite3.IntegrityError:
        added = False  # Already tagged

    conn.close()
    return added


def remove_tag_from_project(project_id: int, tag_name: str) -> bool:
    """
    Remove a tag from a project.

    Returns True if tag was removed, False if project didn't have that tag.
    """
    tag = get_tag(tag_name)
    if tag is None:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM project_tags WHERE project_id = ? AND tag_id = ?",
        (project_id, tag.id)
    )

    conn.commit()
    removed = cursor.rowcount > 0
    conn.close()

    return removed


def get_projects_by_tag(tag_name: str) -> list[Project]:
    """Get all projects that have a specific tag (excludes background tasks)."""
    conn = get_connection()
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
    conn.close()

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

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE projects SET priority = ? WHERE id = ?",
        (priority, project.id)
    )

    conn.commit()
    conn.close()

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

    conn = get_connection()
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
    conn.close()

    project.name = new_name
    return project


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
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Record current time as the start
    now = datetime.now()
    
    cursor.execute(
        "INSERT INTO sessions (project_name, start_time) VALUES (?, ?)",
        (project_name, now.isoformat())  # isoformat() converts datetime to string
    )
    
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    
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
    conn = get_connection()
    cursor = conn.cursor()
    
    # WHERE end_time IS NULL finds sessions that haven't been stopped
    # ORDER BY start_time DESC + LIMIT 1 gets the most recent one
    cursor.execute("""
        SELECT id, project_name, start_time, end_time, notes
        FROM sessions
        WHERE end_time IS NULL
        ORDER BY start_time DESC
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
    
    return Session(
        id=row["id"],
        project_name=row["project_name"],
        start_time=datetime.fromisoformat(row["start_time"]),
        end_time=None,
        notes=row["notes"] or ""
    )


def get_active_sessions() -> list[Session]:
    """
    Get ALL currently running sessions.

    Returns:
        List of Session objects with end_time IS NULL, ordered by start_time DESC
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, project_name, start_time, end_time, notes
        FROM sessions
        WHERE end_time IS NULL
        ORDER BY start_time DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        Session(
            id=row["id"],
            project_name=row["project_name"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=None,
            notes=row["notes"] or ""
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, project_name, start_time, end_time, notes
        FROM sessions
        WHERE end_time IS NULL AND project_name = ?
        ORDER BY start_time DESC
        LIMIT 1
    """, (project_name,))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return Session(
        id=row["id"],
        project_name=row["project_name"],
        start_time=datetime.fromisoformat(row["start_time"]),
        end_time=None,
        notes=row["notes"] or ""
    )


def stop_session(project_name: Optional[str] = None, notes: str = "") -> Optional[Session]:
    """
    Stop an active session.

    Args:
        project_name: If provided, stop session for this specific project.
                     If None, stop the most recent active session.
        notes: Optional description of what you worked on

    Returns:
        The stopped Session, or None if no matching session was active
    """
    # Find the target session
    if project_name:
        active = get_active_session_by_project(project_name)
    else:
        active = get_active_session()

    if active is None:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    
    # UPDATE modifies existing rows
    # SET specifies which columns to change
    # WHERE ensures we only update the right row
    cursor.execute("""
        UPDATE sessions
        SET end_time = ?, notes = ?
        WHERE id = ?
    """, (now.isoformat(), notes, active.id))
    
    conn.commit()
    conn.close()
    
    # Update the in-memory object to reflect the change
    active.end_time = now
    active.notes = notes
    
    return active


def stop_all_sessions(notes: str = "") -> list[Session]:
    """
    Stop ALL currently active sessions.

    Args:
        notes: Optional notes applied to all stopped sessions

    Returns:
        List of stopped Session objects
    """
    active_sessions = get_active_sessions()

    if not active_sessions:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()

    # Stop each session
    for session in active_sessions:
        cursor.execute("""
            UPDATE sessions
            SET end_time = ?, notes = ?
            WHERE id = ?
        """, (now.isoformat(), notes, session.id))
        session.end_time = now
        session.notes = notes

    conn.commit()
    conn.close()

    return active_sessions


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
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO sessions (project_name, start_time, end_time, notes)
        VALUES (?, ?, ?, ?)
    """, (project_name, start_time.isoformat(), end_time.isoformat(), notes))
    
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    
    return Session(
        id=session_id,
        project_name=project_name,
        start_time=start_time,
        end_time=end_time,
        notes=notes
    )


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
    conn = get_connection()
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
    conn.close()
    
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
    conn = get_connection()
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
    conn.close()
    
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
    conn = get_connection()
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
    conn.close()

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
    conn = get_connection()
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
    conn.close()

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


def delete_session(session_id: int) -> bool:
    """
    Delete a session by ID.
    
    Returns True if a session was deleted, False if ID not found.
    Use with caution—there's no undo.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    
    conn.commit()
    
    # rowcount tells us how many rows were affected
    deleted = cursor.rowcount > 0
    
    conn.close()
    
    return deleted


def export_sessions_csv(filepath: str):
    """
    Export all completed sessions to a CSV file.
    
    CSV (Comma-Separated Values) is a simple text format that
    spreadsheet programs like Excel can open.
    """
    import csv  # Standard library CSV writer
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT project_name, start_time, end_time, notes,
               (strftime('%s', end_time) - strftime('%s', start_time)) as duration_seconds
        FROM sessions
        WHERE end_time IS NOT NULL
        ORDER BY start_time
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
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
