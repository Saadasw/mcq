#!/usr/bin/env python3
"""
Migration script: Convert old CSV format to normalized structure
Usage: python migrate_to_normalized.py
"""

import csv
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Directories
WEB_DIR = Path(__file__).parent / "web"
OLD_ANSWER_KEYS_DIR = WEB_DIR / "answer_keys"
OLD_ANSWERS_DIR = WEB_DIR / "answers"
OLD_SESSION_METADATA_DIR = WEB_DIR / "session_metadata"
GENERATED_DIR = WEB_DIR / "generated"

# New normalized files
EXAMS_FILE = WEB_DIR / "exams.csv"
QUESTIONS_FILE = WEB_DIR / "questions.csv"
SUBMISSIONS_FILE = WEB_DIR / "submissions.csv"
STUDENT_ANSWERS_FILE = WEB_DIR / "student_answers.csv"

# Backup directory
BACKUP_DIR = WEB_DIR / "csv_backup_old_format"


def backup_old_files():
    """Backup old CSV files before migration"""
    print("📦 Creating backup of old CSV files...")
    BACKUP_DIR.mkdir(exist_ok=True)

    # Backup answer_keys
    if OLD_ANSWER_KEYS_DIR.exists():
        backup_answer_keys = BACKUP_DIR / "answer_keys"
        if backup_answer_keys.exists():
            shutil.rmtree(backup_answer_keys)
        shutil.copytree(OLD_ANSWER_KEYS_DIR, backup_answer_keys)
        print(f"  ✓ Backed up answer_keys/")

    # Backup answers
    if OLD_ANSWERS_DIR.exists():
        backup_answers = BACKUP_DIR / "answers"
        if backup_answers.exists():
            shutil.rmtree(backup_answers)
        shutil.copytree(OLD_ANSWERS_DIR, backup_answers)
        print(f"  ✓ Backed up answers/")

    # Backup session_metadata
    if OLD_SESSION_METADATA_DIR.exists():
        backup_metadata = BACKUP_DIR / "session_metadata"
        if backup_metadata.exists():
            shutil.rmtree(backup_metadata)
        shutil.copytree(OLD_SESSION_METADATA_DIR, backup_metadata)
        print(f"  ✓ Backed up session_metadata/")

    print(f"✅ Backup complete: {BACKUP_DIR}\n")


def get_session_metadata(session_id: str) -> Dict[str, str]:
    """Get metadata for a session from old metadata files"""
    metadata_file = OLD_SESSION_METADATA_DIR / f"metadata_{session_id}.csv"

    default_metadata = {
        "exam_name": "Legacy Exam (Migrated)",
        "subject": "General",
        "duration_minutes": "25",
        "passing_percentage": "40",
        "question_count": "0",
        "created_at": "2025-11-01 00:00:00",
        "created_by": "admin",
        "allowed_students": "ALL"
    }

    if not metadata_file.exists():
        return default_metadata

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    key = row[0].lower().replace("_", "_")
                    value = row[1]
                    if key == "exam_name":
                        default_metadata["exam_name"] = value
                    elif key == "subject":
                        default_metadata["subject"] = value
                    elif key == "duration_minutes":
                        default_metadata["duration_minutes"] = value
                    elif key == "passing_percentage":
                        default_metadata["passing_percentage"] = value
                    elif key == "question_count":
                        default_metadata["question_count"] = value
                    elif key == "created_at":
                        default_metadata["created_at"] = value
                    elif key == "allowed_students":
                        # Convert comma-separated to semicolon-separated
                        default_metadata["allowed_students"] = value.replace(",", ";")
    except Exception as e:
        print(f"    ⚠️  Error reading metadata for {session_id}: {e}")

    return default_metadata


def get_image_urls(session_id: str) -> Dict[int, str]:
    """Get image URLs for a session from generated folder"""
    image_urls = {}
    image_urls_file = GENERATED_DIR / session_id / "image_urls.csv"

    if not image_urls_file.exists():
        return image_urls

    try:
        with open(image_urls_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    question_idx = int(row[0])
                    url = row[1].strip()
                    if url:
                        image_urls[question_idx] = url
    except Exception as e:
        print(f"    ⚠️  Error reading image URLs for {session_id}: {e}")

    return image_urls


def migrate_answer_keys() -> Tuple[Dict[str, List[Dict]], Dict[str, int]]:
    """
    Migrate old answer_key_*.csv to normalized questions.csv
    Returns: (questions_by_exam, exam_question_counts)
    """
    print("📝 Migrating answer keys to questions.csv...")

    questions_by_exam = {}  # exam_id -> list of questions
    exam_question_counts = {}  # exam_id -> question_count
    question_id = 1

    if not OLD_ANSWER_KEYS_DIR.exists():
        print("  ⚠️  No answer_keys directory found")
        return questions_by_exam, exam_question_counts

    for answer_key_file in sorted(OLD_ANSWER_KEYS_DIR.glob("answer_key_*.csv")):
        session_id = answer_key_file.stem.replace("answer_key_", "")

        try:
            with open(answer_key_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)

                for row in reader:
                    if len(row) < 2:
                        continue

                    # Answer key is a string like "1234"
                    answer_key_string = row[1].strip()

                    if not answer_key_string:
                        continue

                    # Get image URLs for this session
                    image_urls = get_image_urls(session_id)

                    # Create one question per digit
                    questions = []
                    for idx, correct_option in enumerate(answer_key_string, start=1):
                        if correct_option not in '1234':
                            continue

                        question = {
                            "question_id": question_id,
                            "exam_id": session_id,
                            "question_order": idx,
                            "correct_option": correct_option,
                            "marks": "1",
                            "image_url": image_urls.get(idx, "")
                        }
                        questions.append(question)
                        question_id += 1

                    questions_by_exam[session_id] = questions
                    exam_question_counts[session_id] = len(questions)
                    print(f"  ✓ {session_id}: {len(questions)} questions")

        except Exception as e:
            print(f"  ✗ Error processing {answer_key_file.name}: {e}")

    print(f"✅ Migrated {len(questions_by_exam)} exams\n")
    return questions_by_exam, exam_question_counts


def migrate_submissions() -> Tuple[List[Dict], List[Dict]]:
    """
    Migrate old answers_*.csv to submissions.csv + student_answers.csv
    Returns: (submissions, student_answers)
    """
    print("📊 Migrating student submissions...")

    submissions = []
    student_answers = []
    submission_id = 1

    if not OLD_ANSWERS_DIR.exists():
        print("  ⚠️  No answers directory found")
        return submissions, student_answers

    for answers_file in sorted(OLD_ANSWERS_DIR.glob("answers_*.csv")):
        session_id = answers_file.stem.replace("answers_", "")

        try:
            with open(answers_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)

                if not header:
                    continue

                # Find Q1, Q2, Q3... columns
                question_columns = []
                for i, col in enumerate(header):
                    if col.startswith('Q') and col[1:].isdigit():
                        question_columns.append((i, int(col[1:])))

                for row in reader:
                    if len(row) < 5:
                        continue

                    student_id = row[0]
                    # row[1] is session_id (redundant)
                    submitted_at = row[2] if len(row) > 2 else ""
                    score = row[3] if len(row) > 3 else "0"
                    total_marks = row[4] if len(row) > 4 else "0"

                    # Create submission
                    submission = {
                        "submission_id": submission_id,
                        "exam_id": session_id,
                        "student_id": student_id,
                        "submitted_at": submitted_at,
                        "score": score,
                        "total_marks": total_marks,
                        "time_taken_seconds": "",
                        "ip_address": "",
                        "device_info": "",
                        "status": "completed"
                    }
                    submissions.append(submission)

                    # Create student answers
                    for col_idx, question_order in question_columns:
                        if col_idx < len(row):
                            selected = row[col_idx].strip()

                            # Convert Bengali to number
                            option_map = {'ক': '1', 'খ': '2', 'গ': '3', 'ঘ': '4'}
                            selected_option = option_map.get(selected, "0")

                            if selected_option != "0":
                                answer = {
                                    "submission_id": submission_id,
                                    "question_order": question_order,
                                    "selected_option": selected_option,
                                    "is_correct": "",  # Will be calculated
                                    "time_spent_seconds": ""
                                }
                                student_answers.append(answer)

                    submission_id += 1

            print(f"  ✓ {session_id}: {len([s for s in submissions if s['exam_id'] == session_id])} submissions")

        except Exception as e:
            print(f"  ✗ Error processing {answers_file.name}: {e}")

    print(f"✅ Migrated {len(submissions)} submissions, {len(student_answers)} answers\n")
    return submissions, student_answers


def create_exams_csv(questions_by_exam: Dict[str, List[Dict]], exam_question_counts: Dict[str, int]):
    """Create exams.csv from session metadata and answer keys"""
    print("📋 Creating exams.csv...")

    exams = []

    # Get all unique exam IDs
    all_exam_ids = set(questions_by_exam.keys())

    for exam_id in sorted(all_exam_ids):
        metadata = get_session_metadata(exam_id)
        question_count = exam_question_counts.get(exam_id, 0)

        exam = {
            "exam_id": exam_id,
            "exam_name": metadata["exam_name"],
            "subject": metadata["subject"],
            "duration_minutes": metadata["duration_minutes"],
            "passing_percentage": metadata["passing_percentage"],
            "question_count": str(question_count),
            "created_at": metadata["created_at"],
            "created_by": metadata.get("created_by", "admin"),
            "status": "active",
            "allowed_students": metadata["allowed_students"]
        }
        exams.append(exam)

    # Write exams.csv
    with open(EXAMS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "exam_id", "exam_name", "subject", "duration_minutes",
            "passing_percentage", "question_count", "created_at",
            "created_by", "status", "allowed_students"
        ])
        writer.writeheader()
        writer.writerows(exams)

    print(f"✅ Created exams.csv with {len(exams)} exams\n")


def write_normalized_files(questions_by_exam: Dict[str, List[Dict]],
                           submissions: List[Dict],
                           student_answers: List[Dict]):
    """Write all normalized CSV files"""
    print("💾 Writing normalized CSV files...")

    # Write questions.csv
    all_questions = []
    for questions in questions_by_exam.values():
        all_questions.extend(questions)

    with open(QUESTIONS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "question_id", "exam_id", "question_order",
            "correct_option", "marks", "image_url"
        ])
        writer.writeheader()
        writer.writerows(all_questions)
    print(f"  ✓ questions.csv: {len(all_questions)} questions")

    # Write submissions.csv
    with open(SUBMISSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "submission_id", "exam_id", "student_id", "submitted_at",
            "score", "total_marks", "time_taken_seconds",
            "ip_address", "device_info", "status"
        ])
        writer.writeheader()
        writer.writerows(submissions)
    print(f"  ✓ submissions.csv: {len(submissions)} submissions")

    # Calculate is_correct for student answers
    # Build a lookup: (exam_id, question_order) -> correct_option
    correct_answers_lookup = {}
    for questions in questions_by_exam.values():
        for q in questions:
            key = (q["exam_id"], q["question_order"])
            correct_answers_lookup[key] = q["correct_option"]

    # Build submission_id -> exam_id mapping
    submission_exam_map = {s["submission_id"]: s["exam_id"] for s in submissions}

    # Update is_correct field
    for answer in student_answers:
        submission_id = answer["submission_id"]
        exam_id = submission_exam_map.get(submission_id)
        question_order = answer["question_order"]

        key = (exam_id, question_order)
        correct_option = correct_answers_lookup.get(key)

        if correct_option:
            answer["is_correct"] = "true" if answer["selected_option"] == correct_option else "false"
        else:
            answer["is_correct"] = ""

    # Write student_answers.csv
    with open(STUDENT_ANSWERS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "submission_id", "question_order", "selected_option",
            "is_correct", "time_spent_seconds"
        ])
        writer.writeheader()
        writer.writerows(student_answers)
    print(f"  ✓ student_answers.csv: {len(student_answers)} answers")

    print("✅ All normalized files written\n")


def main():
    """Main migration process"""
    print("\n" + "="*70)
    print("  CSV NORMALIZATION MIGRATION")
    print("="*70 + "\n")

    print("This script will convert your old CSV format to normalized structure.")
    print("Your old files will be backed up to: csv_backup_old_format/\n")

    response = input("Continue with migration? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Migration cancelled")
        return

    print()

    # Step 1: Backup
    backup_old_files()

    # Step 2: Migrate answer keys
    questions_by_exam, exam_question_counts = migrate_answer_keys()

    # Step 3: Migrate submissions
    submissions, student_answers = migrate_submissions()

    # Step 4: Create exams.csv
    create_exams_csv(questions_by_exam, exam_question_counts)

    # Step 5: Write normalized files
    write_normalized_files(questions_by_exam, submissions, student_answers)

    # Summary
    print("="*70)
    print("  MIGRATION COMPLETE!")
    print("="*70)
    print("\n📊 Summary:")
    print(f"  • Exams: {len(questions_by_exam)}")
    print(f"  • Questions: {sum(len(q) for q in questions_by_exam.values())}")
    print(f"  • Submissions: {len(submissions)}")
    print(f"  • Student Answers: {len(student_answers)}")
    print(f"\n📦 Backup: {BACKUP_DIR}")
    print(f"\n📁 New Files:")
    print(f"  • {EXAMS_FILE}")
    print(f"  • {QUESTIONS_FILE}")
    print(f"  • {SUBMISSIONS_FILE}")
    print(f"  • {STUDENT_ANSWERS_FILE}")
    print("\n⚠️  Next Steps:")
    print("  1. Review the migrated files")
    print("  2. Update your application code to use new format")
    print("  3. Test thoroughly before deploying")
    print("  4. Keep backup until migration is verified\n")


if __name__ == "__main__":
    main()
