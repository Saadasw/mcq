import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates"
INPUT_SNIPPETS_DIR = REPO_ROOT / "inputs" / "snippets"
OUT_DIR = REPO_ROOT / "out"
OUT_SNIPPETS_DIR = OUT_DIR / "snippets"


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}\n\n{result.stdout}")
    return result.stdout


def ensure_dirs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)


def load_snippet_template() -> str:
    template = (TEMPLATES_DIR / "snippet_template.tex").read_text(encoding="utf-8")
    return template


def extract_body(content: str) -> str:
    r"""Return LaTeX body between \begin{document} and \end{document} if present; otherwise original."""
    m = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", content, flags=re.S)
    if m:
        return m.group(1).strip()
    return content.strip()


def render_snippet_tex(template: str, content: str) -> str:
    body = extract_body(content)
    return template.replace("% CONTENT_HERE", body)


def compile_snippet(content_tex: str, idx: int) -> Path:
    """Compile a single snippet to a PDF and return its final path under OUT_SNIPPETS_DIR."""
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        tex_path = tdir / f"snippet_{idx}.tex"
        tex_path.write_text(content_tex, encoding="utf-8")

        # Compile with lualatex (twice for stability if needed)
        # Use nonstopmode but don't halt on error to get better error messages
        for attempt in range(2):
            result = subprocess.run(
                ["lualatex", "-interaction=nonstopmode", tex_path.name],
                cwd=tdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            # On second attempt, check if PDF was created
            if attempt == 1:
                pdf_path = tdir / f"snippet_{idx}.pdf"
                if not pdf_path.exists():
                    # Try to read the log file for better error messages
                    log_path = tdir / f"snippet_{idx}.log"
                    error_details = ""
                    if log_path.exists():
                        log_content = log_path.read_text(encoding="utf-8", errors="ignore")
                        # Extract error messages from log
                        error_lines = [line for line in log_content.split("\n") if "!" in line or "Error" in line or "Fatal" in line]
                        if error_lines:
                            error_details = "\n".join(error_lines[-10:])  # Last 10 error lines
                    raise RuntimeError(
                        f"Failed to compile snippet {idx}.\n"
                        f"LaTeX return code: {result.returncode}\n"
                        f"Last output:\n{result.stdout[-1000:]}\n"
                        f"Errors from log:\n{error_details}"
                    )

        pdf_path = tdir / f"snippet_{idx}.pdf"
        if not pdf_path.exists():
            raise RuntimeError(f"Expected PDF not produced for snippet {idx}: {pdf_path}")

        # No cropping: copy the compiled PDF directly to output snippets dir
        final_pdf = OUT_SNIPPETS_DIR / f"snippet_{idx}.pdf"
        shutil.copy2(pdf_path, final_pdf)

    return final_pdf


def read_inputs_from_dir() -> list[str]:
    inputs = []
    if INPUT_SNIPPETS_DIR.exists():
        for p in sorted(INPUT_SNIPPETS_DIR.glob("*.tex")):
            inputs.append(p.read_text(encoding="utf-8"))
    return inputs


def generate_sheet_tex(pdf_paths: list[Path], columns: int, rows: int, title: str) -> str:
    # Build a tabular with columns columns and rows rows (total cells = columns*rows)
    # Each cell includes the cropped snippet PDF, width=\linewidth
    # Use larger column width for better visibility (0.49 for 2 columns, 0.95 for 1 column)
    col_width = "0.49\\textwidth" if columns == 2 else "0.95\\textwidth"
    col_def = "|" + "|".join([f"m{{{col_width}}}"] * columns) + "|"
    lines = []
    lines.append("\\documentclass[12pt]{article}")
    lines.append("\\usepackage{graphicx}")
    lines.append("\\usepackage{array}")
    lines.append("\\usepackage[paperwidth=105mm,paperheight=148mm,margin=0.2in]{geometry}")  # Half width of A5 landscape for larger text
    lines.append("\\usepackage{polyglossia}")
    lines.append("\\usepackage{tikz}")
    lines.append("\\setmainlanguage{bengali}")
    lines.append("\\newfontfamily\\bengalifont[Script=Bengali]{Nirmala UI}")
    lines.append("\\AtBeginDocument{\\fontsize{14}{18}\\selectfont}")  # Larger font for better readability
    lines.append("\\setlength{\\tabcolsep}{10pt}")  # Increased column separation
    lines.append("\\renewcommand{\\arraystretch}{1.8}")  # Increased row height for bigger cells
    # Larger, more visible radio buttons
    lines.append("\\newcommand{\\radiobutton}[1]{\\tikz[baseline=-0.3ex]{\\draw[black,line width=0.8pt,fill=white] (0,0) circle (0.25em);}\\hspace{0.3em}\\normalsize#1\\hspace{0.5em}}")
    lines.append("\\begin{document}")
    lines.append(f"\\section*{{{title}}}")
    lines.append(f"\\begin{{tabular}}{{{col_def}}}")

    total_cells = columns * rows
    cells = [str(p).replace("\\", "/") for p in pdf_paths][:total_cells]
    # pad with empties
    while len(cells) < total_cells:
        cells.append("")

    # fill row-wise
    for r in range(rows):
        row_cells = []
        for c in range(columns):
            idx = r + c * rows  # column-major to distribute evenly top-down per column
            path = cells[idx]
            if path:
                # Create cell content with PDF and radio buttons at bottom
                cell_content = []
                cell_content.append("\\centering")
                # Use scalebox to make PDF content slightly larger if needed
                cell_content.append(f"\\includegraphics[width=0.98\\linewidth,keepaspectratio]{{{path}}}")
                cell_content.append("\\\\[0.5em]")  # Increased spacing before radio buttons
                # Radio buttons: ক, খ, গ, ঘ - using normal size instead of small
                cell_content.append("\\radiobutton{ক}\\radiobutton{খ}\\radiobutton{গ}\\radiobutton{ঘ}")
                row_cells.append(" ".join(cell_content))
            else:
                row_cells.append("~")
        lines.append(" & ".join(row_cells) + " \\\\[0.2em]")  # Added extra row spacing
    lines.append("\\end{tabular}")
    lines.append("\\end{document}")
    return "\n".join(lines)


def build_sheets(snippet_texts: list[str]):
    ensure_dirs()
    template = load_snippet_template()

    cropped_paths: list[Path] = []
    for i, snippet in enumerate(snippet_texts, start=1):
        try:
            print(f"Compiling snippet {i}/{len(snippet_texts)}...", end=" ", flush=True)
            rendered = render_snippet_tex(template, snippet)
            cropped = compile_snippet(rendered, i)
            cropped_paths.append(cropped)
            print("[OK]")
        except Exception as e:
            print("[FAILED]")
            print(f"Error compiling snippet {i}: {e}")
            print(f"Skipping snippet {i} and continuing with others...")
            # Continue with other snippets instead of failing completely
            continue

    # 2-column desktop: 15 rows per column (30 cells) - reduced for bigger cells
    two_col_tex = generate_sheet_tex(cropped_paths, columns=2, rows=15, title="MCQ Sheet (2-Column)")
    two_col_path = OUT_DIR / "sheet_2col.tex"
    two_col_path.write_text(two_col_tex, encoding="utf-8")
    run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", two_col_path.name], cwd=OUT_DIR)

    # 1-column mobile: 30 rows (30 cells) - reduced for bigger cells
    one_col_tex = generate_sheet_tex(cropped_paths, columns=1, rows=30, title="MCQ Sheet (1-Column)")
    one_col_path = OUT_DIR / "sheet_1col.tex"
    one_col_path.write_text(one_col_tex, encoding="utf-8")
    run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", one_col_path.name], cwd=OUT_DIR)

    print("\nGenerated:")
    print(f" - {OUT_DIR / 'sheet_2col.pdf'}")
    print(f" - {OUT_DIR / 'sheet_1col.pdf'}")


def main():
    parser = argparse.ArgumentParser(description="Build MCQ sheets from LaTeX snippets.")
    parser.add_argument("--inputs", nargs="*", help="Optional snippet files (.tex). If omitted, reads inputs/snippets/*.tex")
    args = parser.parse_args()

    if args.inputs:
        texts = [Path(p).read_text(encoding="utf-8") for p in args.inputs]
    else:
        texts = read_inputs_from_dir()

    if not texts:
        example = INPUT_SNIPPETS_DIR / "example1.tex"
        raise SystemExit(
            f"No snippet inputs found. Add .tex files under {INPUT_SNIPPETS_DIR} or pass files via --inputs.\n"
            f"Example snippet: {example}")

    build_sheets(texts)


if __name__ == "__main__":
    main()


