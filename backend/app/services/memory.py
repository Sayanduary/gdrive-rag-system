import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

DATABASE_PATH = DATA_DIR / "memory.db"


class ConversationMemory:

    def __init__(self):

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        self.connection = sqlite3.connect(
            DATABASE_PATH,
            check_same_thread=False
        )

        self.connection.row_factory = sqlite3.Row

        # Enable foreign-key support.
        self.connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        self.create_tables()

    # ==================================================
    # TABLES
    # ==================================================

    def create_tables(self):

        # ----------------------------------------------
        # Create conversations table.
        #
        # folder_id is included for new databases.
        # ----------------------------------------------

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                folder_id TEXT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # ----------------------------------------------
        # Create messages table.
        # ----------------------------------------------

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TEXT NOT NULL,

                FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
            )
            """
        )

        self.connection.commit()

        # ----------------------------------------------
        # Migrate old database BEFORE creating indexes.
        # ----------------------------------------------

        self.migrate_tables()

        # ----------------------------------------------
        # Indexes
        # ----------------------------------------------

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_conversations_user
            ON conversations(user_id)
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_conversations_folder
            ON conversations(folder_id)
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_messages_conversation
            ON messages(conversation_id)
            """
        )

        self.connection.commit()

    # ==================================================
    # DATABASE MIGRATION
    # ==================================================

    def migrate_tables(self):

        columns = self.connection.execute(
            """
            PRAGMA table_info(conversations)
            """
        ).fetchall()

        column_names = {
            column["name"]
            for column in columns
        }

        # ----------------------------------------------
        # Add folder_id to old database
        # ----------------------------------------------

        if "folder_id" not in column_names:

            print(
                "Migrating conversations table: "
                "adding folder_id..."
            )

            self.connection.execute(
                """
                ALTER TABLE conversations
                ADD COLUMN folder_id TEXT
                """
            )

            self.connection.commit()

    # ==================================================
    # CREATE CONVERSATION
    # ==================================================

    def create_conversation(
        self,
        user_id: str,
        folder_id: str | None = None,
        title: str = "New Chat"
    ) -> int:

        now = datetime.now(
            timezone.utc
        ).isoformat()

        cursor = self.connection.execute(
            """
            INSERT INTO conversations (
                user_id,
                folder_id,
                title,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                folder_id,
                title,
                now,
                now
            )
        )

        self.connection.commit()

        return cursor.lastrowid

    # ==================================================
    # ADD MESSAGE
    # ==================================================

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        sources: list | None = None
    ):

        now = datetime.now(
            timezone.utc
        ).isoformat()

        self.connection.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                sources,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                json.dumps(
                    sources or []
                ),
                now
            )
        )

        self.connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (
                now,
                conversation_id
            )
        )

        self.connection.commit()

    # ==================================================
    # GET MESSAGES
    # ==================================================

    def get_messages(
        self,
        conversation_id: int,
        limit: int = 30
    ):

        rows = self.connection.execute(
            """
            SELECT
                role,
                content,
                sources,
                created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                conversation_id,
                limit
            )
        ).fetchall()

        messages = []

        for row in reversed(rows):

            try:
                sources = json.loads(
                    row["sources"] or "[]"
                )

            except (
                json.JSONDecodeError,
                TypeError
            ):

                sources = []

            messages.append({
                "role": row["role"],
                "content": row["content"],
                "sources": sources,
                "created_at": row["created_at"]
            })

        return messages

    # ==================================================
    # GET USER CONVERSATIONS
    # ==================================================

    def get_user_conversations(
        self,
        user_id: str
    ):

        rows = self.connection.execute(
            """
            SELECT
                id,
                folder_id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (
                user_id,
            )
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    # ==================================================
    # GET CONVERSATION FOLDER
    # ==================================================

    def get_conversation_folder(
        self,
        conversation_id: int,
        user_id: str
    ):

        row = self.connection.execute(
            """
            SELECT
                folder_id
            FROM conversations
            WHERE id = ?
            AND user_id = ?
            """,
            (
                conversation_id,
                user_id
            )
        ).fetchone()

        if not row:
            return None

        return row["folder_id"]

    # ==================================================
    # GET CONVERSATION
    # ==================================================

    def get_conversation(
        self,
        conversation_id: int,
        user_id: str
    ):

        row = self.connection.execute(
            """
            SELECT
                id,
                user_id,
                folder_id,
                title,
                created_at,
                updated_at
            FROM conversations
            WHERE id = ?
            AND user_id = ?
            """,
            (
                conversation_id,
                user_id
            )
        ).fetchone()

        if not row:
            return None

        return dict(row)

    # ==================================================
    # OWNERSHIP CHECK
    # ==================================================

    def conversation_belongs_to_user(
        self,
        conversation_id: int,
        user_id: str
    ) -> bool:

        row = self.connection.execute(
            """
            SELECT
                id
            FROM conversations
            WHERE id = ?
            AND user_id = ?
            """,
            (
                conversation_id,
                user_id
            )
        ).fetchone()

        return row is not None

    # ==================================================
    # RENAME CONVERSATION
    # ==================================================

    def rename_conversation(
        self,
        conversation_id: int,
        user_id: str,
        title: str
    ):

        now = datetime.now(
            timezone.utc
        ).isoformat()

        self.connection.execute(
            """
            UPDATE conversations
            SET
                title = ?,
                updated_at = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                title,
                now,
                conversation_id,
                user_id
            )
        )

        self.connection.commit()

    # ==================================================
    # DELETE CONVERSATION
    # ==================================================

    def delete_conversation(
        self,
        conversation_id: int,
        user_id: str
    ):

        self.connection.execute(
            """
            DELETE FROM conversations
            WHERE id = ?
            AND user_id = ?
            """,
            (
                conversation_id,
                user_id
            )
        )

        self.connection.commit()

    # ==================================================
    # UPDATE CONVERSATION FOLDER
    # ==================================================

    def update_conversation_folder(
        self,
        conversation_id: int,
        user_id: str,
        folder_id: str
    ):

        self.connection.execute(
            """
            UPDATE conversations
            SET
                folder_id = ?,
                updated_at = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                folder_id,
                datetime.now(
                    timezone.utc
                ).isoformat(),
                conversation_id,
                user_id
            )
        )

        self.connection.commit()