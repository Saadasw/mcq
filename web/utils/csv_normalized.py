"""
Normalized CSV Database Helper Functions
Provides clean API for reading/writing normalized CSV files
"""

import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


# File paths
WEB_DIR = Path(__file__).parent.parent
EXAMS_FILE = WEB_DIR / "exams.csv"
QUESTIONS_FILE = WEB_DIR / "questions.csv"
SUBMISSIONS_FILE = WEB_DIR / "submissions.csv"
STUDENT_ANSWERS_FILE = WEB_DIR / "student_answers.csv"


class NormalizedCSVDB:
    """Interface for normalized CSV database operations"""

    # ========== EXAMS ==========

    @staticmethod
    def get_all_exams(status: str = None) -> List[Dict]:
        """Get all exams, optionally filtered by status"""
        if not EXAMS_FILE.exists():
            return []

        exams = []
        with open(EXAMS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if status is None or row.get('status') == status:
                    exams.append(row)
        return exams

    @staticmethod
    def get_exam(exam_id: str) -> Optional[Dict]:
        """Get exam by ID"""
        if not EXAMS_FILE.exists():
            return None

        with open(EXAMS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['exam_id'] == exam_id:
                    return row
        return None

    @staticmethod
    def create_exam(exam_data: Dict) -> bool:
        """Create a new exam"""
        try:
            # Check if file exists
            file_exists = EXAMS_FILE.exists()

            # Read existing exams
            existing_exams = []
            if file_exists:
                with open(EXAMS_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_exams = list(reader)

            # Check for duplicate exam_id
            if any(e['exam_id'] == exam_data['exam_id'] for e in existing_exams):
                print(f"Error: Exam {exam_data['exam_id']} already exists")
                return False

            # Add new exam
            existing_exams.append(exam_data)

            # Write back
            with open(EXAMS_FILE, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    "exam_id", "exam_name", "subject", "duration_minutes",
                    "passing_percentage", "question_count", "created_at",
                    "created_by", "status", "allowed_students"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_exams)

            return True
        except Exception as e:
            print(f"Error creating exam: {e}")
            return False

    @staticmethod
    def get_allowed_students(exam_id: str) -> List[str]:
        """Get list of allowed students for an exam"""
        exam = NormalizedCSVDB.get_exam(exam_id)
        if not exam:
            return []

        allowed_str = exam.get('allowed_students', '').strip()
        if allowed_str == 'ALL' or not allowed_str:
            return ['ALL']

        # Split by semicolon
        return [s.strip() for s in allowed_str.split(';') if s.strip()]

    # ========== QUESTIONS ==========

    @staticmethod
    def get_questions(exam_id: str) -> List[Dict]:
        """Get all questions for an exam, ordered by question_order"""
        if not QUESTIONS_FILE.exists():
            return []

        questions = []
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['exam_id'] == exam_id:
                    questions.append(row)

        # Sort by question_order
        questions.sort(key=lambda q: int(q['question_order']))
        return questions

    @staticmethod
    def create_questions(questions: List[Dict]) -> bool:
        """Create multiple questions (bulk insert)"""
        try:
            # Read existing questions
            existing_questions = []
            if QUESTIONS_FILE.exists():
                with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_questions = list(reader)

            # Generate question IDs
            max_id = 0
            if existing_questions:
                max_id = max(int(q['question_id']) for q in existing_questions)

            for i, q in enumerate(questions, start=1):
                if 'question_id' not in q:
                    q['question_id'] = str(max_id + i)

            # Add new questions
            existing_questions.extend(questions)

            # Write back
            with open(QUESTIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    "question_id", "exam_id", "question_order",
                    "correct_option", "marks", "image_url"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_questions)

            return True
        except Exception as e:
            print(f"Error creating questions: {e}")
            return False

    @staticmethod
    def get_correct_answers(exam_id: str) -> Dict[int, str]:
        """Get correct answers for an exam as {question_order: correct_option}"""
        questions = NormalizedCSVDB.get_questions(exam_id)
        return {int(q['question_order']): q['correct_option'] for q in questions}

    # ========== SUBMISSIONS ==========

    @staticmethod
    def get_submission(exam_id: str, student_id: str) -> Optional[Dict]:
        """Get a specific submission"""
        if not SUBMISSIONS_FILE.exists():
            return None

        with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['exam_id'] == exam_id and row['student_id'] == student_id:
                    return row
        return None

    @staticmethod
    def has_submitted(exam_id: str, student_id: str) -> bool:
        """Check if student has already submitted this exam"""
        return NormalizedCSVDB.get_submission(exam_id, student_id) is not None

    @staticmethod
    def get_student_submissions(student_id: str) -> List[Dict]:
        """Get all submissions for a student"""
        if not SUBMISSIONS_FILE.exists():
            return []

        submissions = []
        with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['student_id'] == student_id:
                    submissions.append(row)
        return submissions

    @staticmethod
    def get_exam_submissions(exam_id: str) -> List[Dict]:
        """Get all submissions for an exam"""
        if not SUBMISSIONS_FILE.exists():
            return []

        submissions = []
        with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['exam_id'] == exam_id:
                    submissions.append(row)
        return submissions

    @staticmethod
    def create_submission(submission_data: Dict, answers: List[Dict]) -> bool:
        """
        Create a submission with answers
        submission_data: {exam_id, student_id, submitted_at, score, total_marks, ...}
        answers: [{question_order, selected_option, is_correct}, ...]
        """
        try:
            # Check for duplicate
            if NormalizedCSVDB.has_submitted(submission_data['exam_id'],
                                             submission_data['student_id']):
                print(f"Error: Student {submission_data['student_id']} already submitted {submission_data['exam_id']}")
                return False

            # Read existing submissions
            existing_submissions = []
            if SUBMISSIONS_FILE.exists():
                with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_submissions = list(reader)

            # Generate submission ID
            max_id = 0
            if existing_submissions:
                max_id = max(int(s['submission_id']) for s in existing_submissions)
            submission_id = max_id + 1
            submission_data['submission_id'] = str(submission_id)

            # Add submission
            existing_submissions.append(submission_data)

            # Write submissions
            with open(SUBMISSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    "submission_id", "exam_id", "student_id", "submitted_at",
                    "score", "total_marks", "time_taken_seconds",
                    "ip_address", "device_info", "status"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_submissions)

            # Add submission_id to answers
            for answer in answers:
                answer['submission_id'] = str(submission_id)

            # Read existing answers
            existing_answers = []
            if STUDENT_ANSWERS_FILE.exists():
                with open(STUDENT_ANSWERS_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_answers = list(reader)

            # Add new answers
            existing_answers.extend(answers)

            # Write answers
            with open(STUDENT_ANSWERS_FILE, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    "submission_id", "question_order", "selected_option",
                    "is_correct", "time_spent_seconds"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_answers)

            return True
        except Exception as e:
            print(f"Error creating submission: {e}")
            return False

    @staticmethod
    def get_student_answers(submission_id: str) -> List[Dict]:
        """Get all answers for a submission"""
        if not STUDENT_ANSWERS_FILE.exists():
            return []

        answers = []
        with open(STUDENT_ANSWERS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['submission_id'] == submission_id:
                    answers.append(row)

        # Sort by question_order
        answers.sort(key=lambda a: int(a['question_order']))
        return answers

    # ========== UTILITY FUNCTIONS ==========

    @staticmethod
    def calculate_score(exam_id: str, student_answers: Dict[int, str]) -> tuple:
        """
        Calculate score for student answers
        Args:
            exam_id: Exam ID
            student_answers: {question_order: selected_option}
        Returns:
            (score, total_marks, answer_details)
        """
        questions = NormalizedCSVDB.get_questions(exam_id)
        correct_answers = {int(q['question_order']): q['correct_option'] for q in questions}

        score = 0
        total_marks = 0
        answer_details = []

        for question in questions:
            q_order = int(question['question_order'])
            correct = question['correct_option']
            marks = int(question['marks'])
            selected = student_answers.get(q_order, '0')

            is_correct = (selected == correct)
            if is_correct:
                score += marks
            total_marks += marks

            answer_details.append({
                'question_order': str(q_order),
                'selected_option': selected,
                'is_correct': 'true' if is_correct else 'false',
                'time_spent_seconds': ''
            })

        return score, total_marks, answer_details

    @staticmethod
    def initialize_files():
        """Create empty CSV files with headers if they don't exist"""
        # Create exams.csv
        if not EXAMS_FILE.exists():
            with open(EXAMS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "exam_id", "exam_name", "subject", "duration_minutes",
                    "passing_percentage", "question_count", "created_at",
                    "created_by", "status", "allowed_students"
                ])

        # Create questions.csv
        if not QUESTIONS_FILE.exists():
            with open(QUESTIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "question_id", "exam_id", "question_order",
                    "correct_option", "marks", "image_url"
                ])

        # Create submissions.csv
        if not SUBMISSIONS_FILE.exists():
            with open(SUBMISSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "submission_id", "exam_id", "student_id", "submitted_at",
                    "score", "total_marks", "time_taken_seconds",
                    "ip_address", "device_info", "status"
                ])

        # Create student_answers.csv
        if not STUDENT_ANSWERS_FILE.exists():
            with open(STUDENT_ANSWERS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "submission_id", "question_order", "selected_option",
                    "is_correct", "time_spent_seconds"
                ])


# Initialize files on import
NormalizedCSVDB.initialize_files()
