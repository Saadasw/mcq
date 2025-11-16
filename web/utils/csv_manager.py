"""
CSV Management Utilities with Thread-Safe Operations
Provides file locking, validation, backup, and CRUD operations for CSV files.
"""

import csv
import fcntl
import hashlib
import json
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import tempfile


class CSVValidationError(Exception):
    """Raised when CSV data validation fails"""
    pass


class CSVLockError(Exception):
    """Raised when unable to acquire file lock"""
    pass


class CSVSchema:
    """Schema definition for CSV files with validation rules"""

    def __init__(self, name: str, columns: List[str],
                 primary_key: str,
                 required_columns: Optional[List[str]] = None,
                 validators: Optional[Dict[str, Callable]] = None):
        self.name = name
        self.columns = columns
        self.primary_key = primary_key
        self.required_columns = required_columns or columns
        self.validators = validators or {}

    def validate_row(self, row: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate a single row against schema. Returns (is_valid, error_message)"""
        # Check required columns
        for col in self.required_columns:
            if col not in row or not row[col]:
                return False, f"Missing required column: {col}"

        # Check extra columns
        for col in row.keys():
            if col not in self.columns:
                return False, f"Unknown column: {col}"

        # Run custom validators
        for col, validator in self.validators.items():
            if col in row:
                try:
                    if not validator(row[col]):
                        return False, f"Validation failed for {col}: {row[col]}"
                except Exception as e:
                    return False, f"Validator error for {col}: {str(e)}"

        return True, None


# Define schemas for all CSV files
SCHEMAS = {
    "sessions": CSVSchema(
        name="sessions",
        columns=["session_id", "content_hash", "question_count", "created_at",
                 "expires_at", "status", "exam_duration_minutes", "created_by", "version"],
        primary_key="session_id",
        validators={
            "question_count": lambda x: str(x).isdigit() and int(x) > 0,
            "status": lambda x: x in ["active", "archived", "deleted"],
            "exam_duration_minutes": lambda x: str(x).isdigit() and int(x) > 0,
        }
    ),
    "answer_keys": CSVSchema(
        name="answer_keys",
        columns=["answer_key_id", "session_id", "question_index",
                 "correct_option", "marks", "created_at", "version"],
        primary_key="answer_key_id",
        validators={
            "question_index": lambda x: str(x).isdigit() and int(x) >= 0,
            "correct_option": lambda x: x in ["1", "2", "3", "4"],
            "marks": lambda x: str(x).replace(".", "").isdigit(),
        }
    ),
    "students": CSVSchema(
        name="students",
        columns=["student_id", "name", "email", "institution",
                 "batch", "registration_date", "status", "version"],
        primary_key="student_id",
        validators={
            "status": lambda x: x in ["active", "inactive", "suspended"],
            "email": lambda x: "@" in x,
        }
    ),
    "student_sessions": CSVSchema(
        name="student_sessions",
        columns=["attempt_id", "student_id", "session_id", "exam_id",
                 "start_time", "submit_time", "time_taken_seconds",
                 "status", "ip_address", "user_agent", "version"],
        primary_key="attempt_id",
        validators={
            "status": lambda x: x in ["in_progress", "submitted", "time_expired", "abandoned"],
        }
    ),
    "answers": CSVSchema(
        name="answers",
        columns=["answer_id", "attempt_id", "question_index",
                 "selected_option", "is_correct", "marks_awarded",
                 "answered_at", "version"],
        primary_key="answer_id",
        validators={
            "selected_option": lambda x: x in ["1", "2", "3", "4", "NULL", ""],
            "is_correct": lambda x: x in ["true", "false", ""],
        }
    ),
    "submissions": CSVSchema(
        name="submissions",
        columns=["submission_id", "attempt_id", "total_marks",
                 "marks_obtained", "percentage", "result",
                 "submitted_at", "graded_at", "graded_by", "version"],
        primary_key="submission_id",
        validators={
            "result": lambda x: x in ["pass", "fail", "pending"],
        }
    ),
    "audit_log": CSVSchema(
        name="audit_log",
        columns=["log_id", "timestamp", "entity_type", "entity_id",
                 "action", "user_id", "old_value", "new_value",
                 "ip_address", "version"],
        primary_key="log_id",
        validators={
            "action": lambda x: x in ["create", "update", "delete", "view"],
        }
    ),
}


class CSVManager:
    """Thread-safe CSV file manager with locking, validation, and backup"""

    def __init__(self, data_dir: Path, auto_backup: bool = True,
                 lock_timeout: int = 5, schema_version: str = "2.0"):
        self.data_dir = Path(data_dir)
        self.auto_backup = auto_backup
        self.lock_timeout = lock_timeout
        self.schema_version = schema_version
        self._ensure_structure()

    def _ensure_structure(self):
        """Create directory structure if it doesn't exist"""
        (self.data_dir / "core").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "transactions").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "audit").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "backups" / "daily").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "backups" / "before_write").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "backups" / "before_migration").mkdir(parents=True, exist_ok=True)

        # Create schema version file
        version_file = self.data_dir / "schema_version.txt"
        if not version_file.exists():
            version_file.write_text(self.schema_version)

    @contextmanager
    def _lock_file(self, file_path: Path, mode: str = 'r'):
        """Context manager for file locking"""
        lock_file = file_path.parent / f".{file_path.name}.lock"
        lock_file.touch(exist_ok=True)

        with open(lock_file, 'w') as lock_handle:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
            except IOError:
                raise CSVLockError(f"Could not acquire lock for {file_path}")
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    def _backup_file(self, file_path: Path, backup_type: str = "before_write"):
        """Create backup of CSV file"""
        if not file_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.data_dir / "backups" / backup_type
        backup_file = backup_dir / f"{file_path.stem}_{timestamp}.csv"

        shutil.copy2(file_path, backup_file)

        # Keep only last 10 backups per file
        backups = sorted(backup_dir.glob(f"{file_path.stem}_*.csv"))
        for old_backup in backups[:-10]:
            old_backup.unlink()

    def _get_file_path(self, schema_name: str) -> Path:
        """Get file path for a schema"""
        if schema_name in ["sessions", "answer_keys", "students", "exams"]:
            return self.data_dir / "core" / f"{schema_name}.csv"
        elif schema_name in ["student_sessions", "answers", "submissions"]:
            return self.data_dir / "transactions" / f"{schema_name}.csv"
        elif schema_name == "audit_log":
            return self.data_dir / "audit" / f"{schema_name}.csv"
        else:
            raise ValueError(f"Unknown schema: {schema_name}")

    def _ensure_file_exists(self, file_path: Path, schema: CSVSchema):
        """Create CSV file with headers if it doesn't exist"""
        if not file_path.exists():
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=schema.columns)
                writer.writeheader()

    def read(self, schema_name: str, filter_fn: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Read all rows from CSV file

        Args:
            schema_name: Name of the schema (e.g., 'sessions', 'answers')
            filter_fn: Optional function to filter rows. Should return True to include row.

        Returns:
            List of dictionaries, each representing a row
        """
        schema = SCHEMAS.get(schema_name)
        if not schema:
            raise ValueError(f"Unknown schema: {schema_name}")

        file_path = self._get_file_path(schema_name)
        self._ensure_file_exists(file_path, schema)

        rows = []
        with self._lock_file(file_path, 'r'):
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if filter_fn is None or filter_fn(row):
                        rows.append(row)

        return rows

    def read_by_id(self, schema_name: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Read a single row by primary key"""
        schema = SCHEMAS.get(schema_name)
        if not schema:
            raise ValueError(f"Unknown schema: {schema_name}")

        pk = schema.primary_key
        rows = self.read(schema_name, filter_fn=lambda r: r.get(pk) == entity_id)
        return rows[0] if rows else None

    def write(self, schema_name: str, rows: List[Dict[str, Any]],
              mode: str = 'append', validate: bool = True) -> int:
        """
        Write rows to CSV file

        Args:
            schema_name: Name of the schema
            rows: List of dictionaries to write
            mode: 'append' to add rows, 'replace' to overwrite file
            validate: Whether to validate rows before writing

        Returns:
            Number of rows written
        """
        schema = SCHEMAS.get(schema_name)
        if not schema:
            raise ValueError(f"Unknown schema: {schema_name}")

        # Validate all rows
        if validate:
            for i, row in enumerate(rows):
                is_valid, error = schema.validate_row(row)
                if not is_valid:
                    raise CSVValidationError(f"Row {i} validation failed: {error}")

        file_path = self._get_file_path(schema_name)

        # Backup before write
        if self.auto_backup and file_path.exists():
            self._backup_file(file_path)

        with self._lock_file(file_path, 'w'):
            if mode == 'replace':
                # Replace entire file
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=schema.columns)
                    writer.writeheader()
                    writer.writerows(rows)
            else:
                # Append to file
                self._ensure_file_exists(file_path, schema)
                with open(file_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=schema.columns)
                    writer.writerows(rows)

        # Log to audit
        self._log_audit(
            entity_type=schema_name,
            entity_id=",".join([r.get(schema.primary_key, "?") for r in rows[:3]]),
            action="create" if mode == 'append' else "replace",
            user_id="system",
            new_value=f"{len(rows)} rows"
        )

        return len(rows)

    def update(self, schema_name: str, entity_id: str,
               updates: Dict[str, Any], user_id: str = "system") -> bool:
        """
        Update a single row by primary key

        Args:
            schema_name: Name of the schema
            entity_id: Value of primary key
            updates: Dictionary of column->value to update
            user_id: User performing the update

        Returns:
            True if row was found and updated, False otherwise
        """
        schema = SCHEMAS.get(schema_name)
        if not schema:
            raise ValueError(f"Unknown schema: {schema_name}")

        pk = schema.primary_key
        file_path = self._get_file_path(schema_name)

        if not file_path.exists():
            return False

        # Read all rows
        all_rows = []
        old_row = None
        found = False

        with self._lock_file(file_path, 'r'):
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get(pk) == entity_id:
                        old_row = row.copy()
                        row.update(updates)
                        found = True
                    all_rows.append(row)

        if not found:
            return False

        # Validate updated row
        updated_row = next((r for r in all_rows if r.get(pk) == entity_id), None)
        if updated_row:
            is_valid, error = schema.validate_row(updated_row)
            if not is_valid:
                raise CSVValidationError(f"Update validation failed: {error}")

        # Backup and write
        if self.auto_backup:
            self._backup_file(file_path)

        with self._lock_file(file_path, 'w'):
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=schema.columns)
                writer.writeheader()
                writer.writerows(all_rows)

        # Log to audit
        self._log_audit(
            entity_type=schema_name,
            entity_id=entity_id,
            action="update",
            user_id=user_id,
            old_value=json.dumps(old_row),
            new_value=json.dumps(updated_row)
        )

        return True

    def delete(self, schema_name: str, entity_id: str, user_id: str = "system") -> bool:
        """
        Delete a row by primary key

        Args:
            schema_name: Name of the schema
            entity_id: Value of primary key
            user_id: User performing the delete

        Returns:
            True if row was found and deleted, False otherwise
        """
        schema = SCHEMAS.get(schema_name)
        if not schema:
            raise ValueError(f"Unknown schema: {schema_name}")

        pk = schema.primary_key
        file_path = self._get_file_path(schema_name)

        if not file_path.exists():
            return False

        # Read all rows except the one to delete
        all_rows = []
        deleted_row = None

        with self._lock_file(file_path, 'r'):
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get(pk) == entity_id:
                        deleted_row = row.copy()
                    else:
                        all_rows.append(row)

        if not deleted_row:
            return False

        # Backup and write
        if self.auto_backup:
            self._backup_file(file_path)

        with self._lock_file(file_path, 'w'):
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=schema.columns)
                writer.writeheader()
                writer.writerows(all_rows)

        # Log to audit
        self._log_audit(
            entity_type=schema_name,
            entity_id=entity_id,
            action="delete",
            user_id=user_id,
            old_value=json.dumps(deleted_row),
            new_value="NULL"
        )

        return True

    def _log_audit(self, entity_type: str, entity_id: str, action: str,
                   user_id: str, old_value: str = "NULL",
                   new_value: str = "NULL", ip_address: str = "127.0.0.1"):
        """Write to audit log (without triggering recursive logging)"""
        try:
            audit_file = self.data_dir / "audit" / "audit_log.csv"

            # Generate log ID
            log_id = f"LOG{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

            row = {
                "log_id": log_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "user_id": user_id,
                "old_value": old_value[:200],  # Truncate long values
                "new_value": new_value[:200],
                "ip_address": ip_address,
                "version": self.schema_version
            }

            # Ensure file exists
            if not audit_file.exists():
                with open(audit_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=SCHEMAS["audit_log"].columns)
                    writer.writeheader()

            # Append without triggering audit (avoid recursion)
            with open(audit_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=SCHEMAS["audit_log"].columns)
                writer.writerow(row)
        except Exception as e:
            print(f"Warning: Failed to write audit log: {e}")

    def generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        random_part = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        return f"{prefix}{random_part.upper()}"

    def backup_all(self, backup_name: str = None):
        """Create a complete backup of all CSV files"""
        if backup_name is None:
            backup_name = f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_dir = self.data_dir / "backups" / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup all CSV files
        for csv_file in self.data_dir.rglob("*.csv"):
            if "backups" not in str(csv_file):
                rel_path = csv_file.relative_to(self.data_dir)
                dest = backup_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(csv_file, dest)

        print(f"Backup created: {backup_dir}")
        return backup_dir

    def count(self, schema_name: str, filter_fn: Optional[Callable] = None) -> int:
        """Count rows in a CSV file"""
        return len(self.read(schema_name, filter_fn=filter_fn))

    def exists(self, schema_name: str, entity_id: str) -> bool:
        """Check if a row exists by primary key"""
        return self.read_by_id(schema_name, entity_id) is not None


# Convenience functions
def get_csv_manager(data_dir: str = None) -> CSVManager:
    """Get a CSV manager instance"""
    if data_dir is None:
        from pathlib import Path
        data_dir = Path(__file__).parent.parent / "data"
    return CSVManager(Path(data_dir))


# Example usage
if __name__ == "__main__":
    # Create manager
    manager = CSVManager(Path("web/data"))

    # Create a session
    session_data = {
        "session_id": "session_test123",
        "content_hash": "abc123def",
        "question_count": "10",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": "2025-12-31 23:59:59",
        "status": "active",
        "exam_duration_minutes": "25",
        "created_by": "admin",
        "version": "2.0"
    }

    manager.write("sessions", [session_data])

    # Read all sessions
    sessions = manager.read("sessions")
    print(f"Found {len(sessions)} sessions")

    # Update a session
    manager.update("sessions", "session_test123", {"status": "archived"}, user_id="admin")

    # Read specific session
    session = manager.read_by_id("sessions", "session_test123")
    print(f"Session status: {session['status']}")

    # Delete session
    manager.delete("sessions", "session_test123", user_id="admin")

    print("CSV Manager demo complete!")
