# File Locking - No Installation Required

## ❌ Common Error

```bash
ERROR: Could not find a version that satisfies the requirement fcntl
ERROR: No matching distribution found for fcntl
```

## ✅ Solution

**DON'T install fcntl!** It's a built-in Python module.

```bash
# ❌ WRONG - Don't do this
pip install fcntl

# ✅ CORRECT - It's already available
python3 -c "import fcntl; print('Works!')"
```

---

## 🔍 Technical Details

### Platform Support

| Platform | Module | Status |
|----------|--------|--------|
| Linux | `fcntl` | ✅ Built-in |
| macOS | `fcntl` | ✅ Built-in |
| Windows | `msvcrt` | ✅ Built-in |

### Our Implementation

The `csv_manager.py` automatically detects your platform:

```python
# Linux/macOS
import fcntl
fcntl.flock(file, fcntl.LOCK_EX)

# Windows
import msvcrt
msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
```

**No configuration needed!** It just works.

---

## 📦 Required Packages

Only these need to be installed:

```bash
pip install -r requirements.txt
```

**Contents:**
- Flask (web framework)
- gunicorn (production server)

**That's it!** File locking uses built-in modules.

---

## 🧪 Test File Locking

```bash
# Test on your system
python3 -c "
from web.utils.csv_manager import LOCK_AVAILABLE
print(f'File locking available: {LOCK_AVAILABLE}')
"
```

**Expected output:**
```
File locking available: True
```

---

## 🔒 How It Works

### Cross-Platform Locking

```python
# Automatically uses the right method for your OS
with csv_manager._lock_file(file_path):
    # Write to file - protected from race conditions
    writer.writerow([data])
```

**Benefits:**
- ✅ Prevents data corruption
- ✅ No race conditions
- ✅ Works on all platforms
- ✅ Zero configuration

---

## 📚 More Information

- **CSV Management:** See `web/utils/csv_manager.py`
- **Race Conditions:** See `CLEAN_STRUCTURE_AND_RACE_CONDITIONS.md`
- **Migration Guide:** See `CSV_QUICK_START.md`

---

## ❓ FAQ

**Q: Do I need to install fcntl?**
A: No! It's built-in on Unix/Linux/macOS.

**Q: What about Windows?**
A: Uses `msvcrt` (also built-in).

**Q: What if locking isn't available?**
A: Code still works, but without race condition protection.

**Q: How do I enable locking?**
A: It's automatic! Just use the CSV v2.0 system.

---

**Bottom line:** Don't install fcntl. It's already there! 🎉
