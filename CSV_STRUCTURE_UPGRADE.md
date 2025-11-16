# CSV Structure Upgrade Guide

## 📊 Current CSV Structure Analysis

### **Current Issues**

| Issue | Impact | Severity |
|-------|--------|----------|
| **Multiple files per session** | Hard to query across sessions | High |
| **No CSV versioning** | Schema changes break old data | High |
| **Dynamic columns (Q1, Q2...)** | Schema management difficult | Medium |
| **No data validation** | Corrupt data possible | High |
| **No file locking** | Race conditions on concurrent writes | High |
| **No backup mechanism** | Data loss risk | Critical |
| **No audit trail** | Can't track changes | Medium |
| **No indexing** | Slow lookups in large files | Medium |
| **Redundant data** | Storage waste, update anomalies | Low |

### **Current Structure**

#### 1. `exam_sessions.csv` (Global file)
```csv
Student_ID,Session_ID,Start_Time,Date
23,session_0ad719cf,2025-11-06 23:34:33,2025-11-06
```
**Problems:**
- ❌ No unique ID column
- ❌ Date is redundant (extracted from Start_Time)
- ❌ No exam metadata (duration, status)
- ❌ No session expiry tracking

#### 2. `answer_keys/answer_key_{session_id}.csv` (Per-session files)
```csv
Session_ID,Answer_Key
session_8ebac4ca,2
```
**Problems:**
- ❌ One file per session (inefficient)
- ❌ Session_ID redundant (in filename)
- ❌ No question count validation
- ❌ No created_by, created_at metadata
- ❌ No version tracking

#### 3. `answers/answers_{session_id}.csv` (Per-session files)
```csv
Student_ID,Session_ID,Timestamp,Marks,Total,Q1,Q2,Q3,...
1,session_8ebac4ca,2025-11-07 17:17:46,1,1,গ
```
**Problems:**
- ❌ One file per session (thousands of files)
- ❌ Dynamic column count (Q1, Q2, ..., Q40)
- ❌ Hard to query specific questions across students
- ❌ No submission metadata (IP, user agent, time taken)
- ❌ Can't store partial submissions efficiently

---

## 🎯 Improved CSV Structure

### **Design Principles**
1. ✅ **Normalized structure** - Minimal redundancy
2. ✅ **Single files per entity** - Easy to manage
3. ✅ **Fixed schema** - Versioned with migrations
4. ✅ **Indexing columns** - First column = primary key
5. ✅ **Metadata columns** - created_at, updated_at, version
6. ✅ **Foreign keys** - Documented relationships
7. ✅ **Audit trail** - Track all changes

---

## 📁 New File Structure

```
web/data/
├── schema_version.txt              # Current schema version (e.g., "2.0")
├── backups/                        # Automatic backups
│   ├── daily/
│   ├── before_write/
│   └── before_migration/
├── core/                           # Core entity files
│   ├── sessions.csv               # All exam sessions
│   ├── answer_keys.csv            # All answer keys
│   ├── students.csv               # Student registry
│   └── exams.csv                  # Exam definitions
├── transactions/                   # High-volume data
│   ├── student_sessions.csv       # Student exam attempts
│   ├── answers.csv                # Individual answers (normalized)
│   └── submissions.csv            # Submission metadata
└── audit/                          # Audit logs
    └── audit_log.csv              # All changes

web/utils/                          # Utility scripts (version controlled)
├── csv_manager.py                  # CSV management library
├── migrate_to_v2.py               # Migration script: v1 → v2
├── validate_csv.py                # Data validation tool
└── csv_usage_examples.py          # Usage examples
```

**Note:** Migration scripts are in `web/utils/` (version controlled), while migration backups go in `web/data/backups/before_migration/` (data directory).

---

## 📋 Detailed Schema Definitions

### **1. `core/sessions.csv`** (Exam Session Master)

```csv
session_id,content_hash,question_count,created_at,expires_at,status,exam_duration_minutes,created_by,version
session_8ebac4ca,a1b2c3d4,10,2025-11-07 10:00:00,2025-11-14 10:00:00,active,25,admin,1
session_26d60f60,e5f6g7h8,15,2025-11-06 15:30:00,2025-11-13 15:30:00,active,30,teacher1,1
session_archived1,x9y8z7w6,20,2025-10-01 09:00:00,2025-10-08 09:00:00,archived,25,admin,1
```

**Columns:**
- `session_id` (PK): Unique session identifier
- `content_hash`: Hash of questions (for cache invalidation)
- `question_count`: Number of questions
- `created_at`: Session creation timestamp
- `expires_at`: When session becomes unavailable
- `status`: `active`, `archived`, `deleted`
- `exam_duration_minutes`: Allowed exam time
- `created_by`: Who created this session
- `version`: Schema version

**Indexes:** session_id (primary)

---

### **2. `core/answer_keys.csv`** (Centralized Answer Keys)

```csv
answer_key_id,session_id,question_index,correct_option,marks,created_at,version
ak_001,session_8ebac4ca,0,2,1,2025-11-07 10:00:00,1
ak_002,session_8ebac4ca,1,3,1,2025-11-07 10:00:00,1
ak_003,session_26d60f60,0,1,1,2025-11-06 15:30:00,1
ak_004,session_26d60f60,1,4,2,2025-11-06 15:30:00,1
ak_005,session_26d60f60,2,2,1,2025-11-06 15:30:00,1
```

**Columns:**
- `answer_key_id` (PK): Unique identifier
- `session_id` (FK): → sessions.session_id
- `question_index`: 0-based question number (0, 1, 2...)
- `correct_option`: 1=ক, 2=খ, 3=গ, 4=ঘ
- `marks`: Points for this question
- `created_at`: When answer key was added
- `version`: Schema version

**Indexes:** answer_key_id (primary), session_id (foreign)

**Benefits:**
- ✅ Supports variable marks per question
- ✅ Easy to query all answers for a session
- ✅ Can update individual answers
- ✅ Supports partial answer keys

---

### **3. `core/students.csv`** (Student Registry)

```csv
student_id,name,email,institution,batch,registration_date,status,version
STU001,Saad Ahmed,saad@example.com,BUET,2024,2025-11-01,active,1
STU002,Nowshinn Khan,nowshinn@example.com,DU,2023,2025-11-02,active,1
STU003,Test Student,test@example.com,Test Institute,2025,2025-11-03,inactive,1
```

**Columns:**
- `student_id` (PK): Unique student identifier
- `name`: Full name
- `email`: Contact email
- `institution`: School/college/university
- `batch`: Batch year
- `registration_date`: When registered
- `status`: `active`, `inactive`, `suspended`
- `version`: Schema version

**Indexes:** student_id (primary), email (unique)

---

### **4. `core/exams.csv`** (Exam Definitions)

```csv
exam_id,exam_name,subject,total_marks,pass_marks,created_at,created_by,status,version
EXM001,Physics Mid-term,Physics,100,40,2025-11-01,admin,active,1
EXM002,Math Quiz 1,Mathematics,50,20,2025-11-02,teacher1,active,1
EXM003,Chemistry Final,Chemistry,150,60,2025-10-15,admin,archived,1
```

**Columns:**
- `exam_id` (PK): Unique exam identifier
- `exam_name`: Display name
- `subject`: Subject/topic
- `total_marks`: Maximum marks
- `pass_marks`: Minimum to pass
- `created_at`: Creation timestamp
- `created_by`: Creator
- `status`: `active`, `archived`, `deleted`
- `version`: Schema version

---

### **5. `transactions/student_sessions.csv`** (Student Exam Attempts)

```csv
attempt_id,student_id,session_id,exam_id,start_time,submit_time,time_taken_seconds,status,ip_address,user_agent,version
ATT001,STU001,session_8ebac4ca,EXM001,2025-11-07 10:00:00,2025-11-07 10:23:45,1425,submitted,192.168.1.1,Mozilla/5.0,1
ATT002,STU002,session_8ebac4ca,EXM001,2025-11-07 10:05:00,2025-11-07 10:29:30,1470,submitted,192.168.1.2,Chrome/120.0,1
ATT003,STU001,session_26d60f60,EXM002,2025-11-07 11:00:00,,NULL,in_progress,192.168.1.1,Mozilla/5.0,1
ATT004,STU003,session_8ebac4ca,EXM001,2025-11-07 10:10:00,2025-11-07 10:35:00,1500,time_expired,192.168.1.3,Safari/17.0,1
```

**Columns:**
- `attempt_id` (PK): Unique attempt identifier
- `student_id` (FK): → students.student_id
- `session_id` (FK): → sessions.session_id
- `exam_id` (FK): → exams.exam_id
- `start_time`: When exam started
- `submit_time`: When submitted (NULL if not submitted)
- `time_taken_seconds`: Duration in seconds
- `status`: `in_progress`, `submitted`, `time_expired`, `abandoned`
- `ip_address`: For audit trail
- `user_agent`: Browser info
- `version`: Schema version

**Indexes:** attempt_id (primary), student_id (foreign), session_id (foreign)

---

### **6. `transactions/answers.csv`** (Normalized Answers)

```csv
answer_id,attempt_id,question_index,selected_option,is_correct,marks_awarded,answered_at,version
ANS001,ATT001,0,2,true,1,2025-11-07 10:05:30,1
ANS002,ATT001,1,1,false,0,2025-11-07 10:08:15,1
ANS003,ATT002,0,2,true,1,2025-11-07 10:10:20,1
ANS004,ATT002,1,3,true,1,2025-11-07 10:12:45,1
ANS005,ATT003,0,1,true,1,2025-11-07 11:03:00,1
```

**Columns:**
- `answer_id` (PK): Unique answer identifier
- `attempt_id` (FK): → student_sessions.attempt_id
- `question_index`: 0-based question number
- `selected_option`: 1=ক, 2=খ, 3=গ, 4=ঘ, NULL=unanswered
- `is_correct`: true/false (calculated at save time)
- `marks_awarded`: Marks for this answer
- `answered_at`: When this answer was given
- `version`: Schema version

**Indexes:** answer_id (primary), attempt_id (foreign)

**Benefits:**
- ✅ Easy to query: "Show all students who answered Q5 correctly"
- ✅ Easy to analyze: "Which question was hardest?"
- ✅ Supports partial submissions
- ✅ Can track answer change history

---

### **7. `transactions/submissions.csv`** (Submission Summary)

```csv
submission_id,attempt_id,total_marks,marks_obtained,percentage,result,submitted_at,graded_at,graded_by,version
SUB001,ATT001,10,8,80.0,pass,2025-11-07 10:23:45,2025-11-07 10:23:46,auto,1
SUB002,ATT002,10,10,100.0,pass,2025-11-07 10:29:30,2025-11-07 10:29:31,auto,1
SUB003,ATT004,10,3,30.0,fail,2025-11-07 10:35:00,2025-11-07 10:35:01,auto,1
```

**Columns:**
- `submission_id` (PK): Unique submission ID
- `attempt_id` (FK): → student_sessions.attempt_id
- `total_marks`: Maximum possible marks
- `marks_obtained`: Marks scored
- `percentage`: Percentage score
- `result`: `pass`, `fail`, `pending`
- `submitted_at`: Submission timestamp
- `graded_at`: When grading completed
- `graded_by`: `auto` or teacher ID
- `version`: Schema version

---

### **8. `audit/audit_log.csv`** (Complete Audit Trail)

```csv
log_id,timestamp,entity_type,entity_id,action,user_id,old_value,new_value,ip_address,version
LOG001,2025-11-07 10:00:00,session,session_8ebac4ca,create,admin,NULL,"{...}",192.168.1.100,1
LOG002,2025-11-07 10:23:45,submission,SUB001,create,STU001,NULL,"{...}",192.168.1.1,1
LOG003,2025-11-07 11:00:00,answer_key,ak_001,update,admin,"2","3",192.168.1.100,1
LOG004,2025-11-07 12:00:00,session,session_old,delete,admin,"{...}",NULL,192.168.1.100,1
```

**Columns:**
- `log_id` (PK): Unique log entry
- `timestamp`: When action occurred
- `entity_type`: `session`, `answer_key`, `student`, `submission`
- `entity_id`: ID of affected entity
- `action`: `create`, `update`, `delete`, `view`
- `user_id`: Who performed action
- `old_value`: Previous value (JSON string)
- `new_value`: New value (JSON string)
- `ip_address`: Source IP
- `version`: Schema version

---

## 🔧 Benefits of New Structure

### **Storage Efficiency**

| Aspect | Old Structure | New Structure | Improvement |
|--------|---------------|---------------|-------------|
| **Files** | 1000 sessions = ~2000 files | 8 core files | 99.6% reduction |
| **Redundancy** | Session_ID in every row | Normalized | 40-60% smaller |
| **Queries** | Scan multiple files | Single file scan | 10-100x faster |
| **Backup** | 2000 files to backup | 8 files | Much easier |

### **Data Integrity**

- ✅ **Foreign key relationships** documented
- ✅ **Validation** at write time
- ✅ **Atomic writes** with file locking
- ✅ **Audit trail** for all changes
- ✅ **Backup before updates**
- ✅ **Schema versioning** for migrations

### **Query Capabilities**

```python
# Old: Need to open 100 files
for session_file in glob("answers_*.csv"):
    # Read each file...

# New: Single query
df = pd.read_csv("transactions/answers.csv")
top_students = df[df['is_correct'] == 'true'].groupby('student_id').size()
```

---

## 📊 Migration Path

### **Step 1: Backup Everything**
```bash
cp -r web/answers web/answers.backup.$(date +%Y%m%d)
cp -r web/answer_keys web/answer_keys.backup.$(date +%Y%m%d)
cp -r web/sessions web/sessions.backup.$(date +%Y%m%d)
```

### **Step 2: Create New Structure**
```bash
mkdir -p web/data/{core,transactions,audit,backups,migrations}
echo "2.0" > web/data/schema_version.txt
```

### **Step 3: Run Migration Script** (to be created)
```bash
python3 web/utils/migrate_to_v2.py --source web/ --dest web/data/
```

### **Step 4: Validate Data**
```bash
python3 web/utils/validate_csv.py --data-dir web/data/
```

### **Step 5: Update Application Code**
- Replace direct CSV access with CSV utility classes
- Update all read/write operations
- Test thoroughly

### **Step 6: Monitor & Rollback Plan**
- Keep old structure for 30 days
- Monitor for issues
- Rollback script ready if needed

---

## 🎯 Implementation Priority

### **Phase 1: Critical (Week 1)**
1. ✅ Create CSV utility classes with locking
2. ✅ Implement backup mechanism
3. ✅ Build migration script
4. ✅ Create validation tools

### **Phase 2: Core (Week 2)**
1. ✅ Migrate answer_keys (easiest)
2. ✅ Migrate sessions
3. ✅ Migrate student_sessions
4. ✅ Test thoroughly

### **Phase 3: Advanced (Week 3)**
1. ✅ Migrate answers to normalized structure
2. ✅ Add audit logging
3. ✅ Create reporting tools
4. ✅ Performance optimization

---

## 📝 Next Steps

1. Review this structure
2. Approve the design
3. I'll create the utility classes
4. I'll create migration scripts
5. Test on sample data
6. Deploy to production

**Would you like me to proceed with creating the implementation files?**
