#!/usr/bin/env python3
"""
Usage Examples for New CSV Structure

This file demonstrates how to use the CSV Manager in your application.
"""

from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.csv_manager import get_csv_manager


def example_1_create_session():
    """Example: Create a new exam session"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Create New Session")
    print("="*60)

    manager = get_csv_manager("web/data")

    # Create session data
    session_data = {
        "session_id": "session_example_001",
        "content_hash": "abc123def456",
        "question_count": "15",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": "2025-12-31 23:59:59",
        "status": "active",
        "exam_duration_minutes": "30",
        "created_by": "admin",
        "version": "2.0"
    }

    # Write to CSV
    manager.write("sessions", [session_data])

    print("✓ Session created:", session_data["session_id"])
    print()


def example_2_add_answer_keys():
    """Example: Add answer keys for a session"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Add Answer Keys")
    print("="*60)

    manager = get_csv_manager("web/data")

    # Answer key: 1=ক, 2=খ, 3=গ, 4=ঘ
    answer_key_string = "12342134"  # 8 questions

    answer_keys = []
    for i, correct_option in enumerate(answer_key_string):
        answer_key = {
            "answer_key_id": manager.generate_id("AK"),
            "session_id": "session_example_001",
            "question_index": str(i),
            "correct_option": correct_option,
            "marks": "1",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "2.0"
        }
        answer_keys.append(answer_key)

    manager.write("answer_keys", answer_keys)

    print(f"✓ Added {len(answer_keys)} answer keys")
    print()


def example_3_register_student():
    """Example: Register a new student"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Register Student")
    print("="*60)

    manager = get_csv_manager("web/data")

    student_data = {
        "student_id": "STU12345",
        "name": "Ahmed Khan",
        "email": "ahmed@example.com",
        "institution": "BUET",
        "batch": "2024",
        "registration_date": datetime.now().strftime("%Y-%m-%d"),
        "status": "active",
        "version": "2.0"
    }

    manager.write("students", [student_data])

    print("✓ Student registered:", student_data["name"])
    print()


def example_4_start_exam():
    """Example: Student starts an exam"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Start Exam Session")
    print("="*60)

    manager = get_csv_manager("web/data")

    # Check if student exists
    student = manager.read_by_id("students", "STU12345")
    if not student:
        print("✗ Student not found")
        return

    # Check if session exists
    session = manager.read_by_id("sessions", "session_example_001")
    if not session:
        print("✗ Session not found")
        return

    # Create exam attempt
    attempt_data = {
        "attempt_id": manager.generate_id("ATT"),
        "student_id": "STU12345",
        "session_id": "session_example_001",
        "exam_id": "EXM001",
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "submit_time": "",
        "time_taken_seconds": "",
        "status": "in_progress",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "version": "2.0"
    }

    manager.write("student_sessions", [attempt_data])

    print("✓ Exam started for student STU12345")
    print(f"  Attempt ID: {attempt_data['attempt_id']}")
    print()

    return attempt_data["attempt_id"]


def example_5_submit_answers(attempt_id: str):
    """Example: Student submits answers"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Submit Answers")
    print("="*60)

    manager = get_csv_manager("web/data")

    # Student's answers (8 questions, answers: ক, খ, গ, ঘ, ক, খ, গ, ঘ)
    # Map to numbers: ক=1, খ=2, গ=3, ঘ=4
    student_answers = ["1", "2", "3", "4", "1", "2", "3", "4"]

    # Get correct answers
    answer_keys = manager.read(
        "answer_keys",
        filter_fn=lambda r: r.get("session_id") == "session_example_001"
    )

    # Sort by question_index
    answer_keys.sort(key=lambda x: int(x.get("question_index", 0)))

    # Build answer key map
    correct_answers = {int(key["question_index"]): key["correct_option"]
                       for key in answer_keys}

    # Create answer records
    answer_records = []
    correct_count = 0

    for i, selected_option in enumerate(student_answers):
        is_correct = selected_option == correct_answers.get(i, "")
        if is_correct:
            correct_count += 1

        answer_data = {
            "answer_id": manager.generate_id("ANS"),
            "attempt_id": attempt_id,
            "question_index": str(i),
            "selected_option": selected_option,
            "is_correct": "true" if is_correct else "false",
            "marks_awarded": "1" if is_correct else "0",
            "answered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "2.0"
        }
        answer_records.append(answer_data)

    # Write answers
    manager.write("answers", answer_records)

    # Update attempt status
    manager.update(
        "student_sessions",
        attempt_id,
        {
            "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "time_taken_seconds": "1250",  # ~20 minutes
            "status": "submitted"
        },
        user_id="STU12345"
    )

    # Create submission record
    total_marks = len(student_answers)
    marks_obtained = correct_count
    percentage = (marks_obtained / total_marks) * 100
    result = "pass" if percentage >= 40 else "fail"

    submission_data = {
        "submission_id": manager.generate_id("SUB"),
        "attempt_id": attempt_id,
        "total_marks": str(total_marks),
        "marks_obtained": str(marks_obtained),
        "percentage": f"{percentage:.2f}",
        "result": result,
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "graded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "graded_by": "auto",
        "version": "2.0"
    }

    manager.write("submissions", [submission_data])

    print(f"✓ Answers submitted and graded")
    print(f"  Total questions: {total_marks}")
    print(f"  Correct answers: {marks_obtained}")
    print(f"  Percentage: {percentage:.1f}%")
    print(f"  Result: {result.upper()}")
    print()


def example_6_query_data():
    """Example: Query and analyze data"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Query Data")
    print("="*60)

    manager = get_csv_manager("web/data")

    # Get all active sessions
    active_sessions = manager.read(
        "sessions",
        filter_fn=lambda r: r.get("status") == "active"
    )
    print(f"✓ Active sessions: {len(active_sessions)}")

    # Get all students
    students = manager.read("students")
    print(f"✓ Total students: {len(students)}")

    # Get all submitted attempts
    submitted_attempts = manager.read(
        "student_sessions",
        filter_fn=lambda r: r.get("status") == "submitted"
    )
    print(f"✓ Submitted attempts: {len(submitted_attempts)}")

    # Get all passing submissions
    passing_submissions = manager.read(
        "submissions",
        filter_fn=lambda r: r.get("result") == "pass"
    )
    print(f"✓ Passing submissions: {len(passing_submissions)}")

    print()


def example_7_analytics():
    """Example: Analytics and reporting"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Analytics")
    print("="*60)

    manager = get_csv_manager("web/data")

    # Question difficulty analysis: Which questions are hardest?
    answers = manager.read("answers")

    question_stats = {}
    for answer in answers:
        q_index = int(answer.get("question_index", 0))
        is_correct = answer.get("is_correct") == "true"

        if q_index not in question_stats:
            question_stats[q_index] = {"correct": 0, "total": 0}

        question_stats[q_index]["total"] += 1
        if is_correct:
            question_stats[q_index]["correct"] += 1

    print("Question Difficulty (% correct):")
    for q_index in sorted(question_stats.keys()):
        stats = question_stats[q_index]
        if stats["total"] > 0:
            pct = (stats["correct"] / stats["total"]) * 100
            difficulty = "Easy" if pct > 70 else "Medium" if pct > 40 else "Hard"
            print(f"  Q{q_index + 1}: {pct:.1f}% ({difficulty})")

    print()


def example_8_cleanup():
    """Example: Clean up test data"""
    print("\n" + "="*60)
    print("EXAMPLE 8: Clean Up Test Data")
    print("="*60)

    manager = get_csv_manager("web/data")

    # Delete test session
    deleted = manager.delete("sessions", "session_example_001", user_id="admin")
    print(f"✓ Session deleted: {deleted}")

    # Note: In production, you'd also need to delete related records
    # (answer keys, student sessions, answers, submissions)
    # This is handled automatically if you implement CASCADE delete logic

    print()


def run_all_examples():
    """Run all examples in sequence"""
    print("\n" + "="*70)
    print("CSV MANAGER USAGE EXAMPLES")
    print("="*70)

    # Run examples
    example_1_create_session()
    example_2_add_answer_keys()
    example_3_register_student()
    attempt_id = example_4_start_exam()

    if attempt_id:
        example_5_submit_answers(attempt_id)
        example_6_query_data()
        example_7_analytics()
        # Uncomment to clean up:
        # example_8_cleanup()

    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Run all examples
    run_all_examples()

    # Or run individual examples:
    # example_1_create_session()
    # example_6_query_data()
