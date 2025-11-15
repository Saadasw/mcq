#!/usr/bin/env python3
"""
Migration script: Old CSV structure → New normalized structure (v2.0)

Usage:
    python3 migrate_to_v2.py --source web/ --dest web/data/ [--dry-run]

This script:
1. Backs up all existing CSV files
2. Migrates data to new normalized structure
3. Validates migrated data
4. Creates rollback script
"""

import argparse
import csv
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add parent directory to path to import csv_manager
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.csv_manager import CSVManager, SCHEMAS


class MigrationStats:
    """Track migration statistics"""

    def __init__(self):
        self.sessions_migrated = 0
        self.answer_keys_migrated = 0
        self.student_sessions_migrated = 0
        self.answers_migrated = 0
        self.students_created = 0
        self.errors = []

    def report(self):
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Sessions migrated:         {self.sessions_migrated}")
        print(f"Answer keys migrated:      {self.answer_keys_migrated}")
        print(f"Student sessions migrated: {self.student_sessions_migrated}")
        print(f"Individual answers:        {self.answers_migrated}")
        print(f"Students registered:       {self.students_created}")
        print(f"Errors encountered:        {len(self.errors)}")
        print("=" * 60)

        if self.errors:
            print("\nERRORS:")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")


class Migrator:
    """Handles migration from old to new CSV structure"""

    def __init__(self, source_dir: Path, dest_dir: Path, dry_run: bool = False):
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.dry_run = dry_run
        self.stats = MigrationStats()
        self.csv_manager = CSVManager(dest_dir)

        # Track unique students
        self.students_map: Dict[str, Dict] = {}

    def backup_source(self):
        """Create backup of source directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.source_dir.parent / f"backup_before_migration_{timestamp}"

        print(f"Creating backup: {backup_dir}")

        if not self.dry_run:
            shutil.copytree(
                self.source_dir / "answers",
                backup_dir / "answers",
                ignore=shutil.ignore_patterns("*.pyc", "__pycache__")
            )
            shutil.copytree(
                self.source_dir / "answer_keys",
                backup_dir / "answer_keys",
                ignore=shutil.ignore_patterns("*.pyc", "__pycache__")
            )
            if (self.source_dir / "sessions").exists():
                shutil.copytree(
                    self.source_dir / "sessions",
                    backup_dir / "sessions",
                    ignore=shutil.ignore_patterns("*.pyc", "__pycache__")
                )

        print(f"✓ Backup created: {backup_dir}\n")
        return backup_dir

    def migrate_sessions_from_generated(self):
        """Migrate session metadata from generated/ directory"""
        print("Migrating sessions from generated/ directory...")

        generated_dir = self.source_dir.parent / "generated"
        if not generated_dir.exists():
            print("  No generated/ directory found, skipping...")
            return

        sessions_to_create = []

        for session_dir in generated_dir.iterdir():
            if not session_dir.is_dir() or not session_dir.name.startswith("session_"):
                continue

            session_id = session_dir.name
            pdf_dir = session_dir / "pdfs"

            if not pdf_dir.exists():
                continue

            # Count questions
            question_count = len(list(pdf_dir.glob("snippet_*.pdf")))
            if question_count == 0:
                continue

            # Generate content hash (for cache invalidation)
            content_hash = hashlib.md5(
                "".join([p.name for p in sorted(pdf_dir.glob("*.pdf"))]).encode()
            ).hexdigest()[:16]

            # Get creation time
            try:
                created_at = datetime.fromtimestamp(session_dir.stat().st_ctime)
            except:
                created_at = datetime.now()

            # Create session record
            session_data = {
                "session_id": session_id,
                "content_hash": content_hash,
                "question_count": str(question_count),
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "expires_at": "2026-12-31 23:59:59",  # Default expiry
                "status": "active",
                "exam_duration_minutes": "25",  # Default 25 minutes
                "created_by": "migrated",
                "version": "2.0"
            }

            sessions_to_create.append(session_data)
            self.stats.sessions_migrated += 1

        # Write all sessions
        if sessions_to_create and not self.dry_run:
            self.csv_manager.write("sessions", sessions_to_create, mode='append', validate=True)

        print(f"  ✓ Migrated {len(sessions_to_create)} sessions\n")

    def migrate_answer_keys(self):
        """Migrate answer keys from answer_keys/*.csv to core/answer_keys.csv"""
        print("Migrating answer keys...")

        answer_keys_dir = self.source_dir / "answer_keys"
        if not answer_keys_dir.exists():
            print("  No answer_keys/ directory found, skipping...\n")
            return

        all_answer_keys = []
        answer_key_id_counter = 1

        for answer_key_file in answer_keys_dir.glob("answer_key_*.csv"):
            try:
                # Extract session_id from filename
                session_id = answer_key_file.stem.replace("answer_key_", "")

                with open(answer_key_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        answer_key_str = row.get("Answer_Key", "").strip()

                        # Convert answer key string to individual rows
                        # e.g., "1234" → 4 rows (one per question)
                        for question_index, correct_option in enumerate(answer_key_str):
                            if correct_option in "1234":
                                answer_key_data = {
                                    "answer_key_id": f"AK{answer_key_id_counter:06d}",
                                    "session_id": session_id,
                                    "question_index": str(question_index),
                                    "correct_option": correct_option,
                                    "marks": "1",  # Default 1 mark per question
                                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "version": "2.0"
                                }
                                all_answer_keys.append(answer_key_data)
                                answer_key_id_counter += 1

                self.stats.answer_keys_migrated += 1

            except Exception as e:
                error_msg = f"Error processing {answer_key_file.name}: {e}"
                print(f"  ⚠ {error_msg}")
                self.stats.errors.append(error_msg)

        # Write all answer keys
        if all_answer_keys and not self.dry_run:
            self.csv_manager.write("answer_keys", all_answer_keys, mode='append', validate=True)

        print(f"  ✓ Migrated {self.stats.answer_keys_migrated} answer key files")
        print(f"    ({len(all_answer_keys)} individual question answers)\n")

    def migrate_student_sessions(self):
        """Migrate exam_sessions.csv to student_sessions.csv"""
        print("Migrating student sessions...")

        sessions_file = self.source_dir / "sessions" / "exam_sessions.csv"
        if not sessions_file.exists():
            print("  No exam_sessions.csv found, skipping...\n")
            return

        student_sessions = []
        attempt_id_counter = 1

        with open(sessions_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    student_id = row.get("Student_ID", "").strip()
                    session_id = row.get("Session_ID", "").strip()
                    start_time = row.get("Start_Time", "").strip()

                    if not student_id or not session_id:
                        continue

                    # Register student if new
                    self._register_student(student_id)

                    # Create student session record
                    session_data = {
                        "attempt_id": f"ATT{attempt_id_counter:06d}",
                        "student_id": student_id,
                        "session_id": session_id,
                        "exam_id": "MIGRATED",  # We don't have exam_id in old structure
                        "start_time": start_time,
                        "submit_time": "",  # Will be filled from answers if available
                        "time_taken_seconds": "",
                        "status": "submitted",  # Assume old sessions are completed
                        "ip_address": "unknown",
                        "user_agent": "unknown",
                        "version": "2.0"
                    }

                    student_sessions.append(session_data)
                    attempt_id_counter += 1
                    self.stats.student_sessions_migrated += 1

                except Exception as e:
                    error_msg = f"Error processing session row: {e}"
                    self.stats.errors.append(error_msg)

        # Write all student sessions
        if student_sessions and not self.dry_run:
            self.csv_manager.write("student_sessions", student_sessions, mode='append', validate=True)

        print(f"  ✓ Migrated {len(student_sessions)} student sessions\n")
        return student_sessions

    def migrate_answers(self, student_sessions: List[Dict]):
        """Migrate individual answers from answers/*.csv to transactions/answers.csv"""
        print("Migrating student answers...")

        answers_dir = self.source_dir / "answers"
        if not answers_dir.exists():
            print("  No answers/ directory found, skipping...\n")
            return

        # Create lookup: (student_id, session_id) → attempt_id
        attempt_lookup = {}
        for session in student_sessions:
            key = (session["student_id"], session["session_id"])
            attempt_lookup[key] = session["attempt_id"]

        all_answers = []
        answer_id_counter = 1

        for answers_file in answers_dir.glob("answers_*.csv"):
            try:
                # Extract session_id from filename
                session_id = answers_file.stem.replace("answers_", "")

                with open(answers_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        student_id = row.get("Student_ID", "").strip()
                        timestamp = row.get("Timestamp", "").strip()

                        # Find attempt_id
                        attempt_id = attempt_lookup.get((student_id, session_id))
                        if not attempt_id:
                            # Create a new attempt if not found
                            attempt_id = f"ATT{len(attempt_lookup) + 1:06d}"
                            attempt_lookup[(student_id, session_id)] = attempt_id
                            self._register_student(student_id)

                        # Get answer key for validation
                        answer_key = self._get_answer_key(session_id)

                        # Extract individual answers (Q1, Q2, ...)
                        question_index = 0
                        while f"Q{question_index + 1}" in row:
                            q_col = f"Q{question_index + 1}"
                            selected_answer = row.get(q_col, "").strip()

                            if selected_answer:
                                # Map Bengali options to numbers: ক=1, খ=2, গ=3, ঘ=4
                                option_map = {"ক": "1", "খ": "2", "গ": "3", "ঘ": "4"}
                                selected_option = option_map.get(selected_answer, "")

                                # Check if correct
                                is_correct = "false"
                                marks_awarded = "0"
                                if answer_key and question_index < len(answer_key):
                                    if selected_option == answer_key[question_index]:
                                        is_correct = "true"
                                        marks_awarded = "1"

                                answer_data = {
                                    "answer_id": f"ANS{answer_id_counter:08d}",
                                    "attempt_id": attempt_id,
                                    "question_index": str(question_index),
                                    "selected_option": selected_option,
                                    "is_correct": is_correct,
                                    "marks_awarded": marks_awarded,
                                    "answered_at": timestamp,
                                    "version": "2.0"
                                }

                                all_answers.append(answer_data)
                                answer_id_counter += 1

                            question_index += 1

            except Exception as e:
                error_msg = f"Error processing {answers_file.name}: {e}"
                print(f"  ⚠ {error_msg}")
                self.stats.errors.append(error_msg)

        self.stats.answers_migrated = len(all_answers)

        # Write all answers
        if all_answers and not self.dry_run:
            # Write in batches to avoid memory issues
            batch_size = 5000
            for i in range(0, len(all_answers), batch_size):
                batch = all_answers[i:i + batch_size]
                self.csv_manager.write("answers", batch, mode='append', validate=True)

        print(f"  ✓ Migrated {len(all_answers)} individual answers\n")

    def _register_student(self, student_id: str):
        """Register a student if not already registered"""
        if student_id in self.students_map:
            return

        student_data = {
            "student_id": student_id,
            "name": f"Student {student_id}",  # Placeholder
            "email": f"{student_id}@placeholder.com",
            "institution": "Unknown",
            "batch": "Unknown",
            "registration_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "active",
            "version": "2.0"
        }

        self.students_map[student_id] = student_data
        self.stats.students_created += 1

    def _get_answer_key(self, session_id: str) -> str:
        """Get answer key string for a session from old format"""
        answer_key_file = self.source_dir / "answer_keys" / f"answer_key_{session_id}.csv"
        if not answer_key_file.exists():
            return ""

        try:
            with open(answer_key_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    return row.get("Answer_Key", "").strip()
        except:
            return ""

    def write_students(self):
        """Write all registered students to CSV"""
        if self.students_map and not self.dry_run:
            students_list = list(self.students_map.values())
            self.csv_manager.write("students", students_list, mode='append', validate=True)
            print(f"✓ Created {len(students_list)} student records\n")

    def validate_migration(self):
        """Validate migrated data"""
        print("Validating migrated data...")

        if self.dry_run:
            print("  [DRY RUN] Skipping validation\n")
            return True

        try:
            # Check that all files exist
            required_files = [
                "core/sessions.csv",
                "core/answer_keys.csv",
                "core/students.csv",
                "transactions/student_sessions.csv",
                "transactions/answers.csv"
            ]

            for file_path in required_files:
                full_path = self.dest_dir / file_path
                if not full_path.exists():
                    print(f"  ✗ Missing file: {file_path}")
                    return False
                else:
                    # Count rows
                    with open(full_path, 'r', encoding='utf-8') as f:
                        row_count = sum(1 for _ in csv.reader(f)) - 1  # Exclude header
                    print(f"  ✓ {file_path}: {row_count} rows")

            print("\n✓ Validation passed!\n")
            return True

        except Exception as e:
            print(f"  ✗ Validation error: {e}\n")
            return False

    def create_rollback_script(self, backup_dir: Path):
        """Create a rollback script"""
        rollback_script = self.dest_dir.parent / "rollback_migration.sh"

        script_content = f"""#!/bin/bash
# Rollback migration to v2.0
# Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

echo "Rolling back migration..."

# Remove new structure
rm -rf {self.dest_dir}

# Restore from backup
cp -r {backup_dir}/* {self.source_dir}/

echo "✓ Rollback complete!"
echo "Old structure restored from: {backup_dir}"
"""

        if not self.dry_run:
            rollback_script.write_text(script_content)
            rollback_script.chmod(0o755)

        print(f"✓ Rollback script created: {rollback_script}\n")

    def run(self):
        """Run the complete migration"""
        print("\n" + "=" * 60)
        print("CSV MIGRATION: Old Structure → New Structure (v2.0)")
        print("=" * 60)
        print(f"Source: {self.source_dir}")
        print(f"Destination: {self.dest_dir}")
        print(f"Dry run: {self.dry_run}")
        print("=" * 60 + "\n")

        if self.dry_run:
            print("⚠ DRY RUN MODE - No files will be modified\n")

        # Step 1: Backup
        backup_dir = self.backup_source()

        # Step 2: Migrate sessions
        self.migrate_sessions_from_generated()

        # Step 3: Migrate answer keys
        self.migrate_answer_keys()

        # Step 4: Migrate student sessions
        student_sessions = self.migrate_student_sessions()

        # Step 5: Migrate answers
        if student_sessions:
            self.migrate_answers(student_sessions)

        # Step 6: Write students
        self.write_students()

        # Step 7: Validate
        is_valid = self.validate_migration()

        # Step 8: Create rollback script
        self.create_rollback_script(backup_dir)

        # Step 9: Show summary
        self.stats.report()

        if is_valid:
            print("\n✅ Migration completed successfully!")
            print(f"Backup location: {backup_dir}")
            print(f"New data location: {self.dest_dir}")
        else:
            print("\n⚠ Migration completed with validation errors!")
            print("Please review the errors above.")

        return is_valid


def main():
    parser = argparse.ArgumentParser(
        description="Migrate CSV structure from v1.0 to v2.0"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Source directory containing old CSV structure (e.g., web/)"
    )
    parser.add_argument(
        "--dest",
        type=str,
        required=True,
        help="Destination directory for new CSV structure (e.g., web/data/)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run migration without writing files (test mode)"
    )

    args = parser.parse_args()

    # Run migration
    migrator = Migrator(
        source_dir=Path(args.source),
        dest_dir=Path(args.dest),
        dry_run=args.dry_run
    )

    success = migrator.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
