# MCQ Application - Complete Project Structure

## 📁 Full Directory Tree

```
mcq/
├── 📄 Configuration Files
│   ├── .dockerignore                    # Docker ignore patterns
│   ├── Dockerfile                       # Docker container setup
│   ├── docker-compose.yml               # Docker Compose config
│   ├── fly.toml                         # Fly.io deployment config
│   ├── railway.json                     # Railway deployment config
│   ├── render.yaml                      # Render deployment config
│   ├── requirements.txt                 # Python dependencies
│   ├── Makefile                         # Build automation
│   ├── run.sh                           # Quick start script
│   └── start.sh                         # App start script
│
├── 📚 Documentation
│   ├── README.md                        # Main project documentation
│   ├── QUICKSTART.md                    # Quick start guide
│   ├── BEGINNER_GUIDE.md                # Beginner's guide
│   ├── DEPLOYMENT.md                    # Deployment instructions
│   ├── SETUP_SUMMARY.md                 # Setup summary
│   ├── DOCKER_SETUP.md                  # Docker setup guide
│   ├── DOCKER_PERMISSIONS_EXPLAINED.md  # Docker permissions guide
│   ├── PAPER_SIZE_OPTIONS.md            # Paper size configuration
│   ├── CSV_STRUCTURE_UPGRADE.md         # CSV v2.0 technical spec
│   ├── CSV_QUICK_START.md               # CSV v2.0 quick start
│   └── CSV_IMPROVEMENTS_SUMMARY.md      # CSV improvements summary
│
├── 📝 LaTeX Templates & Inputs
│   ├── templates/
│   │   └── snippet_template.tex         # LaTeX template for questions
│   │
│   └── inputs/
│       └── snippets/
│           ├── example1.tex             # Example question 1
│           ├── example2.tex             # Example question 2
│           ├── mcq_latex_snipet.tex     # MCQ template
│           └── sample_from_user.tex     # User sample
│
├── 🔧 Builder (Question Sheet Generator)
│   └── builder/
│       └── build_sheet.py               # Builds MCQ sheets from snippets
│
├── 🌐 Web Application
│   └── web/
│       │
│       ├── app.py                       # Main Flask application (750+ lines)
│       ├── __init__.py                  # Package initialization
│       │
│       ├── 🎨 Frontend
│       │   ├── templates/
│       │   │   ├── input.html           # Question input page
│       │   │   ├── output.html          # Exam display page
│       │   │   ├── marks_list.html      # Marks overview page
│       │   │   ├── marks_detail.html    # Detailed marks page
│       │   │   └── manage_sessions.html # Session management page
│       │   │
│       │   └── static/
│       │       └── styles.css           # Global styles
│       │
│       ├── 📊 Data Storage (Current v1.0 Structure)
│       │   ├── generated/               # Generated question PDFs
│       │   │   └── session_*/
│       │   │       └── pdfs/
│       │   │           ├── snippet_1.pdf
│       │   │           ├── snippet_2.pdf
│       │   │           └── ...
│       │   │
│       │   ├── answers/                 # Student submissions
│       │   │   ├── README.md
│       │   │   ├── answers_session_079bc94e.csv
│       │   │   ├── answers_session_26d60f60.csv
│       │   │   ├── answers_session_4a7edf87.csv
│       │   │   ├── answers_session_8ebac4ca.csv
│       │   │   └── answers_session_*.csv (many files)
│       │   │
│       │   ├── answer_keys/             # Answer keys per session
│       │   │   ├── answer_key_session_079bc94e.csv
│       │   │   ├── answer_key_session_0ad719cf.csv
│       │   │   ├── answer_key_session_135930d3.csv
│       │   │   └── answer_key_session_*.csv (many files)
│       │   │
│       │   └── sessions/                # Exam session tracking
│       │       ├── README_SESSION.md
│       │       └── exam_sessions.csv
│       │
│       ├── 🛠️ Utilities (CSV v2.0 System)
│       │   └── utils/
│       │       ├── __init__.py
│       │       ├── csv_manager.py       # CSV management library (450+ lines)
│       │       ├── migrate_to_v2.py     # Migration script v1→v2 (380+ lines)
│       │       ├── validate_csv.py      # Data validation tool (320+ lines)
│       │       ├── csv_usage_examples.py # Usage examples (400+ lines)
│       │       └── MIGRATIONS_README.md # Migration documentation
│       │
│       └── 📁 New CSV v2.0 Structure (When Migrated)
│           └── data/
│               ├── schema_version.txt   # Version tracking (2.0)
│               │
│               ├── core/                # Master data
│               │   ├── sessions.csv     # All exam sessions
│               │   ├── answer_keys.csv  # All answer keys (normalized)
│               │   ├── students.csv     # Student registry
│               │   └── exams.csv        # Exam definitions
│               │
│               ├── transactions/        # High-volume transactional data
│               │   ├── student_sessions.csv  # Exam attempts
│               │   ├── answers.csv      # Individual answers (normalized)
│               │   └── submissions.csv  # Graded submissions
│               │
│               ├── audit/               # Audit trail
│               │   └── audit_log.csv    # All changes logged
│               │
│               └── backups/             # Automatic backups
│                   ├── daily/           # Daily backups
│                   ├── before_write/    # Pre-write backups
│                   └── before_migration/ # Pre-migration backups
│
└── 📦 Output (Generated Files)
    └── out/
        ├── sheet_2col.pdf               # 2-column MCQ sheet
        ├── sheet_1col.pdf               # 1-column MCQ sheet
        └── snippets/                    # Compiled snippets
            ├── snippet_1.pdf
            ├── snippet_2.pdf
            └── ...
```

---

## 🔑 Key Components Breakdown

### **1. Flask Application** (`web/app.py`)

**Main Routes:**
```python
# Core functionality
/                          # Input page (create questions)
/compile                   # Compile LaTeX to PDFs
/view/<session_id>         # View/take exam
/generated/<path>          # Serve generated PDFs

# Session management
/sessions                  # List all sessions
/manage-sessions           # Manage/delete sessions
/delete-session/<id>       # Delete specific session
/delete-all-sessions       # Delete all sessions

# Student exam flow
/start-session             # Start exam timer
/check-session             # Check session status
/save-answers              # Submit answers

# Marks/results
/marks                     # View all session marks
/marks/<session_id>        # Detailed marks for session

# System
/health                    # Health check endpoint
```

**Key Functions:**
- `compile_and_crop_snippet()` - Compiles LaTeX to PDF
- `calculate_marks()` - Grades student answers
- `get_answer_key()` - Retrieves answer keys
- `ensure_clean_session_dir()` - Manages session directories

---

### **2. CSV Data Structure**

#### **Current Structure (v1.0)** - Active Now
```
web/
├── answers/answers_session_*.csv        # One file per session
│   Format: Student_ID, Session_ID, Timestamp, Marks, Total, Q1, Q2, Q3...
│
├── answer_keys/answer_key_session_*.csv # One file per session
│   Format: Session_ID, Answer_Key
│
└── sessions/exam_sessions.csv           # Global session tracking
    Format: Student_ID, Session_ID, Start_Time, Date
```

#### **New Structure (v2.0)** - Ready to Migrate
```
web/data/
├── core/sessions.csv                    # Normalized sessions
│   Columns: session_id, content_hash, question_count, created_at,
│            expires_at, status, exam_duration_minutes, created_by, version
│
├── core/answer_keys.csv                 # Normalized answer keys
│   Columns: answer_key_id, session_id, question_index, correct_option,
│            marks, created_at, version
│
├── core/students.csv                    # Student registry
│   Columns: student_id, name, email, institution, batch,
│            registration_date, status, version
│
├── transactions/student_sessions.csv    # Exam attempts
│   Columns: attempt_id, student_id, session_id, exam_id, start_time,
│            submit_time, time_taken_seconds, status, ip_address,
│            user_agent, version
│
├── transactions/answers.csv             # Individual answers
│   Columns: answer_id, attempt_id, question_index, selected_option,
│            is_correct, marks_awarded, answered_at, version
│
└── transactions/submissions.csv         # Submission summaries
    Columns: submission_id, attempt_id, total_marks, marks_obtained,
             percentage, result, submitted_at, graded_at, graded_by, version
```

---

### **3. Frontend Templates**

| Template | Purpose | Features |
|----------|---------|----------|
| `input.html` | Question creation | LaTeX input, answer key entry |
| `output.html` | Exam display | PDF viewer, timer, answer submission |
| `marks_list.html` | Marks overview | Session statistics, navigation |
| `marks_detail.html` | Detailed results | Student rankings, analytics, export |
| `manage_sessions.html` | Admin panel | Delete sessions, view statistics |

---

### **4. Utility Scripts**

| Script | Purpose | Lines | Status |
|--------|---------|-------|--------|
| `csv_manager.py` | CSV CRUD with locking | 450+ | ✅ Complete |
| `migrate_to_v2.py` | v1→v2 migration | 380+ | ✅ Complete |
| `validate_csv.py` | Data validation | 320+ | ✅ Complete |
| `csv_usage_examples.py` | Usage examples | 400+ | ✅ Complete |

---

### **5. Configuration Files**

| File | Purpose |
|------|---------|
| `Dockerfile` | Container definition |
| `docker-compose.yml` | Multi-container setup |
| `requirements.txt` | Python dependencies (Flask) |
| `railway.json` | Railway deployment |
| `render.yaml` | Render deployment |
| `fly.toml` | Fly.io deployment |
| `Makefile` | Build commands |

---

## 📊 Data Flow

### **Question Creation Flow:**
```
1. User enters LaTeX in input.html
2. POST /compile
3. compile_and_crop_snippet() compiles each question
4. PDFs stored in generated/session_xxx/pdfs/
5. Answer key saved to answer_keys/answer_key_session_xxx.csv
6. Redirect to /view/<session_id>
```

### **Student Exam Flow:**
```
1. Student visits /view/<session_id>
2. Enters Student ID
3. POST /start-session (creates timer entry)
4. Student answers questions
5. POST /save-answers
   ├── Validates answers against answer key
   ├── Calculates marks
   ├── Saves to answers/answers_session_xxx.csv
   └── Returns result
```

### **Teacher Marks View Flow:**
```
1. Teacher visits /marks
2. See all sessions with statistics
3. Click session → /marks/<session_id>
4. View detailed results:
   ├── Student rankings
   ├── Answer key comparison
   ├── Pass/fail statistics
   └── Export to CSV
```

---

## 🔢 Statistics

**Total Files:** ~100+
- **Python files:** 6 (app.py + 5 utilities)
- **HTML templates:** 5
- **Documentation:** 11 markdown files
- **Config files:** 8
- **Data files:** Varies (CSV files per session)

**Code Lines:**
- **Flask app:** ~750 lines
- **CSV utilities:** ~1,550 lines
- **Total Python:** ~2,300 lines
- **HTML/CSS:** ~2,000 lines

**Features:**
- ✅ Question creation from LaTeX
- ✅ Multi-format PDF generation
- ✅ Timed exams (25 minutes)
- ✅ Auto-grading
- ✅ Session management
- ✅ Marks viewing with analytics
- ✅ CSV export
- ✅ Docker deployment
- ✅ Cloud deployment ready

---

## 🚀 Deployment Options

**Local:**
```bash
python3 web/app.py
# → http://localhost:5000
```

**Docker:**
```bash
docker compose up
# → http://localhost:5000
```

**Cloud:**
- Railway (railway.json)
- Render (render.yaml)
- Fly.io (fly.toml)

---

## 📝 Data Migration Path

**Current State:**
- Using v1.0 structure (scattered CSV files)
- Works perfectly, no issues

**Migration Ready:**
- v2.0 tools created and tested
- Run when you want better performance
- Optional upgrade

**To Migrate:**
```bash
python3 web/utils/migrate_to_v2.py \
  --source web/ \
  --dest web/data/ \
  --dry-run  # Test first
```

---

## 🎯 Next Steps / Future Enhancements

### **Immediate (Ready to Use):**
- ✅ All features working
- ✅ Marks page functional
- ✅ CSV v2.0 system ready

### **Optional Improvements:**
- 📊 Migrate to CSV v2.0 structure
- 🔐 Add user authentication
- 📧 Email notifications for results
- 📱 Mobile app
- 🎨 Theme customization
- 📈 Advanced analytics dashboard
- 🔄 Question bank/library
- 👥 Multi-teacher support

---

**Current Version:** 1.0 (with v2.0 migration ready)
**Last Updated:** 2025-11-16
**Status:** Production Ready ✅
