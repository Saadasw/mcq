#!/usr/bin/env python3
"""
CSV Data Validation Tool

Validates CSV files against schemas and checks data integrity.

Usage:
    python3 validate_csv.py --data-dir web/data/
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.csv_manager import SCHEMAS, CSVManager


class ValidationReport:
    """Track validation results"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.file_stats = {}

    def add_error(self, message: str):
        self.errors.append(f"ERROR: {message}")

    def add_warning(self, message: str):
        self.warnings.append(f"WARNING: {message}")

    def add_info(self, message: str):
        self.info.append(f"INFO: {message}")

    def add_file_stats(self, file_name: str, row_count: int, file_size: int):
        self.file_stats[file_name] = {"rows": row_count, "size": file_size}

    def print_report(self):
        print("\n" + "=" * 70)
        print("CSV VALIDATION REPORT")
        print("=" * 70)

        # File statistics
        print("\nFILE STATISTICS:")
        print("-" * 70)
        for file_name, stats in sorted(self.file_stats.items()):
            size_kb = stats["size"] / 1024
            print(f"  {file_name:30s} {stats['rows']:6d} rows  {size_kb:8.2f} KB")

        # Info messages
        if self.info:
            print("\nINFORMATION:")
            print("-" * 70)
            for msg in self.info:
                print(f"  ℹ {msg}")

        # Warnings
        if self.warnings:
            print("\nWARNINGS:")
            print("-" * 70)
            for msg in self.warnings:
                print(f"  ⚠ {msg}")

        # Errors
        if self.errors:
            print("\nERRORS:")
            print("-" * 70)
            for msg in self.errors:
                print(f"  ✗ {msg}")

        # Summary
        print("\nSUMMARY:")
        print("-" * 70)
        print(f"  Files validated: {len(self.file_stats)}")
        print(f"  Info messages:   {len(self.info)}")
        print(f"  Warnings:        {len(self.warnings)}")
        print(f"  Errors:          {len(self.errors)}")

        if self.errors:
            print("\n❌ VALIDATION FAILED")
        elif self.warnings:
            print("\n⚠️  VALIDATION PASSED WITH WARNINGS")
        else:
            print("\n✅ VALIDATION PASSED")

        print("=" * 70 + "\n")

    def has_errors(self) -> bool:
        return len(self.errors) > 0


class CSVValidator:
    """Validates CSV files against schemas and checks referential integrity"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.report = ValidationReport()
        self.csv_manager = CSVManager(data_dir)

        # Cache for foreign key lookups
        self.pk_cache: Dict[str, Set[str]] = {}

    def validate_schema_version(self):
        """Check schema version file"""
        version_file = self.data_dir / "schema_version.txt"

        if not version_file.exists():
            self.report.add_error("schema_version.txt not found")
            return

        version = version_file.read_text().strip()
        expected_version = "2.0"

        if version != expected_version:
            self.report.add_warning(f"Schema version is {version}, expected {expected_version}")
        else:
            self.report.add_info(f"Schema version: {version}")

    def validate_file_structure(self):
        """Check that required directories and files exist"""
        required_dirs = [
            "core",
            "transactions",
            "audit",
            "backups"
        ]

        for dir_name in required_dirs:
            dir_path = self.data_dir / dir_name
            if not dir_path.exists():
                self.report.add_error(f"Required directory missing: {dir_name}/")
            else:
                self.report.add_info(f"Directory exists: {dir_name}/")

    def validate_csv_file(self, schema_name: str):
        """Validate a single CSV file"""
        schema = SCHEMAS.get(schema_name)
        if not schema:
            self.report.add_error(f"Unknown schema: {schema_name}")
            return

        file_path = self.csv_manager._get_file_path(schema_name)

        if not file_path.exists():
            self.report.add_warning(f"File does not exist: {file_path.name} (this is OK if no data yet)")
            return

        # Check file size
        file_size = file_path.stat().st_size

        # Read and validate rows
        try:
            rows = []
            pk_set = set()
            row_num = 0

            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Check headers
                if reader.fieldnames != schema.columns:
                    self.report.add_error(
                        f"{schema_name}: Column mismatch. "
                        f"Expected {schema.columns}, got {reader.fieldnames}"
                    )
                    return

                # Validate each row
                for row in reader:
                    row_num += 1
                    rows.append(row)

                    # Validate row against schema
                    is_valid, error_msg = schema.validate_row(row)
                    if not is_valid:
                        self.report.add_error(
                            f"{schema_name} row {row_num}: {error_msg}"
                        )

                    # Check primary key uniqueness
                    pk_value = row.get(schema.primary_key)
                    if pk_value:
                        if pk_value in pk_set:
                            self.report.add_error(
                                f"{schema_name} row {row_num}: Duplicate primary key: {pk_value}"
                            )
                        pk_set.add(pk_value)

            # Cache primary keys for foreign key validation
            self.pk_cache[schema_name] = pk_set

            # Add stats
            self.report.add_file_stats(file_path.name, len(rows), file_size)

            # Info message
            self.report.add_info(f"{schema_name}: Validated {len(rows)} rows")

        except Exception as e:
            self.report.add_error(f"{schema_name}: Failed to read file: {e}")

    def validate_foreign_keys(self):
        """Validate foreign key relationships"""
        # Define relationships: (child_table, child_column) -> (parent_table, parent_column)
        relationships = [
            ("answer_keys", "session_id", "sessions", "session_id"),
            ("student_sessions", "student_id", "students", "student_id"),
            ("student_sessions", "session_id", "sessions", "session_id"),
            ("answers", "attempt_id", "student_sessions", "attempt_id"),
            ("submissions", "attempt_id", "student_sessions", "attempt_id"),
        ]

        for child_table, child_col, parent_table, parent_col in relationships:
            # Skip if either table not cached
            if child_table not in self.pk_cache or parent_table not in self.pk_cache:
                continue

            # Get all values from child table
            child_rows = self.csv_manager.read(child_table)
            parent_keys = self.pk_cache[parent_table]

            orphaned_count = 0
            for row in child_rows:
                fk_value = row.get(child_col, "").strip()
                if fk_value and fk_value not in parent_keys:
                    orphaned_count += 1
                    if orphaned_count <= 5:  # Show first 5
                        self.report.add_error(
                            f"Foreign key violation: {child_table}.{child_col}={fk_value} "
                            f"references non-existent {parent_table}.{parent_col}"
                        )

            if orphaned_count > 0:
                self.report.add_error(
                    f"{child_table}: {orphaned_count} orphaned records (FK: {child_col} -> {parent_table}.{parent_col})"
                )
            else:
                self.report.add_info(
                    f"{child_table}.{child_col} -> {parent_table}.{parent_col}: OK"
                )

    def validate_data_consistency(self):
        """Check for data consistency issues"""
        # Check 1: Answer keys should match session question count
        sessions = self.csv_manager.read("sessions")
        for session in sessions:
            session_id = session.get("session_id")
            expected_count = int(session.get("question_count", 0))

            answer_keys = self.csv_manager.read(
                "answer_keys",
                filter_fn=lambda r: r.get("session_id") == session_id
            )

            actual_count = len(answer_keys)

            if actual_count != expected_count:
                self.report.add_warning(
                    f"Session {session_id}: Expected {expected_count} answer keys, "
                    f"found {actual_count}"
                )

        # Check 2: Answers should reference valid question indices
        answer_keys_by_session = defaultdict(set)
        for key in self.csv_manager.read("answer_keys"):
            session_id = key.get("session_id")
            question_index = int(key.get("question_index", -1))
            answer_keys_by_session[session_id].add(question_index)

        answers = self.csv_manager.read("answers")
        invalid_answer_count = 0

        for answer in answers:
            attempt_id = answer.get("attempt_id")
            question_index = int(answer.get("question_index", -1))

            # Find session for this attempt
            attempt = self.csv_manager.read_by_id("student_sessions", attempt_id)
            if not attempt:
                continue

            session_id = attempt.get("session_id")
            valid_indices = answer_keys_by_session.get(session_id, set())

            if question_index not in valid_indices:
                invalid_answer_count += 1
                if invalid_answer_count <= 5:
                    self.report.add_error(
                        f"Answer {answer.get('answer_id')}: Question index {question_index} "
                        f"not found in answer keys for session {session_id}"
                    )

        if invalid_answer_count > 5:
            self.report.add_error(
                f"... and {invalid_answer_count - 5} more invalid answer references"
            )

    def validate_all(self):
        """Run all validations"""
        print("Starting CSV validation...\n")

        # Step 1: Check schema version
        self.validate_schema_version()

        # Step 2: Check file structure
        self.validate_file_structure()

        # Step 3: Validate each CSV file
        for schema_name in SCHEMAS.keys():
            self.validate_csv_file(schema_name)

        # Step 4: Validate foreign keys
        self.validate_foreign_keys()

        # Step 5: Validate data consistency
        self.validate_data_consistency()

        # Print report
        self.report.print_report()

        return not self.report.has_errors()


def main():
    parser = argparse.ArgumentParser(
        description="Validate CSV data structure and integrity"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="Data directory to validate (e.g., web/data/)"
    )

    args = parser.parse_args()

    validator = CSVValidator(Path(args.data_dir))
    success = validator.validate_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
