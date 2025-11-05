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
    """Return LaTeX body between \begin{document} and \end{document} if present; otherwise original."""
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
        for _ in range(2):
            run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name], cwd=tdir)

        pdf_path = tdir / f"snippet_{idx}.pdf"
        if not pdf_path.exists():
            raise RuntimeError(f"Expected PDF not produced: {pdf_path}")

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
    col_def = "|" + "|".join(["m{0.48\\textwidth}"] * columns) + "|"
    lines = []
    lines.append("\\documentclass[12pt]{article}")
    lines.append("\\usepackage{graphicx}")
    lines.append("\\usepackage{array}")
    lines.append("\\usepackage[margin=0.5in]{geometry}")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.3}")
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
                row_cells.append(f"\\centering\\includegraphics[width=\\linewidth]{{{path}}}")
            else:
                row_cells.append("~")
        lines.append(" & ".join(row_cells) + " \\\\")
    lines.append("\\end{tabular}")
    lines.append("\\end{document}")
    return "\n".join(lines)


def build_sheets(snippet_texts: list[str]):
    ensure_dirs()
    template = load_snippet_template()

    cropped_paths: list[Path] = []
    for i, snippet in enumerate(snippet_texts, start=1):
        rendered = render_snippet_tex(template, snippet)
        cropped = compile_snippet(rendered, i)
        cropped_paths.append(cropped)

    # 2-column desktop: 20 rows per column (40 cells)
    two_col_tex = generate_sheet_tex(cropped_paths, columns=2, rows=20, title="MCQ Sheet (2-Column)")
    two_col_path = OUT_DIR / "sheet_2col.tex"
    two_col_path.write_text(two_col_tex, encoding="utf-8")
    run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", two_col_path.name], cwd=OUT_DIR)

    # 1-column mobile: 40 rows (40 cells)
    one_col_tex = generate_sheet_tex(cropped_paths, columns=1, rows=40, title="MCQ Sheet (1-Column)")
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


