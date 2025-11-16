# CSV Structure - Quick Start Guide

## 🚀 Getting Started with New CSV Structure

### Prerequisites
- Python 3.8+
- Existing MCQ application running

---

## Option 1: Fresh Installation (No Existing Data)

If you're starting fresh with no existing data:

```bash
cd /home/user/mcq

# 1. Create data directory structure
mkdir -p web/data/{core,transactions,audit,backups,migrations}

# 2. Initialize schema version
echo "2.0" > web/data/schema_version.txt

# 3. Test the CSV manager
python3 web/utils/csv_usage_examples.py
```

**You're done!** The CSV files will be created automatically as you add data.

---

## Option 2: Migration from Old Structure (With Existing Data)

If you have existing CSV files in the old structure:

### Step 1: Backup Current Data

```bash
cd /home/user/mcq

# Create timestamped backup
BACKUP_DIR="web_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup all CSV directories
cp -r web/answers "$BACKUP_DIR/"
cp -r web/answer_keys "$BACKUP_DIR/"
cp -r web/sessions "$BACKUP_DIR/" 2>/dev/null || true

echo "Backup created: $BACKUP_DIR"
```

### Step 2: Run Migration (Dry Run First)

```bash
# Test migration without making changes
python3 web/utils/migrate_to_v2.py \
  --source web/ \
  --dest web/data/ \
  --dry-run
```

Review the output to ensure everything looks correct.

### Step 3: Run Actual Migration

```bash
# Perform the migration
python3 web/utils/migrate_to_v2.py \
  --source web/ \
  --dest web/data/
```

### Step 4: Validate Migrated Data

```bash
# Validate all CSV files
python3 web/utils/validate_csv.py --data-dir web/data/
```

If validation passes, you're ready to go!

### Step 5: Update Application Code

See "Integration Guide" below.

---

## Integration Guide

### Replace Old CSV Operations

#### Old Way (Before):
```python
# app.py - Old way
import csv

# Write answer key
answer_key_file = ANSWER_KEYS_DIR / f"answer_key_{session_id}.csv"
with open(answer_key_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Session_ID", "Answer_Key"])
    writer.writerow([session_id, correct_answers_str])

# Read student answers
csv_file = ANSWERS_DIR / f"answers_{session_id}.csv"
with open(csv_file, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Process row...
```

#### New Way (After):
```python
# app.py - New way
from utils.csv_manager import get_csv_manager

manager = get_csv_manager()

# Write answer keys (normalized)
answer_keys = []
for i, correct_option in enumerate(correct_answers_str):
    answer_keys.append({
        "answer_key_id": manager.generate_id("AK"),
        "session_id": session_id,
        "question_index": str(i),
        "correct_option": correct_option,
        "marks": "1",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "2.0"
    })

manager.write("answer_keys", answer_keys)

# Read student answers for a session
answers = manager.read(
    "answers",
    filter_fn=lambda r: r.get("session_id") == session_id
)
```

---

## Common Operations

### 1. Create a New Session

```python
from utils.csv_manager import get_csv_manager
from datetime import datetime

manager = get_csv_manager()

session_data = {
    "session_id": f"session_{unique_id}",
    "content_hash": content_hash,
    "question_count": str(num_questions),
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "expires_at": "2025-12-31 23:59:59",
    "status": "active",
    "exam_duration_minutes": "25",
    "created_by": "admin",
    "version": "2.0"
}

manager.write("sessions", [session_data])
```

### 2. Save Answer Keys

```python
# Convert "1234" → individual answer key rows
answer_key_string = "1234"  # 1=ক, 2=খ, 3=গ, 4=ঘ

answer_keys = []
for i, correct_option in enumerate(answer_key_string):
    answer_keys.append({
        "answer_key_id": manager.generate_id("AK"),
        "session_id": session_id,
        "question_index": str(i),
        "correct_option": correct_option,
        "marks": "1",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "2.0"
    })

manager.write("answer_keys", answer_keys)
```

### 3. Start Student Exam

```python
# Create student record (first time only)
student_data = {
    "student_id": student_id,
    "name": f"Student {student_id}",
    "email": f"{student_id}@example.com",
    "institution": "Unknown",
    "batch": "2025",
    "registration_date": datetime.now().strftime("%Y-%m-%d"),
    "status": "active",
    "version": "2.0"
}

if not manager.exists("students", student_id):
    manager.write("students", [student_data])

# Create exam attempt
attempt_data = {
    "attempt_id": manager.generate_id("ATT"),
    "student_id": student_id,
    "session_id": session_id,
    "exam_id": "EXM001",
    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "submit_time": "",
    "time_taken_seconds": "",
    "status": "in_progress",
    "ip_address": request.remote_addr,
    "user_agent": request.user_agent.string,
    "version": "2.0"
}

manager.write("student_sessions", [attempt_data])
```

### 4. Submit Student Answers

```python
# Get attempt
attempts = manager.read(
    "student_sessions",
    filter_fn=lambda r: r["student_id"] == student_id and r["session_id"] == session_id
)

if not attempts:
    return error("No active attempt found")

attempt_id = attempts[0]["attempt_id"]

# Get answer keys
answer_keys = manager.read(
    "answer_keys",
    filter_fn=lambda r: r["session_id"] == session_id
)

# Build correct answers map
correct_answers = {int(key["question_index"]): key["correct_option"]
                   for key in answer_keys}

# Save answers
answer_records = []
correct_count = 0

for question_index, selected_option in student_answers.items():
    is_correct = selected_option == correct_answers.get(question_index, "")
    if is_correct:
        correct_count += 1

    answer_records.append({
        "answer_id": manager.generate_id("ANS"),
        "attempt_id": attempt_id,
        "question_index": str(question_index),
        "selected_option": selected_option,
        "is_correct": "true" if is_correct else "false",
        "marks_awarded": "1" if is_correct else "0",
        "answered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "2.0"
    })

manager.write("answers", answer_records)

# Update attempt status
manager.update(
    "student_sessions",
    attempt_id,
    {
        "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "submitted"
    },
    user_id=student_id
)
```

### 5. Query Data

```python
# Get all active sessions
active_sessions = manager.read(
    "sessions",
    filter_fn=lambda r: r["status"] == "active"
)

# Get student's submission
submission = manager.read(
    "submissions",
    filter_fn=lambda r: r["attempt_id"] == attempt_id
)

# Count students who passed
passing_count = manager.count(
    "submissions",
    filter_fn=lambda r: r["result"] == "pass"
)
```

---

## Maintenance Tasks

### Daily Backup
```bash
# Create backup
python3 -c "from web.utils.csv_manager import get_csv_manager; \
            get_csv_manager().backup_all('daily_$(date +%Y%m%d)')"
```

### Validate Data
```bash
# Run validation
python3 web/utils/validate_csv.py --data-dir web/data/
```

### View Audit Log
```bash
# See recent changes
tail -n 50 web/data/audit/audit_log.csv
```

---

## Rollback (If Needed)

If something goes wrong, you can rollback:

```bash
# Option 1: Use the auto-generated rollback script
./rollback_migration.sh

# Option 2: Manual rollback
rm -rf web/data/
mv web_backup_YYYYMMDD_HHMMSS/* web/
```

---

## Performance Tips

### 1. Use Filters to Reduce I/O
```python
# ❌ Bad: Read all then filter in Python
all_answers = manager.read("answers")
filtered = [a for a in all_answers if a["session_id"] == session_id]

# ✅ Good: Filter at read time
filtered = manager.read(
    "answers",
    filter_fn=lambda r: r["session_id"] == session_id
)
```

### 2. Batch Writes
```python
# ❌ Bad: Multiple writes
for answer in answers:
    manager.write("answers", [answer])

# ✅ Good: Single batch write
manager.write("answers", answers)
```

### 3. Cache Frequently Used Data
```python
# Cache answer keys for a session
session_answer_keys = {}

def get_answer_keys(session_id):
    if session_id not in session_answer_keys:
        session_answer_keys[session_id] = manager.read(
            "answer_keys",
            filter_fn=lambda r: r["session_id"] == session_id
        )
    return session_answer_keys[session_id]
```

---

## Troubleshooting

### Issue: "CSVLockError: Could not acquire lock"

**Cause:** Another process is writing to the CSV file.

**Solution:** The lock will retry. If it persists, check for stale `.lock` files:
```bash
find web/data/ -name ".*.lock" -delete
```

### Issue: "CSVValidationError: Missing required column"

**Cause:** You're trying to write incomplete data.

**Solution:** Check the schema in `csv_manager.py` and ensure all required fields are provided.

### Issue: "Foreign key violation"

**Cause:** You're referencing a non-existent parent record.

**Solution:** Ensure parent records exist before creating child records:
```python
# Create session first
manager.write("sessions", [session_data])

# Then create answer keys (references session)
manager.write("answer_keys", answer_keys)
```

---

## Next Steps

1. ✅ Review the [detailed structure guide](CSV_STRUCTURE_UPGRADE.md)
2. ✅ Run the [usage examples](web/utils/csv_usage_examples.py)
3. ✅ Update your `app.py` to use the new CSV manager
4. ✅ Test thoroughly in development
5. ✅ Deploy to production with backups

---

## Support

For questions or issues:
1. Check the [full documentation](CSV_STRUCTURE_UPGRADE.md)
2. Review [usage examples](web/utils/csv_usage_examples.py)
3. Open an issue on GitHub

---

**Ready to get started? Run the examples:**

```bash
python3 web/utils/csv_usage_examples.py
```
