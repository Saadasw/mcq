import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
SNIPPET_TEMPLATE = (TEMPLATES_DIR / "snippet_template.tex").read_text(encoding="utf-8")
GENERATED_DIR = APP_ROOT / "generated"


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

    session_id = str(int(time.time()))
    sess_dir = ensure_clean_session_dir(session_id)
    pdf_out_dir = sess_dir / "pdfs"

    cropped_paths: List[Path] = []
    for i, txt in enumerate(texts, start=1):
        try:
            cropped = compile_and_crop_snippet(txt, pdf_out_dir, i)
            cropped_paths.append(cropped)
        except Exception as e:
            # Write an error placeholder PDF? For simplicity, skip and leave empty cell
            print("Compile error:", e)
            continue

    # Build list of relative URLs to serve
    rel_urls = [f"/generated/{session_id}/pdfs/{p.name}" for p in cropped_paths]
    return render_template("output.html", pdf_urls=rel_urls, session_id=session_id)


@app.get("/generated/<session_id>/pdfs/<path:filename>")
def serve_generated(session_id: str, filename: str):
    base = GENERATED_DIR / session_id / "pdfs"
    if not base.exists():
        abort(404)
    return send_from_directory(str(base), filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


