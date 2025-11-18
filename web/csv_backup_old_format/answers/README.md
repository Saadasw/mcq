# Student Answers CSV Files

This directory contains CSV files with student answers for MCQ questions.

## File Format

Each CSV file is named `answers_{session_id}.csv` where `session_id` is the unique identifier for a set of questions.

## CSV Structure

- **Student_ID**: The student's ID number
- **Session_ID**: The session identifier (same for all students taking the same exam)
- **Timestamp**: When the answers were submitted (YYYY-MM-DD HH:MM:SS)
- **Q1, Q2, Q3, ...**: Answers for each question (ক, খ, গ, or ঘ)

## Example

```csv
Student_ID,Session_ID,Timestamp,Q1,Q2,Q3,Q4
12345,session_abc123,2024-01-15 10:30:45,ক,খ,গ,ঘ
12346,session_abc123,2024-01-15 10:35:12,খ,ক,ঘ,গ
```

## Notes

- Each row represents one student's submission
- All students taking the same exam (same questions) will have the same Session_ID
- Answers are saved in Bengali: ক, খ, গ, ঘ
- Multiple submissions from the same student will create multiple rows


