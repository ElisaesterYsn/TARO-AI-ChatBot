import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "taro.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    return connection


def _migrate_users_table(cursor):
    """
    Recreates the users table with the full schema if any columns are missing.
    Preserves all existing rows.
    """
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    required_columns = {"email", "google_id", "avatar", "password_hash"}

    if required_columns.issubset(existing_columns):
        return  # Already up to date

    print("[TARO DB] Migrating users table to full schema...")

    # Disable FK enforcement during migration
    cursor.execute("PRAGMA foreign_keys = OFF")

    # Rename old table
    cursor.execute("ALTER TABLE users RENAME TO users_old")

    # Create new table with full schema
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            google_id TEXT UNIQUE,
            avatar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Copy existing data — map old columns to new ones safely
    cursor.execute("PRAGMA table_info(users_old)")
    old_cols = [row[1] for row in cursor.fetchall()]

    # Build column list that exists in both old and new
    new_cols = ["id", "username", "email", "password_hash", "google_id", "avatar", "created_at"]
    shared = [c for c in new_cols if c in old_cols]

    if shared:
        cols_str = ", ".join(shared)
        cursor.execute(f"INSERT INTO users ({cols_str}) SELECT {cols_str} FROM users_old")

    cursor.execute("DROP TABLE users_old")
    cursor.execute("PRAGMA foreign_keys = ON")
    print("[TARO DB] Users table migration complete.")


def _add_column_if_missing(cursor, table: str, column: str, definition: str):
    """Adds a non-unique column to an existing table if it doesn't already exist."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cursor.fetchall()]
    if column not in existing:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            print(f"[TARO DB] Migrated: added '{column}' to '{table}'")
        except Exception as e:
            print(f"[TARO DB] Migration warning for '{column}': {e}")


def init_db():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            google_id TEXT UNIQUE,
            avatar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migrate existing users table — recreates it with full schema if needed
    _migrate_users_table(cursor)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(key)
        )
    """)

    connection.commit()
    connection.close()
