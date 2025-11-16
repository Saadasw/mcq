# Migration Scripts Location

## 📁 Directory Structure

### Migration Scripts (Utilities)
Migration scripts are stored in `web/utils/`:

```
web/utils/
├── migrate_to_v2.py      # Migration script: v1.0 → v2.0
├── migrate_to_v3.py      # (Future) Migration script: v2.0 → v3.0
└── ...
```

**Why here?**
- Migration scripts are **utilities** that transform data
- They don't need to be in the data directory
- Easier to version control and maintain alongside other utilities

### Migration Backups (Data)
Migration backups are stored in `web/data/backups/before_migration/`:

```
web/data/backups/before_migration/
├── backup_20251116_120000/    # Backup before v1→v2 migration
├── backup_20251201_150000/    # Backup before v2→v3 migration
└── ...
```

**Why here?**
- Backups are **data**, not code
- Automatically created by migration scripts
- Safe to delete after successful migration

---

## 🔄 Available Migration Scripts

### ✅ v1.0 → v2.0 (`migrate_to_v2.py`)

**Location:** `web/utils/migrate_to_v2.py`

**Purpose:** Migrate from old fragmented CSV structure to new normalized structure

**Usage:**
```bash
# Dry run (test without changes)
python3 web/utils/migrate_to_v2.py --source web/ --dest web/data/ --dry-run

# Actual migration
python3 web/utils/migrate_to_v2.py --source web/ --dest web/data/
```

**What it does:**
- Converts `answers_*.csv` files → `transactions/answers.csv`
- Converts `answer_key_*.csv` files → `core/answer_keys.csv`
- Converts `exam_sessions.csv` → `transactions/student_sessions.csv`
- Creates `core/sessions.csv` from generated/ directory
- Normalizes answer keys (string → individual rows)
- Creates automatic backup in `backups/before_migration/`
- Generates rollback script

---

### ⏳ v2.0 → v3.0 (Future)

**Location:** `web/utils/migrate_to_v3.py` (not created yet)

**Purpose:** Future schema upgrades

**When created, it will:**
- Follow the same pattern as `migrate_to_v2.py`
- Include dry-run mode
- Create automatic backups
- Generate rollback scripts
- Validate migrated data

---

## 📝 Creating New Migration Scripts

When you need to create a new migration (e.g., v3.0):

### Step 1: Copy Template
```bash
cp web/utils/migrate_to_v2.py web/utils/migrate_to_v3.py
```

### Step 2: Update Script
- Change version numbers
- Update schema changes
- Add new data transformations
- Update validation rules

### Step 3: Test
```bash
# Always test with dry-run first
python3 web/utils/migrate_to_v3.py --source web/data/ --dest web/data_v3/ --dry-run
```

### Step 4: Document
- Update this README
- Update CSV_STRUCTURE_UPGRADE.md
- Add migration notes

---

## 🗂️ Complete Directory Layout

```
web/
├── utils/                          # Utility scripts (version controlled)
│   ├── csv_manager.py             # CSV management library
│   ├── migrate_to_v2.py           # ✅ Migration: v1 → v2
│   ├── migrate_to_v3.py           # ⏳ Future: v2 → v3
│   ├── validate_csv.py            # Data validation tool
│   └── csv_usage_examples.py      # Usage examples
│
└── data/                           # Data directory (NOT version controlled)
    ├── schema_version.txt         # Current schema version
    ├── core/                      # Master data
    │   ├── sessions.csv
    │   ├── answer_keys.csv
    │   ├── students.csv
    │   └── exams.csv
    ├── transactions/              # Transaction data
    │   ├── student_sessions.csv
    │   ├── answers.csv
    │   └── submissions.csv
    ├── audit/                     # Audit logs
    │   └── audit_log.csv
    └── backups/                   # Automatic backups
        ├── daily/                 # Daily backups
        ├── before_write/          # Pre-write backups
        └── before_migration/      # Pre-migration backups
            ├── backup_20251116_120000/
            └── ...
```

---

## ❓ FAQ

### Q: Why are migration scripts in `web/utils/` instead of `web/data/migrations/`?

**A:** Migration scripts are **executable code**, not data. They should be:
- Version controlled (Git)
- Reviewed like other code
- Tested before use
- Maintained alongside other utilities

The `web/data/` directory contains **data only** and should not be version controlled.

### Q: Where are migration backups stored?

**A:** In `web/data/backups/before_migration/`
- Created automatically before each migration
- Named with timestamp (e.g., `backup_20251116_120000/`)
- Can be used for rollback if needed

### Q: Can I delete old migration backups?

**A:** Yes, after verifying the migration succeeded:
1. Wait 30 days after migration
2. Verify new structure works correctly
3. Delete old backups: `rm -rf web/data/backups/before_migration/backup_*`

### Q: How do I rollback a migration?

**A:** Use the auto-generated rollback script:
```bash
# Created by migration script
./rollback_migration.sh
```

Or manually:
```bash
rm -rf web/data/
mv web/backup_YYYYMMDD_HHMMSS/* web/
```

---

## 📚 Related Documentation

- **CSV Structure:** [CSV_STRUCTURE_UPGRADE.md](../../CSV_STRUCTURE_UPGRADE.md)
- **Quick Start:** [CSV_QUICK_START.md](../../CSV_QUICK_START.md)
- **Usage Examples:** [csv_usage_examples.py](csv_usage_examples.py)

---

**Last Updated:** 2025-11-16
**Current Schema Version:** 2.0
