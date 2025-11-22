import os
import re
import shutil
import subprocess
import tempfile
import time
import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import List
import uuid

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort, jsonify, session, flash
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.utils import secure_filename

# Google Generative AI for LaTeX extraction from images
try:
    import google.generativeai as genai
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("WARNING: Google Generative AI SDK not available. Image-to-LaTeX feature disabled.")

# Add web directory to Python path for utils import
APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

# Import CSV v2.0 manager
try:
    from utils.csv_manager import CSVManager, CSVValidationError
except ImportError:
    # Fallback: CSV manager not available, will use legacy mode
    CSVManager = None
    CSVValidationError = Exception
    print("WARNING: CSV v2.0 manager not available, using legacy mode")

# Import Normalized CSV Database
try:
    from utils.csv_normalized import NormalizedCSVDB
except ImportError:
    NormalizedCSVDB = None
    print("WARNING: Normalized CSV database not available")

# Import robust LaTeX compiler
try:
    from utils.robust_latex_compiler import compile_latex_robust, CompilationResult
    ROBUST_COMPILER_AVAILABLE = True
except ImportError:
    ROBUST_COMPILER_AVAILABLE = False
    print("WARNING: Robust LaTeX compiler not available, using basic compiler")


REPO_ROOT = APP_ROOT.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
SNIPPET_TEMPLATE = (TEMPLATES_DIR / "snippet_template.tex").read_text(encoding="utf-8")
GENERATED_DIR = APP_ROOT / "generated"

# V2.0 data directory
DATA_DIR = APP_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Initialize CSV Manager (v2.0 system with file locking)
if CSVManager:
    csv_manager = CSVManager(DATA_DIR, auto_backup=True)
else:
    csv_manager = None

# Legacy v1.0 directories (kept for backward compatibility)
ANSWERS_DIR = APP_ROOT / "answers"
SESSIONS_DIR = APP_ROOT / "sessions"
ANSWER_KEYS_DIR = APP_ROOT / "answer_keys"
SESSION_METADATA_DIR = APP_ROOT / "session_metadata"
ALLOWED_STUDENTS_DIR = APP_ROOT / "allowed_students"
ANSWERS_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
ANSWER_KEYS_DIR.mkdir(exist_ok=True)
SESSION_METADATA_DIR.mkdir(exist_ok=True)
ALLOWED_STUDENTS_DIR.mkdir(exist_ok=True)

# Activity logging directory (for tracking student logins and attempts)
ACTIVITY_LOGS_DIR = APP_ROOT / "activity_logs"
ACTIVITY_LOGS_DIR.mkdir(exist_ok=True)

# Login sessions directory (for server-side session management)
LOGIN_SESSIONS_DIR = APP_ROOT / "login_sessions"

# Settings directory (for global application settings)
SETTINGS_DIR = APP_ROOT / "settings"
SETTINGS_DIR.mkdir(exist_ok=True)
LOGIN_SESSIONS_DIR.mkdir(exist_ok=True)
ACTIVE_SESSIONS_FILE = LOGIN_SESSIONS_DIR / "active_sessions.csv"


# Login session management functions
def create_login_session(student_id: str, is_admin: bool = False) -> str:
    """
    Create a new login session in CSV and return session ID
    """
    import secrets

    # Generate unique session ID
    session_id = secrets.token_urlsafe(32)

    # Get device information
    user_agent = request.headers.get('User-Agent', 'Unknown')
    ip_address = request.remote_addr or 'Unknown'
    device_info = parse_device_info(user_agent)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create file with header if it doesn't exist
    file_exists = ACTIVE_SESSIONS_FILE.exists()

    with open(ACTIVE_SESSIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "Session_ID",
                "Student_ID",
                "Is_Admin",
                "Login_Time",
                "Last_Activity",
                "IP_Address",
                "Device_Type",
                "Browser",
                "OS",
                "User_Agent",
                "Status"
            ])

        writer.writerow([
            session_id,
            student_id,
            "Yes" if is_admin else "No",
            timestamp,
            timestamp,
            ip_address,
            device_info['device_type'],
            device_info['browser'],
            device_info['os'],
            user_agent,
            "active"
        ])

    return session_id


def update_session_activity(session_id: str):
    """Update last activity time for a session"""
    if not ACTIVE_SESSIONS_FILE.exists():
        return

    try:
        # Read all sessions
        sessions = []
        with open(ACTIVE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            sessions = list(reader)

        # Update the session
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for sess in sessions:
            if sess['Session_ID'] == session_id:
                sess['Last_Activity'] = timestamp
                break

        # Write back
        if sessions:
            with open(ACTIVE_SESSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=sessions[0].keys())
                writer.writeheader()
                writer.writerows(sessions)
    except Exception as e:
        print(f"Error updating session activity: {e}")


def terminate_login_session(session_id: str):
    """Mark a session as terminated"""
    if not ACTIVE_SESSIONS_FILE.exists():
        return

    try:
        # Read all sessions
        sessions = []
        with open(ACTIVE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            sessions = list(reader)

        # Mark session as terminated
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for sess in sessions:
            if sess['Session_ID'] == session_id:
                sess['Status'] = 'terminated'
                sess['Last_Activity'] = timestamp
                break

        # Write back
        if sessions:
            with open(ACTIVE_SESSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=sessions[0].keys())
                writer.writeheader()
                writer.writerows(sessions)
    except Exception as e:
        print(f"Error terminating session: {e}")


def cleanup_expired_sessions(timeout_hours: int = 24):
    """Remove sessions inactive for more than timeout_hours"""
    if not ACTIVE_SESSIONS_FILE.exists():
        return

    try:
        # Read all sessions
        sessions = []
        with open(ACTIVE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            sessions = list(reader)

        # Filter out expired sessions
        now = datetime.now()
        active_sessions = []

        for sess in sessions:
            try:
                last_activity = datetime.strptime(sess['Last_Activity'], "%Y-%m-%d %H:%M:%S")
                hours_inactive = (now - last_activity).total_seconds() / 3600

                # Keep if active and not expired
                if sess['Status'] == 'active' and hours_inactive < timeout_hours:
                    active_sessions.append(sess)
            except Exception:
                continue

        # Write back only active sessions
        if active_sessions:
            with open(ACTIVE_SESSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=active_sessions[0].keys())
                writer.writeheader()
                writer.writerows(active_sessions)
        elif ACTIVE_SESSIONS_FILE.exists():
            # If no active sessions, create empty file with header
            with open(ACTIVE_SESSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Session_ID", "Student_ID", "Is_Admin", "Login_Time",
                    "Last_Activity", "IP_Address", "Device_Type", "Browser",
                    "OS", "User_Agent", "Status"
                ])
    except Exception as e:
        print(f"Error cleaning up sessions: {e}")


# Global settings management functions
def get_auth_required() -> bool:
    """
    Check if authentication is required for the site
    Returns True if auth is required (default), False if open access
    """
    settings_file = SETTINGS_DIR / "auth_settings.csv"

    # Default to True (auth required) if file doesn't exist
    if not settings_file.exists():
        return True

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Setting') == 'auth_required':
                    return row.get('Value', 'true').lower() == 'true'
    except Exception as e:
        print(f"Error reading auth settings: {e}")

    return True  # Default to auth required


def set_auth_required(required: bool):
    """
    Set whether authentication is required for the site
    """
    settings_file = SETTINGS_DIR / "auth_settings.csv"

    try:
        with open(settings_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Setting', 'Value', 'Updated_At', 'Updated_By'])
            writer.writerow([
                'auth_required',
                'true' if required else 'false',
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                session.get('student_id', 'system')
            ])
        return True
    except Exception as e:
        print(f"Error writing auth settings: {e}")
        return False


def get_all_active_sessions() -> list:
    """Get all active login sessions"""
    if not ACTIVE_SESSIONS_FILE.exists():
        return []

    try:
        sessions = []
        with open(ACTIVE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sessions.append(row)
        return sessions
    except Exception as e:
        print(f"Error getting active sessions: {e}")
        return []


def force_logout_session(session_id: str):
    """Force logout a specific session (admin action)"""
    terminate_login_session(session_id)


def get_student_active_sessions(student_id: str) -> list:
    """Get all active sessions for a specific student"""
    all_sessions = get_all_active_sessions()
    return [s for s in all_sessions if s.get('Student_ID') == student_id and s.get('Status') == 'active']


# Activity logging functions
def log_student_activity(student_id: str, activity_type: str, session_id: str = None, details: str = None):
    """
    Log student activity to CSV for audit trail

    Args:
        student_id: Student ID
        activity_type: Type of activity (login, session_start, session_check, answer_submit, logout)
        session_id: Exam session ID (if applicable)
        details: Additional details
    """
    try:
        # Get device information from request
        user_agent = request.headers.get('User-Agent', 'Unknown')
        ip_address = request.remote_addr or 'Unknown'

        # Parse device info from User-Agent
        device_info = parse_device_info(user_agent)

        # Get or increment attempt number for this student and session
        attempt_number = get_attempt_number(student_id, session_id) if session_id else 0

        # Create log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Daily log file (one file per day)
        log_date = datetime.now().strftime("%Y-%m-%d")
        log_file = ACTIVITY_LOGS_DIR / f"activity_{log_date}.csv"

        # Create file with header if it doesn't exist
        file_exists = log_file.exists()

        with open(log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            if not file_exists:
                # Write header
                writer.writerow([
                    "Timestamp",
                    "Student_ID",
                    "Activity_Type",
                    "Session_ID",
                    "Attempt_Number",
                    "IP_Address",
                    "Device_Type",
                    "Browser",
                    "OS",
                    "User_Agent",
                    "Details"
                ])

            # Write activity log
            writer.writerow([
                timestamp,
                student_id,
                activity_type,
                session_id or "",
                attempt_number,
                ip_address,
                device_info['device_type'],
                device_info['browser'],
                device_info['os'],
                user_agent,
                details or ""
            ])

    except Exception as e:
        # Don't crash the app if logging fails
        print(f"Error logging activity: {e}")


def parse_device_info(user_agent: str) -> dict:
    """Parse User-Agent string to extract device information"""
    ua_lower = user_agent.lower()

    # Detect device type
    if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
        device_type = 'Mobile'
    elif 'tablet' in ua_lower or 'ipad' in ua_lower:
        device_type = 'Tablet'
    else:
        device_type = 'Desktop'

    # Detect browser
    if 'edg' in ua_lower:
        browser = 'Edge'
    elif 'chrome' in ua_lower:
        browser = 'Chrome'
    elif 'firefox' in ua_lower:
        browser = 'Firefox'
    elif 'safari' in ua_lower and 'chrome' not in ua_lower:
        browser = 'Safari'
    elif 'opera' in ua_lower or 'opr' in ua_lower:
        browser = 'Opera'
    else:
        browser = 'Other'

    # Detect OS
    if 'windows' in ua_lower:
        os_name = 'Windows'
    elif 'mac' in ua_lower:
        os_name = 'macOS'
    elif 'linux' in ua_lower:
        os_name = 'Linux'
    elif 'android' in ua_lower:
        os_name = 'Android'
    elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
        os_name = 'iOS'
    else:
        os_name = 'Other'

    return {
        'device_type': device_type,
        'browser': browser,
        'os': os_name
    }


def get_attempt_number(student_id: str, session_id: str) -> int:
    """Get the attempt number for a student's session"""
    try:
        # Count how many times this student has started this session
        count = 0

        # Check all activity logs
        for log_file in sorted(ACTIVITY_LOGS_DIR.glob("activity_*.csv")):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if (row.get('Student_ID') == student_id and
                            row.get('Session_ID') == session_id and
                            row.get('Activity_Type') == 'session_start'):
                            count += 1
            except Exception:
                continue

        # Return next attempt number
        return count + 1

    except Exception:
        return 1


def get_all_activity_logs(limit: int = 1000) -> list:
    """Get all activity logs, most recent first"""
    logs = []

    try:
        # Read all log files in reverse chronological order
        for log_file in sorted(ACTIVITY_LOGS_DIR.glob("activity_*.csv"), reverse=True):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        logs.append(row)
                        if len(logs) >= limit:
                            return logs
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
                continue
    except Exception as e:
        print(f"Error getting activity logs: {e}")

    return logs


def get_student_activity_logs(student_id: str) -> list:
    """Get activity logs for a specific student"""
    logs = []

    try:
        for log_file in sorted(ACTIVITY_LOGS_DIR.glob("activity_*.csv"), reverse=True):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('Student_ID') == student_id:
                            logs.append(row)
            except Exception:
                continue
    except Exception as e:
        print(f"Error getting student activity logs: {e}")

    return logs


def run(cmd: List[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n\n{proc.stdout}")
    return proc.stdout


def extract_body(content: str) -> str:
    m = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", content, flags=re.S)
    if m:
        return m.group(1).strip()
    return content.strip()


def render_snippet_tex(content: str) -> str:
    body = extract_body(content)
    return SNIPPET_TEMPLATE.replace("% CONTENT_HERE", body)


def compile_and_crop_snippet(content: str, out_dir: Path, idx: int) -> Path:
    """
    Compile LaTeX snippet to PDF using robust compiler
    Falls back to basic compiler if robust version unavailable
    """
    latex_content = render_snippet_tex(content)
    filename = f"snippet_{idx}"

    # Try robust compiler first
    if ROBUST_COMPILER_AVAILABLE:
        result = compile_latex_robust(
            latex_content,
            out_dir,
            filename=filename,
            validate=True  # Enable pre-compilation validation
        )

        if result.success:
            # Log any warnings
            if result.warnings:
                print(f"⚠️  Snippet {idx} compiled with warnings:")
                for warning in result.warnings[:3]:  # Show first 3 warnings
                    print(f"   - {warning[:100]}")

            return result.pdf_path

        else:
            # Compilation failed with robust compiler
            error_msg = result.error_message or "Unknown error"
            print(f"❌ Robust compilation failed for snippet {idx}: {error_msg}")

            # Try basic compiler as fallback
            print(f"🔄 Trying basic compiler for snippet {idx}...")

    # Fallback to basic compiler (original implementation)
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        tex_path = tdir / f"{filename}.tex"
        tex_path.write_text(latex_content, encoding="utf-8")

        try:
            for _ in range(2):
                run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name], cwd=tdir)
        except RuntimeError as e:
            # Even basic compiler failed
            raise RuntimeError(f"LaTeX compilation failed for snippet {idx}: {str(e)}")

        pdf_path = tdir / f"{filename}.pdf"
        if not pdf_path.exists():
            raise RuntimeError(f"PDF not produced for snippet {idx}")

        # Copy PDF to output directory
        final_pdf = out_dir / f"{filename}.pdf"
        import shutil as _sh
        _sh.copy2(pdf_path, final_pdf)
        return final_pdf


def ensure_clean_session_dir(session_id: str) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    sess_dir = GENERATED_DIR / session_id
    if sess_dir.exists():
        shutil.rmtree(sess_dir, ignore_errors=True)
    (sess_dir / "pdfs").mkdir(parents=True, exist_ok=True)
    return sess_dir


app = Flask(__name__, template_folder=str(APP_ROOT / "templates"), static_folder=str(APP_ROOT / "static"))

# Set secret key for session management
# In production, use environment variable
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Admin student ID
ADMIN_STUDENT_ID = "ASw527174888*"

# Configure Gemini API for LaTeX extraction
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ Gemini API configured successfully")
    except Exception as e:
        print(f"⚠️ Failed to configure Gemini API: {e}")
        GEMINI_AVAILABLE = False
elif GEMINI_AVAILABLE and not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not set. Image-to-LaTeX feature will be disabled.")
    GEMINI_AVAILABLE = False

# Get port from environment variable, default to 5000
PORT = int(os.environ.get("PORT", 5000))
# Get host from environment variable, default to 0.0.0.0
HOST = os.environ.get("HOST", "0.0.0.0")

# ==================== SECURITY CONFIGURATION ====================

# Rate Limiting - Protect against abuse and DDoS
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://",  # Use memory storage (Redis recommended for production)
    strategy="fixed-window"
)

# Security Headers - Protect against common web vulnerabilities
# Disable in development if needed
is_production = os.environ.get("FLASK_ENV") != "development"
if is_production:
    Talisman(
        app,
        force_https=False,  # Render handles HTTPS
        content_security_policy={
            'default-src': "'self'",
            'script-src': ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", "data:", "https:"],
            'font-src': ["'self'", "data:"],
            'frame-src': ["'self'"],
        },
        content_security_policy_nonce_in=['script-src']
    )

# Request size limit (10MB max to prevent memory attacks)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB


# Middleware to update session activity on each request
@app.before_request
def before_request():
    """Update session activity timestamp before each request"""
    if session.get('login_session_id') and session.get('student_id'):
        # Update session activity in CSV
        update_session_activity(session.get('login_session_id'))


# Authentication decorators
def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('student_id'):
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        if session.get('student_id') != ADMIN_STUDENT_ID:
            flash('Admin access required', 'error')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@limiter.limit("100 per minute")
def index():
    """Landing page - Shows all available exam sessions (public access)"""
    # Check if user is logged in as admin
    if session.get('student_id') == ADMIN_STUDENT_ID:
        return redirect(url_for('input_page'))

    # For everyone else (including guests), show public sessions list
    return redirect(url_for('sessions_list'))


@app.route("/login", methods=['GET', 'POST'])
@limiter.limit("10 per minute")  # Prevent brute force attacks
def login():
    """Admin-only login page - Public users don't need to log in"""
    if request.method == 'POST':
        admin_id = request.form.get('student_id', '').strip()

        if not admin_id:
            flash('Please enter admin ID', 'error')
            return render_template("login.html", admin_only=True)

        # Only allow admin login
        if admin_id != ADMIN_STUDENT_ID:
            flash('Invalid admin credentials', 'error')
            return render_template("login.html", admin_only=True)

        # Check for concurrent sessions
        existing_sessions = get_student_active_sessions(admin_id)
        if existing_sessions:
            # Terminate old sessions
            for old_session in existing_sessions:
                terminate_login_session(old_session['Session_ID'])

        # Store admin ID in Flask session
        session['student_id'] = admin_id
        session['is_admin'] = True

        # Create server-side session in CSV
        login_session_id = create_login_session(admin_id, True)
        session['login_session_id'] = login_session_id

        # Cleanup old expired sessions
        cleanup_expired_sessions(timeout_hours=24)

        # Log login activity
        log_student_activity(
            student_id=admin_id,
            activity_type='login',
            details=f"Admin login successful - Session: {login_session_id[:16]}"
        )

        flash(f'Welcome, Admin!', 'success')
        return redirect(url_for('input_page'))

    # GET request - show admin login form
    # If already logged in as admin, redirect
    if session.get('student_id') == ADMIN_STUDENT_ID:
        return redirect(url_for('input_page'))

    return render_template("login.html", admin_only=True)


@app.route("/logout")
def logout():
    """Logout admin"""
    # Log logout activity and terminate server-side session
    if session.get('student_id'):
        log_student_activity(
            student_id=session.get('student_id'),
            activity_type='logout',
            details='Admin logged out'
        )

        # Terminate server-side session
        if session.get('login_session_id'):
            terminate_login_session(session.get('login_session_id'))

    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.route("/admin")
@admin_required
def input_page():
    """Admin input page for creating exams"""
    return render_template("input.html")


@app.route("/extract-latex", methods=['POST'])
@admin_required
@limiter.limit("5 per minute")  # Lower rate limit for full paper processing
def extract_latex():
    """Extract LaTeX code from uploaded full question paper using Gemini Vision API with two-step pipeline"""
    if not GEMINI_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Gemini API not configured. Please set GEMINI_API_KEY environment variable.'
        }), 503

    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file provided'}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400

    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    filename = secure_filename(image_file.filename)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext not in allowed_extensions:
        return jsonify({'success': False, 'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400

    temp_path = None
    temp_dir = None

    try:
        # Save uploaded image temporarily
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        image_file.save(temp_path)

        print(f"📷 Analyzing full question paper: {filename}")

        # STEP 1: Vision Analysis - Understand the structure
        uploaded_file = genai.upload_file(temp_path)
        model = genai.GenerativeModel('gemini-1.5-flash')

        step1_prompt = """
Analyze this MCQ test paper image carefully.

TASK: Provide a structured analysis of the question paper.

OUTPUT FORMAT (JSON-like structure):
1. Total number of questions
2. Question numbering format (1., Q1, etc.)
3. For each question:
   - Question number
   - Question text (Bengali/English, exact transcription)
   - Mathematical formulas (identify locations)
   - Diagrams/images (describe if present)
   - MCQ options (ক, খ, গ, ঘ or A, B, C, D) - list them
4. Layout information (single/multi-column, formatting)

DO NOT generate LaTeX yet. Just analyze and describe the content structure.
Be thorough and accurate with text extraction.
"""

        print("🔍 Step 1: Analyzing question paper structure...")
        response_step1 = model.generate_content([step1_prompt, uploaded_file])
        content_description = response_step1.text.strip()
        print(f"✅ Structure analysis complete ({len(content_description)} chars)")

        # STEP 2: LaTeX Generation - Convert to LaTeX snippets
        step2_prompt = f"""
Based on this analysis of a question paper:
{content_description}

TASK: Generate LaTeX code for EACH question separately.

REQUIREMENTS:
1. Output format: Separate each question with delimiter "### QUESTION N ###"
2. For each question:
   - Extract ONLY the question stem (not the options)
   - Convert text exactly (preserve Bengali/English)
   - Convert math formulas to LaTeX: $inline$ or $$display$$
   - Use \\textbf{{}} for bold, \\textit{{}} for italics
   - For diagrams: use TikZ if simple, otherwise textual description
   - DO NOT include \\documentclass, \\begin{{document}}, or preamble
   - DO NOT include MCQ options (ক, খ, গ, ঘ)
   - Return ONLY the question body as clean LaTeX snippet

EXAMPLE OUTPUT FORMAT:
### QUESTION 1 ###
যদি $x^2 + 5x + 6 = 0$ হয়, তাহলে $x$ এর মান কত?

### QUESTION 2 ###
একটি সমবাহু ত্রিভুজের একটি বাহুর দৈর্ঘ্য $5$ সেমি হলে, এর ক্ষেত্রফল কত?

### QUESTION 3 ###
The value of $\\frac{{a^2 - b^2}}{{a + b}}$ when $a = 5$ and $b = 3$ is:

Generate LaTeX for ALL questions found in the analysis.
"""

        print("📝 Step 2: Generating LaTeX code for all questions...")
        response_step2 = model.generate_content(step2_prompt)
        full_latex = response_step2.text.strip()
        print(f"✅ LaTeX generation complete ({len(full_latex)} chars)")

        # STEP 3: Parse LaTeX to extract individual questions
        questions = parse_latex_questions(full_latex)

        if not questions:
            # Retry with error correction if parsing failed
            print("⚠️ Parsing failed, retrying with clarification...")
            retry_prompt = f"""
The previous output was not properly formatted. Please regenerate with correct format.

CRITICAL: Use exactly this delimiter between questions: ### QUESTION N ###
where N is the question number (1, 2, 3, etc.)

Previous output:
{full_latex[:500]}...

Regenerate with proper delimiters.
"""
            response_retry = model.generate_content(retry_prompt)
            full_latex = response_retry.text.strip()
            questions = parse_latex_questions(full_latex)

        if not questions:
            return jsonify({
                'success': False,
                'error': 'Could not extract individual questions. Please try a clearer image or upload questions separately.',
                'raw_output': full_latex[:500]  # For debugging
            }), 400

        # Clean up temporary files
        try:
            os.remove(temp_path)
            os.rmdir(temp_dir)
        except:
            pass

        print(f"✅ Successfully extracted {len(questions)} questions")

        return jsonify({
            'success': True,
            'question_count': len(questions),
            'questions': questions  # Array of LaTeX snippets
        })

    except Exception as e:
        print(f"❌ Error extracting LaTeX: {e}")
        import traceback
        traceback.print_exc()

        # Clean up on error
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            if temp_dir and os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass

        return jsonify({
            'success': False,
            'error': f'Failed to extract LaTeX: {str(e)}'
        }), 500


def parse_latex_questions(latex_text: str) -> list:
    """Parse LaTeX output to extract individual question snippets"""
    import re

    # Clean markdown code blocks if present
    latex_text = latex_text.replace("```latex", "").replace("```", "").strip()

    # Split by question delimiter
    # Try multiple delimiter patterns
    patterns = [
        r'###\s*QUESTION\s+(\d+)\s*###',  # ### QUESTION N ###
        r'##\s*Question\s+(\d+)\s*##',    # ## Question N ##
        r'\*\*Question\s+(\d+)\*\*',       # **Question N**
        r'Question\s+(\d+):',               # Question N:
        r'^\d+\.',                          # 1., 2., 3. at line start
    ]

    questions = []

    for pattern in patterns:
        splits = re.split(pattern, latex_text, flags=re.MULTILINE | re.IGNORECASE)

        if len(splits) > 2:  # Found delimiters
            # Extract questions (skip first element if it's header text)
            for i in range(1, len(splits), 2):  # Every odd index is a question number
                if i + 1 < len(splits):
                    question_text = splits[i + 1].strip()
                    # Clean up the question
                    question_text = clean_latex_snippet(question_text)
                    if question_text and len(question_text) > 5:  # Minimum length check
                        questions.append(question_text)

            if questions:
                break  # Successfully parsed

    # Fallback: If no delimiter found, try to split by common patterns
    if not questions:
        # Try splitting by numbered lines (1. 2. 3. etc.)
        lines = latex_text.split('\n')
        current_question = []

        for line in lines:
            if re.match(r'^\d+\.', line.strip()):  # New question starts
                if current_question:
                    q_text = '\n'.join(current_question).strip()
                    q_text = clean_latex_snippet(q_text)
                    if q_text:
                        questions.append(q_text)
                    current_question = []
                # Remove the number prefix
                line = re.sub(r'^\d+\.\s*', '', line.strip())
                if line:
                    current_question.append(line)
            elif line.strip():
                current_question.append(line)

        # Add last question
        if current_question:
            q_text = '\n'.join(current_question).strip()
            q_text = clean_latex_snippet(q_text)
            if q_text:
                questions.append(q_text)

    return questions


def clean_latex_snippet(text: str) -> str:
    """Clean up a LaTeX snippet"""
    # Remove document commands if present
    text = re.sub(r'\\documentclass.*?\n', '', text)
    text = re.sub(r'\\usepackage.*?\n', '', text)
    text = re.sub(r'\\begin\{document\}', '', text)
    text = re.sub(r'\\end\{document\}', '', text)

    # Remove MCQ options (ক, খ, গ, ঘ) or (A, B, C, D) patterns
    # Pattern: option letter followed by dot or paren and text
    text = re.sub(r'\n\s*[ক-ঘABCD][.)\]]\s*.*?(?=\n|$)', '', text, flags=re.MULTILINE)

    # Remove extra whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple blank lines to double
    text = text.strip()

    return text


@app.route("/sessions-list")
@app.route("/student/dashboard")  # Keep old route for compatibility
@limiter.limit("100 per minute")
def sessions_list():
    """Public sessions list - shows all available exams (no login required)"""
    student_id = session.get('student_id', 'guest')  # Default to guest if not logged in

    # Get all exams from normalized CSV
    exams_list = []

    if NormalizedCSVDB:
        # Get all active exams
        exams = NormalizedCSVDB.get_all_exams(status='active')

        for exam in exams:
            exam_id = exam['exam_id']

            # Public access - everyone can see all exams
            # Check if student has taken this exam
            has_taken = False
            student_score = None
            if student_id != 'guest':
                submission = NormalizedCSVDB.get_submission(exam_id, student_id)
                if submission:
                    has_taken = True
                    # Calculate percentage
                    try:
                        score = int(submission['score'])
                        total = int(submission['total_marks'])
                        if total > 0:
                            percentage = (score / total) * 100
                            student_score = f"{percentage:.1f}%"
                        else:
                            student_score = f"{score}/{total}"
                    except:
                        student_score = f"{submission['score']}/{submission['total_marks']}"

            exams_list.append({
                'session_id': exam_id,
                'exam_name': exam.get('exam_name', 'Untitled Exam'),
                'subject': exam.get('subject', 'General'),
                'duration': exam.get('duration_minutes', '25'),
                'created_at': exam.get('created_at', ''),
                'is_allowed': True,  # Everyone allowed in public mode
                'has_taken': has_taken,
                'score': student_score
            })

    return render_template("student_dashboard.html",
                         student_id=student_id,
                         sessions=exams_list,
                         public_mode=True)


@app.route("/student/results")
@limiter.limit("50 per minute")
def student_results():
    """Student results page - detailed exam history and scores - Public access"""
    student_id = session.get('student_id', 'guest')

    results = []

    if NormalizedCSVDB:
        # Get all submissions for this student
        submissions = NormalizedCSVDB.get_student_submissions(student_id)

        for submission in submissions:
            exam_id = submission['exam_id']

            # Get exam metadata
            exam = NormalizedCSVDB.get_exam(exam_id)
            if not exam:
                continue

            # Calculate percentage
            try:
                marks_int = int(submission['score'])
                total_int = int(submission['total_marks'])
                if total_int > 0:
                    percentage = (marks_int / total_int) * 100
                    score = f"{marks_int}/{total_int} ({percentage:.1f}%)"
                else:
                    score = f"{marks_int}/{total_int}"
            except:
                score = f"{submission['score']}/{submission['total_marks']}"

            results.append({
                'session_id': exam_id,
                'exam_name': exam.get('exam_name', 'Untitled Exam'),
                'subject': exam.get('subject', 'General'),
                'score': score,
                'marks': submission['score'],
                'total': submission['total_marks'],
                'submission_time': submission['submitted_at'],
                'passing_percentage': exam.get('passing_percentage', '40')
            })

    return render_template("student_results.html",
                         student_id=student_id,
                         results=results)


@app.post("/compile")
@admin_required
def compile_route():
    # inputs come as texts[]
    texts = request.form.getlist("texts[]")
    # Filter out empties/whitespace-only
    texts = [t for t in (x.strip() for x in texts) if t]
    if not texts:
        return redirect(url_for("input_page"))

    # Get exam metadata
    exam_name = request.form.get("exam_name", "").strip() or "Untitled Exam"
    subject = request.form.get("subject", "").strip() or "General"
    exam_duration = request.form.get("exam_duration", "25").strip()
    passing_marks = request.form.get("passing_marks", "40").strip()

    # Get student whitelist
    allowed_students_str = request.form.get("allowed_students", "").strip()
    allowed_students = []
    if allowed_students_str:
        # Parse comma-separated or newline-separated student IDs
        import re
        allowed_students = [s.strip() for s in re.split(r'[,\n]+', allowed_students_str) if s.strip()]

    # Get correct answers
    correct_answers_str = request.form.get("correct_answers", "").strip()

    # Use a fixed session ID based on content hash to ensure same questions for all users
    content_hash = hashlib.md5("|".join(texts).encode()).hexdigest()[:8]
    session_id = f"session_{content_hash}"

    sess_dir = GENERATED_DIR / session_id
    pdf_out_dir = sess_dir / "pdfs"

    # Only compile if PDFs don't already exist (same questions for all users)
    if not pdf_out_dir.exists() or not list(pdf_out_dir.glob("snippet_*.pdf")):
        ensure_clean_session_dir(session_id)
        pdf_out_dir.mkdir(parents=True, exist_ok=True)

        cropped_paths: List[Path] = []
        for i, txt in enumerate(texts, start=1):
            try:
                cropped = compile_and_crop_snippet(txt, pdf_out_dir, i)
                cropped_paths.append(cropped)
            except Exception as e:
                print("Compile error:", e)
                continue
    else:
        # PDFs already exist, just get the list
        cropped_paths = sorted(pdf_out_dir.glob("snippet_*.pdf"), key=lambda p: int(p.stem.split("_")[1]))

    # Handle image URLs
    image_urls = request.form.getlist("image_urls[]")

    # Save image URLs to CSV file
    image_urls_file = sess_dir / "image_urls.csv"
    sess_dir.mkdir(parents=True, exist_ok=True)

    with open(image_urls_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Question_Index", "Image_URL"])
        for i, url in enumerate(image_urls, start=1):
            # Only save if URL is provided
            url = url.strip() if url else ""
            if url:
                writer.writerow([i, url])

    # Save session metadata - ALWAYS save to legacy format for reliability
    metadata_file = SESSION_METADATA_DIR / f"metadata_{session_id}.csv"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(metadata_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Session_ID", session_id])
        writer.writerow(["Exam_Name", exam_name])
        writer.writerow(["Subject", subject])
        writer.writerow(["Duration_Minutes", exam_duration])
        writer.writerow(["Passing_Percentage", passing_marks])
        writer.writerow(["Question_Count", len(texts)])
        writer.writerow(["Created_At", now])
        writer.writerow(["Allowed_Students", ",".join(allowed_students) if allowed_students else "ALL"])

    # ALSO save to Normalized CSV (new format)
    if NormalizedCSVDB:
        try:
            # Prepare allowed students format (semicolon-separated)
            allowed_students_normalized = ";".join(allowed_students) if allowed_students else "ALL"

            # Create exam
            exam_data = {
                "exam_id": session_id,
                "exam_name": exam_name,
                "subject": subject,
                "duration_minutes": exam_duration,
                "passing_percentage": passing_marks,
                "question_count": str(len(texts)),
                "created_at": now,
                "created_by": session.get('student_id', 'admin'),
                "status": "active",
                "allowed_students": allowed_students_normalized
            }
            NormalizedCSVDB.create_exam(exam_data)
        except Exception as e:
            print(f"Error saving exam to normalized CSV: {e}")

    # ALSO save session metadata to CSV v2.0 (if available)
    if csv_manager:
        try:
            session_record = {
                "session_id": session_id,
                "content_hash": content_hash,
                "question_count": str(len(texts)),
                "created_at": now,
                "expires_at": "",
                "status": "active",
                "exam_duration_minutes": exam_duration,
                "created_by": "system",
                "version": "1.0",
                "exam_name": exam_name,
                "subject": subject,
                "passing_percentage": passing_marks,
                "allowed_students": ",".join(allowed_students) if allowed_students else "ALL"
            }
            csv_manager.write("sessions", [session_record], mode='append', validate=False)
        except Exception as e:
            print(f"Error saving to CSV v2.0: {e}")

    # Save correct answers if provided
    if correct_answers_str:
        num_questions = len(texts)
        # Validate length matches number of questions
        if len(correct_answers_str) == num_questions:
            # Validate all digits are 1-4
            if all(c in '1234' for c in correct_answers_str):
                # Save using CSV v2.0 - one row per question
                if csv_manager:
                    try:
                        answer_key_records = []
                        for idx, correct_option in enumerate(correct_answers_str):
                            answer_key_records.append({
                                "answer_key_id": f"{session_id}_q{idx}",
                                "session_id": session_id,
                                "question_index": str(idx),
                                "correct_option": correct_option,
                                "marks": "1",  # 1 mark per question
                                "created_at": now,
                                "version": "1.0"
                            })

                        csv_manager.write("answer_keys", answer_key_records, mode='append', validate=True)
                    except Exception as e:
                        print(f"Error saving answer keys to v2.0: {e}")

                # ALSO save to Normalized CSV (new format)
                if NormalizedCSVDB:
                    try:
                        questions = []
                        for idx, correct_option in enumerate(correct_answers_str, start=1):
                            # Get image URL for this question
                            image_url = ""
                            if idx <= len(image_urls):
                                image_url = image_urls[idx - 1].strip()

                            questions.append({
                                "exam_id": session_id,
                                "question_order": str(idx),
                                "correct_option": correct_option,
                                "marks": "1",
                                "image_url": image_url
                            })

                        NormalizedCSVDB.create_questions(questions)
                    except Exception as e:
                        print(f"Error saving questions to normalized CSV: {e}")
            else:
                print(f"Warning: Answer keys must be digits 1-4. Got: {correct_answers_str}")
        else:
            print(f"Warning: Answer key length ({len(correct_answers_str)}) doesn't match number of questions ({num_questions})")

    # Redirect to view route so URL is shareable (same questions for all users)
    return redirect(url_for("view_session", session_id=session_id))


@app.get("/view/<session_id>")
@limiter.limit("50 per minute")
def view_session(session_id: str):
    """View questions for a specific session ID - Public access, no login required"""
    student_id = session.get('student_id', 'guest')  # Default to guest if not logged in
    is_admin = session.get('is_admin', False)

    # Public platform - everyone can access all exams

    pdf_out_dir = GENERATED_DIR / session_id / "pdfs"

    if not pdf_out_dir.exists():
        return f"Session {session_id} not found. Please compile questions first.", 404

    # Get all PDF files
    cropped_paths = sorted(pdf_out_dir.glob("snippet_*.pdf"), key=lambda p: int(p.stem.split("_")[1]))

    if not cropped_paths:
        return f"No questions found for session {session_id}.", 404

    # Get session metadata
    metadata = get_session_metadata(session_id)

    # Build list of relative URLs to serve
    rel_urls = [f"/generated/{session_id}/pdfs/{p.name}" for p in cropped_paths]

    # Load image URLs from CSV file
    image_urls = {}  # Maps question index to image URL
    image_urls_file = GENERATED_DIR / session_id / "image_urls.csv"
    if image_urls_file.exists():
        try:
            with open(image_urls_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if row and len(row) >= 2:
                        question_idx = int(row[0])
                        url = row[1].strip()
                        if url:
                            image_urls[question_idx] = url
        except Exception as e:
            print(f"Error loading image URLs for {session_id}: {e}")

    return render_template(
        "output.html",
        pdf_urls=rel_urls,
        image_urls=image_urls,
        session_id=session_id,
        student_id=student_id,  # Pass logged-in student ID
        num_questions=len(rel_urls),
        exam_name=metadata["exam_name"],
        subject=metadata["subject"],
        duration_minutes=int(metadata["duration_minutes"]),
        passing_percentage=int(metadata["passing_percentage"])
    )


def get_dir_size(path: Path) -> int:
    """Get total size of directory in bytes"""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    except (OSError, PermissionError):
        pass
    return total


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_session_info(sess_dir: Path) -> dict:
    """Get information about a session directory"""
    pdf_dir = sess_dir / "pdfs"
    if not pdf_dir.exists():
        return None

    pdf_count = len(list(pdf_dir.glob("snippet_*.pdf")))
    if pdf_count == 0:
        return None
    
    size_bytes = get_dir_size(sess_dir)
    size_str = format_size(size_bytes)
    
    # Get creation time
    try:
        created_time = datetime.fromtimestamp(sess_dir.stat().st_ctime)
        created_date = created_time.strftime("%Y-%m-%d %H:%M:%S")
    except:
        created_date = "Unknown"
    
    return {
        "session_id": sess_dir.name,
        "question_count": pdf_count,
        "size": size_str,
        "size_bytes": size_bytes,
        "created_date": created_date,
        "url": f"/view/{sess_dir.name}"
    }


@app.get("/sessions")
@admin_required
def list_sessions():
    """List all available sessions"""
    sessions = []
    if GENERATED_DIR.exists():
        for sess_dir in GENERATED_DIR.iterdir():
            if sess_dir.is_dir() and sess_dir.name.startswith("session_"):
                session_info = get_session_info(sess_dir)
                if session_info:
                    sessions.append(session_info)
    
    # Sort by creation time (newest first)
    sessions.sort(key=lambda x: x.get("size_bytes", 0), reverse=True)
    
    # Create HTML response
    html = "<!DOCTYPE html><html><head><title>Available Sessions</title>"
    html += "<style>body{font-family:Arial;padding:20px;} .session{background:#f0f0f0;padding:10px;margin:10px 0;border-radius:5px;}"
    html += "a{color:#1f6feb;text-decoration:none;font-weight:bold;} a:hover{text-decoration:underline;}</style></head><body>"
    html += "<h1>Available MCQ Sessions</h1>"
    
    if not sessions:
        html += "<p>No sessions available. Please compile questions first.</p>"
    else:
        html += f"<p><a href='/manage-sessions' style='background:#dc3545;color:white;padding:8px 16px;border-radius:4px;text-decoration:none;'>Manage Sessions (Delete)</a></p>"
        html += "<p>Click on a session to view questions:</p>"
        for sess in sessions:
            html += f'<div class="session">'
            html += f'<a href="{sess["url"]}">{sess["session_id"]}</a>'
            html += f' - {sess["question_count"]} questions'
            html += f' - {sess["size"]}'
            html += '</div>'
    
    html += '<p><a href="/">Back to Input Page</a></p>'
    html += "</body></html>"
    return html


@app.get("/manage-sessions")
@admin_required
def manage_sessions():
    """Manage sessions - list all sessions with delete option"""
    sessions = []
    total_size_bytes = 0
    total_questions = 0
    
    if GENERATED_DIR.exists():
        for sess_dir in GENERATED_DIR.iterdir():
            if sess_dir.is_dir() and sess_dir.name.startswith("session_"):
                session_info = get_session_info(sess_dir)
                if session_info:
                    sessions.append(session_info)
                    total_size_bytes += session_info["size_bytes"]
                    total_questions += session_info["question_count"]
    
    # Sort by size (largest first)
    sessions.sort(key=lambda x: x.get("size_bytes", 0), reverse=True)
    
    return render_template("manage_sessions.html",
                         sessions=sessions,
                         total_sessions=len(sessions),
                         total_size=format_size(total_size_bytes),
                         total_questions=total_questions)


@app.post("/delete-session/<session_id>")
@admin_required
def delete_session(session_id: str):
    """Delete a specific session"""
    try:
        sess_dir = GENERATED_DIR / session_id
        
        # Validate session ID format for security
        if not session_id.startswith("session_") or not sess_dir.exists():
            return jsonify({"success": False, "error": "Invalid session ID"}), 400
        
        # Delete the session directory
        if sess_dir.exists():
            shutil.rmtree(sess_dir)
        
        # Also delete related answer key and answer files if they exist
        answer_key_file = ANSWER_KEYS_DIR / f"answer_key_{session_id}.csv"
        if answer_key_file.exists():
            answer_key_file.unlink()
        
        # Note: We keep answer files for record keeping, but you can delete them too if needed
        # answers_file = ANSWERS_DIR / f"answers_{session_id}.csv"
        # if answers_file.exists():
        #     answers_file.unlink()
        
        return jsonify({"success": True, "message": f"Session {session_id} deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.post("/delete-all-sessions")
@admin_required
def delete_all_sessions():
    """Delete all sessions"""
    try:
        deleted_count = 0
        total_size_freed = 0
        
        if GENERATED_DIR.exists():
            for sess_dir in GENERATED_DIR.iterdir():
                if sess_dir.is_dir() and sess_dir.name.startswith("session_"):
                    try:
                        size_bytes = get_dir_size(sess_dir)
                        shutil.rmtree(sess_dir)
                        deleted_count += 1
                        total_size_freed += size_bytes
                        
                        # Delete related answer key file
                        answer_key_file = ANSWER_KEYS_DIR / f"answer_key_{sess_dir.name}.csv"
                        if answer_key_file.exists():
                            answer_key_file.unlink()
                    except Exception as e:
                        print(f"Error deleting {sess_dir.name}: {e}")
                        continue
        
        return jsonify({
            "success": True,
            "message": f"Deleted {deleted_count} sessions",
            "deleted_count": deleted_count,
            "size_freed": format_size(total_size_freed)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/generated/<session_id>/pdfs/<path:filename>")
def serve_generated(session_id: str, filename: str):
    base = GENERATED_DIR / session_id / "pdfs"
    if not base.exists():
        abort(404)
    return send_from_directory(str(base), filename)


@app.post("/start-session")
@limiter.limit("20 per minute")
def start_session():
    """Start an exam session - Public access, no login required"""
    data = request.get_json()
    student_id = data.get("student_id", "").strip() or "guest"
    session_id = data.get("session_id", "").strip()

    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id"}), 400

    # Public platform - no whitelist checking, everyone can take exams

    # Check if session already exists for this student
    sessions_file = SESSIONS_DIR / "exam_sessions.csv"
    session_exists = False
    start_time = None
    
    if sessions_file.exists():
        with open(sessions_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Student_ID"] == student_id and row["Session_ID"] == session_id:
                    session_exists = True
                    start_time = datetime.strptime(row["Start_Time"], "%Y-%m-%d %H:%M:%S")
                    break
    
    if not session_exists:
        # Create new session entry
        start_time = datetime.now()
        file_exists = sessions_file.exists()

        with open(sessions_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Student_ID", "Session_ID", "Start_Time", "Date"])
            writer.writerow([
                student_id,
                session_id,
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                start_time.strftime("%Y-%m-%d")
            ])

        # Log session start activity
        log_student_activity(
            student_id=student_id,
            activity_type='session_start',
            session_id=session_id,
            details='Started new exam session'
        )
    else:
        # Log session resume activity
        log_student_activity(
            student_id=student_id,
            activity_type='session_resume',
            session_id=session_id,
            details='Resumed existing exam session'
        )

    return jsonify({
        "success": True,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "is_new": not session_exists
    })


@app.post("/check-session")
@limiter.limit("60 per minute")
def check_session():
    """Check if a session exists and calculate remaining time - Public access"""
    data = request.get_json()
    student_id = data.get("student_id", "").strip() or "guest"
    session_id = data.get("session_id", "").strip()

    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id"}), 400

    sessions_file = SESSIONS_DIR / "exam_sessions.csv"

    if not sessions_file.exists():
        return jsonify({"success": False, "exists": False})

    # Get exam duration from metadata
    metadata = get_session_metadata(session_id)
    duration_minutes = int(metadata["duration_minutes"])
    exam_duration = duration_minutes * 60  # Convert to seconds

    with open(sessions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Student_ID"] == student_id and row["Session_ID"] == session_id:
                start_time = datetime.strptime(row["Start_Time"], "%Y-%m-%d %H:%M:%S")
                current_time = datetime.now()
                elapsed_seconds = (current_time - start_time).total_seconds()

                remaining_seconds = max(0, exam_duration - elapsed_seconds)

                # Check if more than exam duration + 5 minutes grace period have passed (session expired)
                if elapsed_seconds > (exam_duration + 5 * 60):
                    return jsonify({
                        "success": True,
                        "exists": False,
                        "expired": True
                    })
                
                # Check if exam time is up
                if remaining_seconds <= 0:
                    return jsonify({
                        "success": True,
                        "exists": True,
                        "time_up": True,
                        "remaining_seconds": 0
                    })
                
                return jsonify({
                    "success": True,
                    "exists": True,
                    "start_time": row["Start_Time"],
                    "remaining_seconds": int(remaining_seconds),
                    "elapsed_seconds": int(elapsed_seconds)
                })
    
    return jsonify({"success": True, "exists": False})


def get_allowed_students(session_id: str) -> list:
    """Get list of allowed student IDs for THIS SPECIFIC SESSION from metadata"""
    # Read session-specific metadata
    metadata = get_session_metadata(session_id)
    allowed_students_str = metadata.get("allowed_students", "ALL")

    # If "ALL", everyone is allowed
    if allowed_students_str == "ALL" or not allowed_students_str:
        return ["ALL"]

    # Parse comma-separated (old format) or semicolon-separated (new format) list
    # Try semicolon first (new normalized format)
    if ";" in allowed_students_str:
        allowed_list = [s.strip() for s in allowed_students_str.split(";") if s.strip()]
    else:
        # Fallback to comma-separated (old format)
        allowed_list = [s.strip() for s in allowed_students_str.split(",") if s.strip()]

    # If empty after parsing, allow all
    if not allowed_list:
        return ["ALL"]

    return allowed_list


def is_student_allowed(session_id: str, student_id: str) -> bool:
    """Check if a student is allowed to take the exam"""
    allowed_students = get_allowed_students(session_id)

    # If "ALL" is in the list, everyone is allowed
    if "ALL" in allowed_students:
        return True

    # Check if student is in the whitelist
    return student_id in allowed_students


def get_session_metadata(session_id: str) -> dict:
    """Get metadata for a session - reads from legacy metadata file or normalized CSV"""
    metadata = {
        "exam_name": "Untitled Exam",
        "subject": "General",
        "duration_minutes": "25",
        "passing_percentage": "40",
        "allowed_students": "ALL",
        "question_count": "0",
        "created_at": ""
    }

    # Try reading from legacy metadata file first
    metadata_file = SESSION_METADATA_DIR / f"metadata_{session_id}.csv"
    metadata_found = False

    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) == 2:
                        field, value = row
                        if field == "Exam_Name":
                            metadata["exam_name"] = value
                        elif field == "Subject":
                            metadata["subject"] = value
                        elif field == "Duration_Minutes":
                            metadata["duration_minutes"] = value
                        elif field == "Passing_Percentage":
                            metadata["passing_percentage"] = value
                        elif field == "Allowed_Students":
                            metadata["allowed_students"] = value
                        elif field == "Question_Count":
                            metadata["question_count"] = value
                        elif field == "Created_At":
                            metadata["created_at"] = value
                metadata_found = True
        except Exception as e:
            print(f"Error reading legacy metadata: {e}")

    # Fallback to normalized CSV if legacy metadata doesn't exist
    if not metadata_found and NormalizedCSVDB:
        try:
            exam = NormalizedCSVDB.get_exam(session_id)
            if exam:
                metadata["exam_name"] = exam.get("exam_name", "Untitled Exam")
                metadata["subject"] = exam.get("subject", "General")
                metadata["duration_minutes"] = exam.get("duration_minutes", "25")
                metadata["passing_percentage"] = exam.get("passing_percentage", "40")
                metadata["allowed_students"] = exam.get("allowed_students", "ALL")
                metadata["question_count"] = exam.get("question_count", "0")
                metadata["created_at"] = exam.get("created_at", "")
        except Exception as e:
            print(f"Error reading normalized CSV metadata: {e}")

    return metadata


def get_answer_key(session_id: str) -> str | None:
    """Get answer key for a session"""
    answer_key_file = ANSWER_KEYS_DIR / f"answer_key_{session_id}.csv"
    if not answer_key_file.exists():
        return None

    with open(answer_key_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row.get("Answer_Key", "").strip()
    return None


def calculate_marks(student_answers: dict, answer_key: str | None) -> dict:
    """Calculate marks and return result details"""
    if not answer_key:
        # Count total questions from student answers
        total_questions = len([k for k in student_answers.keys() if k.startswith("cell")])
        return {
            "marks": 0,
            "total": total_questions,
            "correct_answers": {},
            "student_answers": student_answers,
            "wrong_questions": []
        }
    
    # Convert answer key string to dict (e.g., "142" -> {"cell0": "ক", "cell1": "ঘ", "cell2": "খ"})
    correct_dict = {}
    for i, key_char in enumerate(answer_key):
        # Map 1-4 to Bengali options: 1=ক, 2=খ, 3=গ, 4=ঘ
        option_map = {"1": "ক", "2": "খ", "3": "গ", "4": "ঘ"}
        correct_dict[f"cell{i}"] = option_map.get(key_char, "")
    
    # Convert student answers to question-indexed format
    student_dict = {}
    for key, value in student_answers.items():
        if key.startswith("cell"):
            student_dict[key] = value
    
    # Calculate marks
    marks = 0
    wrong_questions = []
    total = len(correct_dict)
    
    # Make sure we check all questions up to the answer key length
    for i in range(total):
        cell_key = f"cell{i}"
        correct_answer = correct_dict.get(cell_key, "")
        student_answer = student_dict.get(cell_key, "")
        
        if correct_answer and student_answer == correct_answer:
            marks += 1
        elif student_answer:  # Only count as wrong if student provided an answer
            wrong_questions.append(i)
    
    return {
        "marks": marks,
        "total": total,
        "correct_answers": correct_dict,
        "student_answers": student_dict,
        "wrong_questions": wrong_questions
    }


@app.post("/save-answers")
@limiter.limit("10 per minute")  # Prevent spam submissions
def save_answers():
    """Save student answers to CSV file and calculate marks - Public access"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"}), 400

        # Get student ID from session, or use guest
        student_id = session.get('student_id', 'guest')

        session_id = data.get("session_id", "").strip()
        answers = data.get("answers", {})

        if not session_id:
            return jsonify({"success": False, "error": "Missing session_id"}), 400

        if not isinstance(answers, dict):
            return jsonify({"success": False, "error": "Invalid answers format"}), 400

        # Get answer key to determine total number of questions
        answer_key = get_answer_key(session_id)

        # Get actual number of questions from session metadata or answer key
        metadata = get_session_metadata(session_id)
        num_questions = int(metadata.get("question_count", "0"))

        # If we can't get from metadata, try answer key
        if num_questions == 0 and answer_key:
            num_questions = len(answer_key)

        # If still 0, count from submitted answers (fallback)
        if num_questions == 0:
            num_questions = len([k for k in answers.keys() if k.startswith("cell")])

        if num_questions == 0:
            return jsonify({"success": False, "error": "Cannot determine number of questions"}), 400

        # Create complete answers dict with UNANSWERED for missing questions
        complete_answers = {}
        for i in range(num_questions):
            cell_key = f"cell{i}"
            complete_answers[cell_key] = answers.get(cell_key, "UNANSWERED")

        # Calculate marks using complete answers
        result = calculate_marks(complete_answers, answer_key)

        # Ensure result has all required fields
        if "correct_answers" not in result:
            result["correct_answers"] = {}
        if "wrong_questions" not in result:
            result["wrong_questions"] = []
        if "student_answers" not in result:
            result["student_answers"] = complete_answers
        if "marks" not in result:
            result["marks"] = 0
        if "total" not in result:
            result["total"] = num_questions

        # Create a single CSV file for all answers (or per session)
        csv_file = ANSWERS_DIR / f"answers_{session_id}.csv"

        # Check if CSV exists, if not create with headers
        file_exists = csv_file.exists()

        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header if new file
            if not file_exists:
                headers = ["Student_ID", "Session_ID", "Timestamp", "Marks", "Total"] + [f"Q{i+1}" for i in range(num_questions)]
                writer.writerow(headers)

            # Write answer row with ALL questions (including UNANSWERED)
            row = [
                student_id,
                session_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                result["marks"],
                result["total"]
            ]
            # Add all answers in order, using UNANSWERED for missing ones
            for i in range(num_questions):
                row.append(complete_answers.get(f"cell{i}", "UNANSWERED"))
            writer.writerow(row)

        # ALSO save to Normalized CSV (new format)
        if NormalizedCSVDB:
            try:
                # Check if student already submitted (duplicate prevention)
                if not NormalizedCSVDB.has_submitted(session_id, student_id):
                    # Prepare submission data
                    submission_data = {
                        "exam_id": session_id,
                        "student_id": student_id,
                        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "score": str(result["marks"]),
                        "total_marks": str(result["total"]),
                        "time_taken_seconds": "",
                        "ip_address": request.remote_addr or "",
                        "device_info": "",
                        "status": "completed"
                    }

                    # Prepare answers with is_correct flag
                    answer_details = []
                    for i in range(num_questions):
                        cell_key = f"cell{i}"
                        selected = complete_answers.get(cell_key, "UNANSWERED")

                        # Convert Bengali to number
                        option_map = {'ক': '1', 'খ': '2', 'গ': '3', 'ঘ': '4'}
                        selected_option = option_map.get(selected, "0")

                        # Determine if correct
                        correct_option = answer_key.get(i, "0") if answer_key else "0"
                        is_correct = "true" if selected_option == str(correct_option) else "false"

                        if selected != "UNANSWERED":
                            answer_details.append({
                                "question_order": str(i + 1),
                                "selected_option": selected_option,
                                "is_correct": is_correct,
                                "time_spent_seconds": ""
                            })

                    # Create submission
                    NormalizedCSVDB.create_submission(submission_data, answer_details)
            except Exception as e:
                print(f"Error saving submission to normalized CSV: {e}")

        # Log answer submission activity
        log_student_activity(
            student_id=student_id,
            activity_type='answer_submit',
            session_id=session_id,
            details=f"Submitted answers - Score: {result['marks']}/{result['total']}"
        )

        return jsonify({
            "success": True,
            "message": "Answers saved successfully",
            "marks": result["marks"],
            "total": result["total"],
            "correct_answers": result.get("correct_answers", {}),
            "wrong_questions": result.get("wrong_questions", []),
            "student_answers": result.get("student_answers", complete_answers)
        })
    except Exception as e:
        import traceback
        print(f"Error in save_answers: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/marks")
@admin_required
def marks_list():
    """List all sessions that have student submissions"""
    sessions_with_marks = []

    if ANSWERS_DIR.exists():
        for answers_file in ANSWERS_DIR.glob("answers_*.csv"):
            try:
                session_id = answers_file.stem.replace("answers_", "")

                # Read the answers file to get statistics
                with open(answers_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

                    if not rows:
                        continue

                    # Calculate statistics
                    num_students = len(rows)
                    total_questions = rows[0].get("Total", "0") if rows else "0"

                    # Calculate average marks
                    total_marks = 0
                    for row in rows:
                        marks = row.get("Marks", "0")
                        try:
                            total_marks += int(marks)
                        except:
                            pass

                    avg_marks = total_marks / num_students if num_students > 0 else 0

                    sessions_with_marks.append({
                        "session_id": session_id,
                        "num_students": num_students,
                        "total_questions": total_questions,
                        "avg_marks": f"{avg_marks:.2f}",
                        "file_name": answers_file.name
                    })

            except Exception as e:
                print(f"Error processing {answers_file.name}: {e}")
                continue

    # Sort by number of students (descending)
    sessions_with_marks.sort(key=lambda x: x["num_students"], reverse=True)

    return render_template("marks_list.html", sessions=sessions_with_marks)


@app.get("/marks/<session_id>")
@admin_required
def view_marks(session_id: str):
    """View detailed marks for a specific session"""
    answers_file = ANSWERS_DIR / f"answers_{session_id}.csv"

    if not answers_file.exists():
        return render_template("error.html" if (APP_ROOT / "templates" / "error.html").exists() else "marks_list.html",
                             error=f"No marks found for session {session_id}"), 404

    # Get session metadata for passing percentage
    metadata = get_session_metadata(session_id)
    passing_percentage = int(metadata["passing_percentage"])

    # Read all student submissions
    students = []
    headers = []

    try:
        with open(answers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            if not headers:
                return f"Invalid CSV file for session {session_id}", 500

            for row in reader:
                student_id = row.get("Student_ID", "Unknown")
                marks = row.get("Marks", "0")
                total = row.get("Total", "0")
                timestamp = row.get("Timestamp", "")

                # Get all answer columns (Q1, Q2, Q3, ...)
                answers = []
                q_num = 1
                while f"Q{q_num}" in row:
                    answers.append(row.get(f"Q{q_num}", ""))
                    q_num += 1

                # Calculate percentage
                try:
                    percentage = (int(marks) / int(total) * 100) if int(total) > 0 else 0
                except:
                    percentage = 0

                # Determine result using custom passing percentage
                result = "Pass" if percentage >= passing_percentage else "Fail"

                students.append({
                    "student_id": student_id,
                    "marks": marks,
                    "total": total,
                    "percentage": f"{percentage:.1f}",
                    "result": result,
                    "timestamp": timestamp,
                    "answers": answers,
                    "num_questions": len(answers)
                })

        if not students:
            return f"No student data found for session {session_id}. Students may not have submitted yet.", 200

        # Sort by marks (descending)
        students.sort(key=lambda x: int(x.get("marks", 0)), reverse=True)

        # Get answer key if available
        answer_key_file = ANSWER_KEYS_DIR / f"answer_key_{session_id}.csv"
        answer_key = None
        answer_key_bengali = []

        if answer_key_file.exists():
            try:
                with open(answer_key_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        answer_key = row.get("Answer_Key", "")
                        break

                # Convert answer key to Bengali options
                if answer_key:
                    option_map = {"1": "ক", "2": "খ", "3": "গ", "4": "ঘ"}
                    answer_key_bengali = [option_map.get(c, c) for c in answer_key]
            except Exception as e:
                print(f"Warning: Could not read answer key: {e}")

        # Calculate statistics
        total_students = len(students)
        if total_students > 0:
            try:
                avg_marks = sum(int(s["marks"]) for s in students) / total_students
                passing_students = sum(1 for s in students if s["result"] == "Pass")
                pass_rate = (passing_students / total_students) * 100
            except:
                avg_marks = 0
                passing_students = 0
                pass_rate = 0
        else:
            avg_marks = 0
            passing_students = 0
            pass_rate = 0

        stats = {
            "total_students": total_students,
            "avg_marks": f"{avg_marks:.2f}",
            "passing_students": passing_students,
            "pass_rate": f"{pass_rate:.1f}",
            "total_questions": students[0]["total"] if students else "0"
        }

        return render_template(
            "marks_detail.html",
            session_id=session_id,
            students=students,
            stats=stats,
            answer_key=answer_key_bengali
        )

    except Exception as e:
        import traceback
        error_msg = f"Error reading marks for session {session_id}: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return f"<h1>Error Loading Marks</h1><p>{error_msg}</p><p><a href='/marks'>← Back to Marks List</a></p>", 500


@app.get("/manage-students/<session_id>")
@admin_required
def manage_students(session_id: str):
    """View and manage allowed students for THIS SPECIFIC SESSION"""
    # Get session metadata
    metadata = get_session_metadata(session_id)

    # Get session-specific allowed students
    allowed_students_list = get_allowed_students(session_id)

    students = []
    if allowed_students_list == ["ALL"]:
        # Show indicator that all students are allowed
        students.append({
            "student_id": "ALL",
            "added_at": metadata.get("created_at", ""),
            "status": "Active"
        })
    else:
        # Show specific students for this session
        created_at = metadata.get("created_at", "")
        for student_id in allowed_students_list:
            students.append({
                "student_id": student_id,
                "added_at": created_at,
                "status": "Active"
            })

    # Check if this session has questions
    pdf_dir = GENERATED_DIR / session_id / "pdfs"
    session_exists = pdf_dir.exists() and list(pdf_dir.glob("snippet_*.pdf"))

    return render_template(
        "manage_students.html",
        session_id=session_id,
        students=students,
        metadata=metadata,
        session_exists=session_exists
    )


@app.post("/add-student/<session_id>")
@admin_required
def add_student(session_id: str):
    """Add a student to THIS SESSION's allowed list"""
    try:
        data = request.get_json() or request.form
        new_student_id = data.get("student_id", "").strip()

        if not new_student_id:
            return jsonify({"success": False, "error": "Student ID is required"}), 400

        # Get current session metadata
        metadata_file = SESSION_METADATA_DIR / f"metadata_{session_id}.csv"
        if not metadata_file.exists():
            return jsonify({"success": False, "error": "Session not found"}), 404

        # Read current metadata
        metadata = {}
        with open(metadata_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) == 2:
                    metadata[row[0]] = row[1]

        # Get current allowed students
        current_allowed = metadata.get("Allowed_Students", "ALL")

        # Special case: "ALL" means allow everyone (clear whitelist)
        if new_student_id.upper() == "ALL":
            metadata["Allowed_Students"] = "ALL"
        else:
            # Parse current list
            if current_allowed == "ALL" or not current_allowed:
                allowed_list = []
            else:
                allowed_list = [s.strip() for s in current_allowed.split(",") if s.strip()]

            # Add new student if not already in list
            if new_student_id not in allowed_list:
                allowed_list.append(new_student_id)

            # Update metadata
            metadata["Allowed_Students"] = ",".join(allowed_list)

        # Write back to file
        with open(metadata_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Field", "Value"])
            for key, value in metadata.items():
                writer.writerow([key, value])

        message = "Now allowing all students" if new_student_id.upper() == "ALL" else f"Added student {new_student_id}"
        return jsonify({"success": True, "message": message})

    except Exception as e:
        import traceback
        print(f"Error adding student: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.post("/remove-student/<session_id>")
@admin_required
def remove_student(session_id: str):
    """Remove a student from THIS SESSION's allowed list"""
    try:
        data = request.get_json() or request.form
        student_id_to_remove = data.get("student_id", "").strip()

        if not student_id_to_remove:
            return jsonify({"success": False, "error": "Student ID is required"}), 400

        # Cannot remove "ALL" marker
        if student_id_to_remove.upper() == "ALL":
            return jsonify({"success": False, "error": "Cannot remove ALL marker. Add specific students instead."}), 400

        # Get current session metadata
        metadata_file = SESSION_METADATA_DIR / f"metadata_{session_id}.csv"
        if not metadata_file.exists():
            return jsonify({"success": False, "error": "Session not found"}), 404

        # Read current metadata
        metadata = {}
        with open(metadata_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) == 2:
                    metadata[row[0]] = row[1]

        # Get current allowed students
        current_allowed = metadata.get("Allowed_Students", "ALL")

        if current_allowed == "ALL":
            return jsonify({"success": False, "error": "All students are allowed. Cannot remove from empty whitelist."}), 400

        # Parse current list
        allowed_list = [s.strip() for s in current_allowed.split(",") if s.strip()]

        # Remove student
        if student_id_to_remove in allowed_list:
            allowed_list.remove(student_id_to_remove)
        else:
            return jsonify({"success": False, "error": "Student not found in allowed list"}), 404

        # Update metadata (if empty, set to empty string, not "ALL")
        metadata["Allowed_Students"] = ",".join(allowed_list) if allowed_list else ""

        # Write back to file
        with open(metadata_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Field", "Value"])
            for key, value in metadata.items():
                writer.writerow([key, value])

        return jsonify({"success": True, "message": f"Removed student {student_id_to_remove}"})

    except Exception as e:
        import traceback
        print(f"Error removing student: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/admin/login-sessions")
@admin_required
def view_login_sessions():
    """Admin-only page to view and manage active login sessions"""
    # Get all sessions (active and terminated)
    all_sessions = get_all_active_sessions()

    # Calculate statistics
    active_sessions = [s for s in all_sessions if s.get('Status') == 'active']
    terminated_sessions = [s for s in all_sessions if s.get('Status') == 'terminated']

    # Count unique students
    unique_students = len(set(s.get('Student_ID') for s in active_sessions if s.get('Student_ID')))

    # Count admin vs student sessions
    admin_sessions_count = len([s for s in active_sessions if s.get('Is_Admin') == 'Yes'])
    student_sessions_count = len([s for s in active_sessions if s.get('Is_Admin') == 'No'])

    return render_template(
        "login_sessions.html",
        all_sessions=all_sessions,
        active_sessions=active_sessions,
        terminated_sessions=terminated_sessions,
        total_active=len(active_sessions),
        total_terminated=len(terminated_sessions),
        unique_students=unique_students,
        admin_sessions_count=admin_sessions_count,
        student_sessions_count=student_sessions_count
    )


@app.post("/admin/force-logout/<session_id>")
@admin_required
def admin_force_logout(session_id: str):
    """Force logout a specific session (admin action)"""
    try:
        force_logout_session(session_id)
        return jsonify({"success": True, "message": f"Session {session_id[:16]}... forcefully logged out"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/admin/activity-logs")
@admin_required
def view_activity_logs():
    """Admin-only page to view student activity logs"""
    # Get filter parameters
    student_filter = request.args.get('student_id', '').strip()
    activity_filter = request.args.get('activity_type', '').strip()
    limit = int(request.args.get('limit', '500'))

    # Get logs
    if student_filter:
        logs = get_student_activity_logs(student_filter)
    else:
        logs = get_all_activity_logs(limit=limit)

    # Apply activity type filter if specified
    if activity_filter and logs:
        logs = [log for log in logs if log.get('Activity_Type') == activity_filter]

    # Get unique student IDs and activity types for filters
    unique_students = sorted(set(log.get('Student_ID', '') for log in logs if log.get('Student_ID')))
    unique_activities = sorted(set(log.get('Activity_Type', '') for log in logs if log.get('Activity_Type')))

    # Count statistics
    total_logins = len([log for log in logs if log.get('Activity_Type') == 'login'])
    total_sessions = len([log for log in logs if log.get('Activity_Type') == 'session_start'])
    total_submissions = len([log for log in logs if log.get('Activity_Type') == 'answer_submit'])
    unique_student_count = len(unique_students)

    return render_template(
        "activity_logs.html",
        logs=logs,
        student_filter=student_filter,
        activity_filter=activity_filter,
        limit=limit,
        unique_students=unique_students,
        unique_activities=unique_activities,
        total_logins=total_logins,
        total_sessions=total_sessions,
        total_submissions=total_submissions,
        unique_student_count=unique_student_count
    )


@app.route("/admin/settings", methods=['GET', 'POST'])
@admin_required
def admin_settings():
    """Admin-only page to manage global application settings"""
    if request.method == 'POST':
        # Handle auth toggle
        auth_enabled = request.form.get('auth_required') == 'on'
        set_auth_required(auth_enabled)

        if auth_enabled:
            flash('✓ Authentication enabled - Login required for all users', 'success')
        else:
            flash('⚠️ Authentication disabled - Site is now publicly accessible without login', 'warning')

        return redirect(url_for('admin_settings'))

    # GET request - show current settings
    auth_required = get_auth_required()

    return render_template(
        "admin_settings.html",
        auth_required=auth_required
    )


@app.route("/health")
def health_check():
    """Health check endpoint for deployment services"""
    return jsonify({"status": "healthy", "service": "mcq-app"}), 200


if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host=HOST, port=PORT, debug=debug)


