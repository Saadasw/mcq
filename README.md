## LuaLaTeX + Bengali (polyglossia) setup on Ubuntu Desktop and Ubuntu Server

This guide helps you reproduce the same setup used in this repo to compile a Bengali LaTeX document with LuaLaTeX and polyglossia on both Ubuntu Desktop and Ubuntu Server.

### 1) Prerequisites
- Ubuntu 22.04 or newer (works similarly on 20.04/24.04)
- Internet access for installing packages

### 2) Install TeX Live (LuaLaTeX) and required packages
You can install the full TeX Live distribution (large download) or a targeted set. The targeted set is usually enough for polyglossia + fontspec + geometry + enumitem + amsmath.

Minimal, recommended:
```bash
sudo apt update
sudo apt install -y \
  texlive-luatex \
  texlive-latex-recommended \
  texlive-latex-extra \
  texlive-fonts-recommended \
  biber
```

Alternative (bigger, simpler):
```bash
sudo apt update
sudo apt install -y texlive-full
```

Verify LuaLaTeX is available:
```bash
lualatex --version
```

### 3) Install Bengali fonts (Desktop and Server)
For Ubuntu, prefer freely available Noto fonts. Install packages that include Bengali support:
```bash
sudo apt install -y \
  fonts-noto-core \
  fonts-noto-extra \
  fonts-lohit-beng-bengali \
  fonts-beng-extra
```

Notes:
- Noto Sans Bengali is typically provided by the `fonts-noto-*` packages above. If not present on your release, you can manually install from Google Fonts.
- `fonts-lohit-beng-bengali` and `fonts-beng-extra` provide alternative Bengali fonts (e.g., Lohit, Mukti Narrow).

Rebuild the LuaTeX font cache (good practice after installing fonts):
```bash
luaotfload-tool -u
```

### 4) Configure your LaTeX document
If you’re on Ubuntu, use a font that exists on Linux, such as “Noto Sans Bengali”. For example:
```tex
\usepackage{polyglossia}
\setmainlanguage{bengali}
\newfontfamily\bengalifont[Script=Bengali]{Noto Sans Bengali}
```

If you copied the sample from Windows that used `Nirmala UI`, replace that line with `Noto Sans Bengali` as shown above.

### 5) Compile (Desktop and Server)
Run LuaLaTeX (headless-friendly):
```bash
lualatex -interaction=nonstopmode -halt-on-error test.tex
```

If you changed fonts or installed new fonts and LuaLaTeX can’t find them, run:
```bash
luaotfload-tool -u
```
and compile again.

## Build multi-cell MCQ sheets from many inputs

This repo includes a small builder that takes many LaTeX snippets (each snippet is just the body text/math), compiles each to a cropped PDF (only the written part), and then lays them out as:
- Desktop: two columns, 20 rows per column (40 cells) → `out/sheet_2col.pdf`
- Mobile: one column, 40 rows (40 cells) → `out/sheet_1col.pdf`

### Directory layout
```
inputs/
  snippets/
    example1.tex
    example2.tex
templates/
  snippet_template.tex
builder/
  build_sheet.py
out/
  ... generated files here ...
```

### Add your inputs
Put each question/snippet as a `.tex` file under `inputs/snippets/`.

Example (`inputs/snippets/example1.tex`):
```tex
% Bengali + math example snippet
বাংলা উদাহরণ প্রশ্ন: নিচের কোনটি $3 \times 2$ ক্রমের ম্যাট্রিক্স?

$\begin{pmatrix} x & y & z \\ 1 & 2 & 3 \end{pmatrix}$
```

Example (`inputs/snippets/example2.tex`):
```tex
% Bengali + MCQ style snippet
প্রশ্ন: নিচের কোনটি ইউনিট ম্যাট্রিক্স?

ক) $\begin{pmatrix}1 & 0 \\ 0 & 1\end{pmatrix}$
খ) $\begin{pmatrix}0 & 1 \\ 1 & 0\end{pmatrix}$
গ) $\begin{pmatrix}2 & 0 \\ 0 & 2\end{pmatrix}$
ঘ) $\begin{pmatrix}1 & 2 \\ 3 & 4\end{pmatrix}$
```

### Build requirements
Ensure these tools are installed (see sections above for Ubuntu install commands):
- `lualatex` (from TeX Live)
- `pdfcrop` (part of TeX Live; included in `texlive-latex-extra` or `texlive-full`)

Rebuild font cache after adding fonts:
```bash
luaotfload-tool -u
```

### Generate the sheets
```bash
python3 builder/build_sheet.py
```

Outputs:
- `out/sheet_2col.pdf` → Two columns × 20 rows (desktop sheet)
- `out/sheet_1col.pdf` → One column × 40 rows (mobile sheet)

You can also pass specific snippet files:
```bash
python3 builder/build_sheet.py --inputs inputs/snippets/example1.tex inputs/snippets/example2.tex
```

Notes:
- The builder compiles each snippet using the template at `templates/snippet_template.tex`, then crops with `pdfcrop` to show only written content.
- The final sheets place each cropped snippet PDF into a table cell, producing an MCQ-like layout.

### 6) Troubleshooting
- Font not found (fontspec error):
  - Confirm the font is installed: `fc-list | grep -i bengali` or `fc-list | grep -i "Noto Sans Bengali"`
  - Rebuild cache: `luaotfload-tool -u`
  - Ensure the font name matches exactly, e.g., `Noto Sans Bengali`

- Missing characters (squares/empty boxes):
  - Use a font that covers Bengali fully (e.g., `Noto Sans Bengali`, `Lohit Bengali`, `Mukti Narrow`).

- Package missing errors:
  - Install `texlive-latex-extra` to get many commonly used packages.
  - If still missing and you didn’t install `texlive-full`, add the specific package or consider `texlive-full`.

### 7) Example minimal preamble (Ubuntu-ready)
```tex
\documentclass[12pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{polyglossia}
\usepackage{geometry}
\usepackage{enumitem}
\geometry{a4paper, margin=1in}

\setmainlanguage{bengali}
\newfontfamily\bengalifont[Script=Bengali]{Noto Sans Bengali}

\setlength{\parindent}{0pt}
\setlength{\parskip}{0.3em}

\newlist{benglienum}{enumerate}{1}
\setlist[benglienum]{label=(\alph*), leftmargin=2em}

\begin{document}
বাংলা লেখা পরীক্ষা
\end{document}
```

### 8) Ubuntu Desktop vs Ubuntu Server
- Desktop:
  - You may preview PDFs using your PDF viewer.
  - Font installation via Software Center also works; this guide uses APT for reproducibility.

- Server (headless):
  - Use the same APT commands to install TeX Live and fonts.
  - Compile with `lualatex -interaction=nonstopmode -halt-on-error file.tex`.
  - Copy PDFs off the server via SCP/SFTP when needed.

### 9) Optional: Using XeLaTeX instead
If you prefer XeLaTeX, install `texlive-xetex` and compile with `xelatex`. The same polyglossia + fontspec configuration applies.

### 10) Verifying font availability
Useful commands:
```bash
fc-list | grep -i bengali
fc-list | grep -i "Noto Sans Bengali"
luaotfload-tool --find="Noto Sans Bengali" || true
```

If `luaotfload-tool --find` cannot locate the font, rebuild the cache (`luaotfload-tool -u`) and try again.

## Web app: input and output webpages

Run a simple Flask app that lets you:
- Select the number of inputs
- Enter LaTeX body for each snippet
- Compile each snippet (server-side) and crop to written area
- Display results in an output page grid with PDF viewers
  - Desktop: two columns (up to 20 rows per column)
  - Mobile: one column (up to 40 rows)

### Install web dependencies
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install flask
```

Ensure TeX tools exist on the machine (see TeX Live instructions above) and `pdfcrop` is available. Rebuild font cache if needed:
```bash
luaotfload-tool -u
```

### Run the app
```bash
FLASK_APP=web/app.py flask run --host 0.0.0.0 --port 5000
```
Or simply:
```bash
python3 web/app.py
```

Open `http://localhost:5000/` in your browser.

Notes:
- The server compiles snippets using the `templates/snippet_template.tex` (Bengali + polyglossia) and crops each PDF via `pdfcrop`.
- Generated PDFs are stored under `web/generated/<session>/pdfs/` and displayed in the output grid; each cell holds a PDF viewer.
- Limit of 40 inputs per session (fills 40 cells max).
- Security: This is a local tool. Running arbitrary LaTeX can be unsafe. Use in a trusted environment.


