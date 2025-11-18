# Normalized CSV Database Schema

## Overview
This document describes the normalized CSV structure for the MCQ application.
All CSV files use UTF-8 encoding and follow strict schema rules.

---

## 1. EXAMS (web/exams.csv)

**Purpose**: Central registry of all exams (replaces metadata_*.csv files)

**Format**: Horizontal (one exam per row)

```csv
Exam_ID,Exam_Name,Subject,Duration_Minutes,Passing_Percentage,Question_Count,Created_At,Created_By,Status,Allowed_Students
session_079bc94e,Physics Midterm,Physics,25,40,10,2025-11-18 10:30:00,admin,active,stu1;stu2;stu3
session_26d60f60,Math Quiz,Mathematics,30,50,15,2025-11-18 11:00:00,admin,active,ALL
```

**Columns**:
- `Exam_ID`: Unique identifier (session_xxxxx)
- `Exam_Name`: Human-readable exam name
- `Subject`: Subject/topic
- `Duration_Minutes`: Time limit in minutes
- `Passing_Percentage`: Minimum % to pass (0-100)
- `Question_Count`: Number of questions
- `Created_At`: Timestamp when exam was created
- `Created_By`: Admin who created it
- `Status`: active|archived|draft
- `Allowed_Students`: Semicolon-separated student IDs or "ALL"

---

## 2. QUESTIONS (web/questions.csv)

**Purpose**: Store questions with their correct answers and metadata

**Format**: One question per row

```csv
Question_ID,Exam_ID,Question_Order,Correct_Option,Marks,Image_URL
1,session_079bc94e,1,1,1,https://imgur.com/xyz.png
2,session_079bc94e,2,3,1,
3,session_079bc94e,3,2,1,https://example.com/fig2.jpg
```

**Columns**:
- `Question_ID`: Auto-incrementing unique ID
- `Exam_ID`: Which exam this question belongs to
- `Question_Order`: Position in exam (1, 2, 3...)
- `Correct_Option`: Correct answer (1=ক, 2=খ, 3=গ, 4=ঘ)
- `Marks`: Points for this question (usually 1)
- `Image_URL`: Optional image URL (empty if no image)

**Benefits**:
- ✅ Can query "what's the answer to Q3?"
- ✅ Can have different marks per question
- ✅ Can store image URLs per question
- ✅ Can reuse questions across exams (future)

---

## 3. SUBMISSIONS (web/submissions.csv)

**Purpose**: Track exam submissions (one per student per exam)

**Format**: One submission per row

```csv
Submission_ID,Exam_ID,Student_ID,Submitted_At,Score,Total_Marks,Time_Taken_Seconds,IP_Address,Device_Info,Status
1,session_079bc94e,stu001,2025-11-18 14:30:00,8,10,1200,192.168.1.1,Desktop - Chrome - Windows,completed
2,session_079bc94e,stu002,2025-11-18 14:35:00,6,10,900,192.168.1.2,Mobile - Safari - iOS,completed
3,session_26d60f60,stu001,2025-11-18 15:00:00,12,15,1800,192.168.1.1,Desktop - Chrome - Windows,completed
```

**Columns**:
- `Submission_ID`: Auto-incrementing unique ID
- `Exam_ID`: Which exam was submitted
- `Student_ID`: Who submitted
- `Submitted_At`: When they submitted
- `Score`: Points earned
- `Total_Marks`: Total possible points
- `Time_Taken_Seconds`: How long they took
- `IP_Address`: Submission IP
- `Device_Info`: Browser/device info
- `Status`: completed|in_progress|abandoned

**Unique Constraint**: (Exam_ID, Student_ID) - one submission per student per exam

---

## 4. STUDENT_ANSWERS (web/student_answers.csv)

**Purpose**: Store individual question responses

**Format**: One answer per row

```csv
Submission_ID,Question_Order,Selected_Option,Is_Correct,Time_Spent_Seconds
1,1,1,true,45
1,2,2,false,60
1,3,3,true,55
2,1,2,false,30
2,2,3,false,40
```

**Columns**:
- `Submission_ID`: Links to submissions.csv
- `Question_Order`: Which question (1, 2, 3...)
- `Selected_Option`: What student answered (1=ক, 2=খ, 3=গ, 4=ঘ)
- `Is_Correct`: true|false
- `Time_Spent_Seconds`: Time on this question (optional)

**Benefits**:
- ✅ Can query "who got Q5 wrong?"
- ✅ Can analyze question difficulty
- ✅ Can track per-question time
- ✅ Can build detailed analytics

---

## 5. ACTIVITY_LOGS (web/activity_logs/activity_YYYY-MM-DD.csv)

**Purpose**: Track student activity for security/auditing

**Format**: Daily files, one activity per row

```csv
Timestamp,Student_ID,Activity_Type,Exam_ID,Submission_ID,IP_Address,Device_Type,Browser,OS,User_Agent,Details
2025-11-18 10:00:00,stu001,login,,,192.168.1.1,Desktop,Chrome,Windows,Mozilla/5.0...,
2025-11-18 10:05:00,stu001,exam_start,session_079bc94e,,192.168.1.1,Desktop,Chrome,Windows,Mozilla/5.0...,
2025-11-18 10:25:00,stu001,exam_submit,session_079bc94e,1,192.168.1.1,Desktop,Chrome,Windows,Mozilla/5.0...,Score: 8/10
2025-11-18 10:30:00,stu001,logout,,,192.168.1.1,Desktop,Chrome,Windows,Mozilla/5.0...,
```

**Activity Types**:
- `login`: Student logged in
- `logout`: Student logged out
- `exam_start`: Student started an exam
- `exam_submit`: Student submitted an exam
- `tab_switch`: Student switched tabs (potential cheating)
- `session_resume`: Returned to exam in progress

---

## 6. LOGIN_SESSIONS (web/login_sessions/active_sessions.csv)

**Purpose**: Track active login sessions, prevent concurrent logins

**Format**: One session per row

```csv
Session_ID,Student_ID,Is_Admin,Login_Time,Last_Activity,Logout_Time,IP_Address,Device_Info,Status
abc123,stu001,false,2025-11-18 10:00:00,2025-11-18 10:30:00,2025-11-18 10:35:00,192.168.1.1,Desktop-Chrome-Windows,terminated
def456,stu002,false,2025-11-18 11:00:00,2025-11-18 11:15:00,,192.168.1.2,Mobile-Safari-iOS,active
xyz789,admin,true,2025-11-18 09:00:00,2025-11-18 12:00:00,,192.168.1.100,Desktop-Firefox-Linux,active
```

**Status Values**:
- `active`: Currently logged in
- `terminated`: Logged out normally
- `expired`: Session timed out
- `forced_logout`: Admin forced logout

---

## Schema Comparison

### OLD vs NEW: Answer Keys

**OLD** (answer_key_session_*.csv):
```csv
Session_ID,Answer_Key
session_079bc94e,1234
```

**NEW** (questions.csv):
```csv
Question_ID,Exam_ID,Question_Order,Correct_Option,Marks,Image_URL
1,session_079bc94e,1,1,1,
2,session_079bc94e,2,2,1,
3,session_079bc94e,3,3,1,
4,session_079bc94e,4,4,1,
```

### OLD vs NEW: Student Answers

**OLD** (answers_session_*.csv):
```csv
Student_ID,Session_ID,Timestamp,Marks,Total,Q1,Q2,Q3,Q4
stu001,session_079bc94e,2025-11-18 14:30:00,3,4,ক,খ,গ,ঘ
```

**NEW** (submissions.csv + student_answers.csv):

submissions.csv:
```csv
Submission_ID,Exam_ID,Student_ID,Submitted_At,Score,Total_Marks,Time_Taken_Seconds,IP_Address,Device_Info,Status
1,session_079bc94e,stu001,2025-11-18 14:30:00,3,4,1200,192.168.1.1,Desktop-Chrome-Windows,completed
```

student_answers.csv:
```csv
Submission_ID,Question_Order,Selected_Option,Is_Correct,Time_Spent_Seconds
1,1,1,true,
1,2,2,true,
1,3,3,true,
1,4,4,true,
```

---

## Migration Strategy

1. **Create new files** with normalized structure
2. **Migrate data** from old format to new format
3. **Keep old files** as backup (rename to .old)
4. **Update application code** to use new format
5. **Test thoroughly** before deploying

---

## File Locations

```
web/
├── exams.csv                          # All exams
├── questions.csv                      # All questions with answers
├── submissions.csv                    # All exam submissions
├── student_answers.csv                # All individual answers
├── activity_logs/
│   ├── activity_2025-11-18.csv       # Daily activity logs
│   └── activity_2025-11-19.csv
└── login_sessions/
    └── active_sessions.csv            # Active login sessions
```

---

## Benefits of Normalized Structure

1. ✅ **No Dynamic Columns**: Fixed schema, easier to query
2. ✅ **No Duplicate Data**: Session_ID not stored in file content
3. ✅ **Better Queries**: Can filter/aggregate easily
4. ✅ **Scalability**: Can handle thousands of submissions
5. ✅ **Analytics**: Can analyze question difficulty, student performance
6. ✅ **Data Integrity**: Easier to validate and maintain
7. ✅ **Unique Constraints**: Prevent duplicate submissions
8. ✅ **Future-Proof**: Easy to migrate to SQLite later
