import os
import re
import shutil
import subprocess
import tempfile
import time
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort, jsonify


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
SNIPPET_TEMPLATE = (TEMPLATES_DIR / "snippet_template.tex").read_text(encoding="utf-8")
GENERATED_DIR = APP_ROOT / "generated"
ANSWERS_DIR = APP_ROOT / "answers"
SESSIONS_DIR = APP_ROOT / "sessions"
ANSWER_KEYS_DIR = APP_ROOT / "answer_keys"
ANSWERS_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
ANSWER_KEYS_DIR.mkdir(exist_ok=True)


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
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        tex_path = tdir / f"snippet_{idx}.tex"
        tex_path.write_text(render_snippet_tex(content), encoding="utf-8")
        for _ in range(2):
            run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name], cwd=tdir)
        pdf_path = tdir / f"snippet_{idx}.pdf"
        if not pdf_path.exists():
            raise RuntimeError("PDF not produced for snippet")
        # No cropping: copy compiled PDF directly into session output dir
        final_pdf = out_dir / f"snippet_{idx}.pdf"
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

# Get port from environment variable, default to 5000
PORT = int(os.environ.get("PORT", 5000))
# Get host from environment variable, default to 0.0.0.0
HOST = os.environ.get("HOST", "0.0.0.0")


@app.route("/")
def input_page():
    return render_template("input.html")


@app.post("/compile")
def compile_route():
    # inputs come as texts[]
    texts = request.form.getlist("texts[]")
    # Filter out empties/whitespace-only
    texts = [t for t in (x.strip() for x in texts) if t]
    if not texts:
        return redirect(url_for("input_page"))

    # Get correct answers
    correct_answers_str = request.form.get("correct_answers", "").strip()
    
    # Use a fixed session ID based on content hash to ensure same questions for all users
    content_hash = hashlib.md5("|".join(texts).encode()).hexdigest()[:8]
    session_id = f"session_{content_hash}"
    
    sess_dir = GENERATED_DIR / session_id
    pdf_out_dir = sess_dir / "pdfs"
    
    # Only compile if PDFs don't already exist (same questions for all users)
    if not pdf_out_dir.exists() or not list(pdf_out_dir.glob("*.pdf")):
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

    # Save correct answers if provided
    if correct_answers_str:
        num_questions = len(texts)
        # Validate length matches number of questions
        if len(correct_answers_str) == num_questions:
            # Validate all digits are 1-4
            if all(c in '1234' for c in correct_answers_str):
                answer_key_file = ANSWER_KEYS_DIR / f"answer_key_{session_id}.csv"
                with open(answer_key_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Session_ID", "Answer_Key"])
                    writer.writerow([session_id, correct_answers_str])
            else:
                print(f"Warning: Answer keys must be digits 1-4. Got: {correct_answers_str}")
        else:
            print(f"Warning: Answer key length ({len(correct_answers_str)}) doesn't match number of questions ({num_questions})")

    # Redirect to view route so URL is shareable (same questions for all users)
    return redirect(url_for("view_session", session_id=session_id))


@app.get("/view/<session_id>")
def view_session(session_id: str):
    """View questions for a specific session ID"""
    pdf_out_dir = GENERATED_DIR / session_id / "pdfs"
    
    if not pdf_out_dir.exists():
        return f"Session {session_id} not found. Please compile questions first.", 404
    
    # Get all PDF files
    cropped_paths = sorted(pdf_out_dir.glob("snippet_*.pdf"), key=lambda p: int(p.stem.split("_")[1]))
    
    if not cropped_paths:
        return f"No questions found for session {session_id}.", 404
    
    # Build list of relative URLs to serve
    rel_urls = [f"/generated/{session_id}/pdfs/{p.name}" for p in cropped_paths]
    return render_template("output.html", pdf_urls=rel_urls, session_id=session_id, num_questions=len(rel_urls))


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
    
    pdf_count = len(list(pdf_dir.glob("*.pdf")))
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
def start_session():
    """Start an exam session for a student"""
    data = request.get_json()
    student_id = data.get("student_id", "").strip()
    session_id = data.get("session_id", "").strip()
    
    if not student_id or not session_id:
        return jsonify({"success": False, "error": "Missing student_id or session_id"}), 400
    
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
    
    return jsonify({
        "success": True,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "is_new": not session_exists
    })


@app.post("/check-session")
def check_session():
    """Check if a session exists and calculate remaining time"""
    data = request.get_json()
    student_id = data.get("student_id", "").strip()
    session_id = data.get("session_id", "").strip()
    
    if not student_id or not session_id:
        return jsonify({"success": False, "error": "Missing student_id or session_id"}), 400
    
    sessions_file = SESSIONS_DIR / "exam_sessions.csv"
    
    if not sessions_file.exists():
        return jsonify({"success": False, "exists": False})
    
    with open(sessions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Student_ID"] == student_id and row["Session_ID"] == session_id:
                start_time = datetime.strptime(row["Start_Time"], "%Y-%m-%d %H:%M:%S")
                current_time = datetime.now()
                elapsed_seconds = (current_time - start_time).total_seconds()
                
                # Exam duration is 25 minutes (1500 seconds)
                exam_duration = 25 * 60
                remaining_seconds = max(0, exam_duration - elapsed_seconds)
                
                # Check if more than 30 minutes have passed (session expired)
                if elapsed_seconds > 30 * 60:
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
def save_answers():
    """Save student answers to CSV file and calculate marks"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"}), 400
            
        student_id = data.get("student_id", "").strip()
        session_id = data.get("session_id", "").strip()
        answers = data.get("answers", {})
        
        if not student_id or not session_id:
            return jsonify({"success": False, "error": "Missing student_id or session_id"}), 400
        
        if not answers or not isinstance(answers, dict):
            return jsonify({"success": False, "error": "Invalid answers format"}), 400
        
        # Get answer key for this session
        answer_key = get_answer_key(session_id)
        
        # Calculate marks
        result = calculate_marks(answers, answer_key)
        
        # Ensure result has all required fields
        if "correct_answers" not in result:
            result["correct_answers"] = {}
        if "wrong_questions" not in result:
            result["wrong_questions"] = []
        if "student_answers" not in result:
            result["student_answers"] = answers
        if "marks" not in result:
            result["marks"] = 0
        if "total" not in result:
            result["total"] = len([k for k in answers.keys() if k.startswith("cell")])
        
        # Create a single CSV file for all answers (or per session)
        csv_file = ANSWERS_DIR / f"answers_{session_id}.csv"
        
        # Check if CSV exists, if not create with headers
        file_exists = csv_file.exists()
        
        # Get number of questions from answers
        num_questions = len([k for k in answers.keys() if k.startswith("cell")])
        
        if num_questions == 0:
            return jsonify({"success": False, "error": "No valid answers found"}), 400
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header if new file
            if not file_exists:
                headers = ["Student_ID", "Session_ID", "Timestamp", "Marks", "Total"] + [f"Q{i+1}" for i in range(num_questions)]
                writer.writerow(headers)
            
            # Write answer row
            row = [
                student_id, 
                session_id, 
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                result["marks"],
                result["total"]
            ]
            # Sort answers by question number
            sorted_answers = sorted(answers.items(), key=lambda x: int(x[0].replace("cell", "")))
            row.extend([ans for _, ans in sorted_answers])
            writer.writerow(row)
        
        return jsonify({
            "success": True, 
            "message": "Answers saved successfully",
            "marks": result["marks"],
            "total": result["total"],
            "correct_answers": result.get("correct_answers", {}),
            "wrong_questions": result.get("wrong_questions", []),
            "student_answers": result.get("student_answers", answers)
        })
    except Exception as e:
        import traceback
        print(f"Error in save_answers: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health")
def health_check():
    """Health check endpoint for deployment services"""
    return jsonify({"status": "healthy", "service": "mcq-app"}), 200


if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host=HOST, port=PORT, debug=debug)


