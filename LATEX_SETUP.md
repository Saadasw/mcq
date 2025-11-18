# Comprehensive LaTeX Setup for MCQ Application

This document describes the LaTeX compilation capabilities of this MCQ application, which now matches Overleaf's robustness and features.

## Overview

The application now includes a **comprehensive LaTeX installation** with support for:
- Multiple LaTeX engines (LuaLaTeX, XeLaTeX, PDFLaTeX)
- Extensive package collections (math, science, languages, graphics)
- Bengali and multilingual text support
- Advanced graphics (TikZ, PGF plots)
- Bibliography and citations
- Professional publishing formats

## Installed LaTeX Components

### Core Engines
- **LuaLaTeX**: Modern engine with Lua scripting support
- **XeLaTeX**: Advanced Unicode and font handling
- **PDFLaTeX**: Traditional, widely compatible engine

### Package Collections

#### Math and Science
- `texlive-science`: Scientific packages (physics, chemistry, etc.)
- `texlive-mathscience`: Advanced mathematical typesetting
- `amsmath`, `amssymb`, `amsfonts`: AMS math packages
- `mathtools`: Extensions to amsmath

#### Fonts
- Noto fonts (comprehensive Unicode coverage)
- Bengali fonts (fonts-beng, fonts-beng-extra)
- CJK fonts (Chinese, Japanese, Korean)
- Liberation, DejaVu, FreeFont families
- Full TeXLive font collections

#### Languages
- Bengali, Arabic, Chinese, Cyrillic
- European languages (French, German, Italian, Spanish)
- Greek, Japanese, Korean
- Polyglossia for multilingual documents

#### Graphics and Diagrams
- TikZ/PGFplots for diagrams
- PSTricks for PostScript graphics
- GraphicX for image inclusion
- Color support (xcolor)

#### Bibliography
- BibTeX with extra styles
- Biber for advanced bibliographies
- Natbib for natural sciences citations

#### Publishing
- Templates for major publishers
- Professional table formatting (booktabs)
- Advanced caption control
- Hyperref for PDF links

#### Utilities
- Ghostscript (PDF processing)
- ImageMagick (image conversion)
- pdf2svg (vector conversion)
- Poppler utilities (PDF manipulation)

## Compilation Strategies

The robust compiler automatically tries multiple strategies in order:

### 1. **LuaLaTeX Fast** (Default)
- Best for: Modern documents with Unicode
- Features: Shell-escape enabled (for TikZ, minted)
- Timeout: 40 seconds
- Passes: 2

### 2. **XeLaTeX Unicode**
- Best for: Complex font requirements, multilingual
- Features: Superior Unicode handling
- Timeout: 40 seconds
- Passes: 2

### 3. **LuaLaTeX Robust**
- Best for: Documents with potential errors
- Features: Continues compilation on errors
- Timeout: 60 seconds
- Passes: 3 (for references)

### 4. **XeLaTeX Robust**
- Best for: Complex Unicode documents with errors
- Features: Robust error handling
- Timeout: 60 seconds
- Passes: 3

### 5. **PDFLaTeX Modern**
- Best for: Traditional LaTeX documents
- Features: Wide package compatibility
- Timeout: 45 seconds
- Passes: 3

### 6. **PDFLaTeX Safe**
- Best for: Simple documents, maximum compatibility
- Features: No shell-escape (safest)
- Timeout: 30 seconds
- Passes: 2

## Features

### 1. Pre-Compilation Validation
- Syntax checking before compilation
- Detects unbalanced braces
- Validates math delimiters
- Identifies common errors early

### 2. Automatic Package Enhancement
- Auto-adds commonly needed packages
- Smart detection of missing packages
- Overleaf-like defaults (amsmath, graphicx, etc.)

### 3. Intelligent Error Handling
- Extracts meaningful error messages from logs
- Identifies missing packages
- Provides line numbers for errors
- Suggests fixes when possible

### 4. Multi-Pass Compilation
- Automatic multiple passes for references
- Handles bibliographies correctly
- Resolves cross-references

### 5. Timeout Protection
- Prevents infinite loops
- Graceful timeout handling
- Automatic fallback to next strategy

## Supported LaTeX Features

### Mathematics
```latex
\begin{equation}
  E = mc^2
\end{equation}

$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$
```

### Bengali Text
```latex
\documentclass{article}
\usepackage{polyglossia}
\setdefaultlanguage{bengali}
\begin{document}
এটি একটি বাংলা নথি।
\end{document}
```

### Graphics with TikZ
```latex
\usepackage{tikz}
\begin{tikzpicture}
  \draw (0,0) circle (1cm);
\end{tikzpicture}
```

### Tables
```latex
\usepackage{booktabs}
\begin{table}
  \begin{tabular}{lcc}
    \toprule
    Item & Value & Unit \\
    \midrule
    Speed & 100 & m/s \\
    \bottomrule
  \end{tabular}
\end{table}
```

### Chemistry
```latex
\usepackage{mhchem}
\ce{H2O}  % Water molecule
```

### Physics
```latex
\usepackage{physics}
\derivative{f}{x}  % Derivative notation
```

## Docker Configuration

The Dockerfile now includes comprehensive LaTeX support:

```dockerfile
# Install comprehensive TeX Live packages
RUN apt-get update && apt-get install -y \
    texlive-luatex \
    texlive-xetex \
    texlive-latex-extra \
    texlive-science \
    texlive-fonts-extra \
    texlive-lang-other \
    ... (and many more)
```

## Usage in Application

The robust compiler is automatically used when compiling LaTeX snippets:

```python
from utils.robust_latex_compiler import compile_latex_robust

result = compile_latex_robust(
    latex_content,
    output_dir,
    filename="snippet",
    validate=True  # Enable pre-validation
)

if result.success:
    print(f"PDF created: {result.pdf_path}")
    if result.warnings:
        print("Warnings:", result.warnings)
else:
    print(f"Error: {result.error_message}")
```

## Performance Considerations

### Image Size
The comprehensive LaTeX installation adds approximately **1.5-2 GB** to the Docker image. This is a reasonable trade-off for Overleaf-like capabilities.

### Compilation Time
- Simple documents: 2-5 seconds
- Complex documents with graphics: 10-30 seconds
- Maximum timeout: 60 seconds (with automatic fallback)

### Resource Usage
- Memory: ~200-500 MB during compilation
- CPU: 1 core (sequential compilation)
- Disk: Temporary files cleaned after compilation

## Troubleshooting

### Missing Package Errors
If you encounter missing package errors:
1. The compiler will automatically detect and report them
2. Check if the package is in texlive-full (not installed by default)
3. Consider adding the package to Dockerfile
4. Try different compilation strategies

### Compilation Timeouts
If documents timeout:
1. Simplify graphics (reduce TikZ complexity)
2. Remove unnecessary packages
3. Split large documents
4. Check for infinite loops in macros

### Font Issues
For Bengali/multilingual fonts:
1. Use LuaLaTeX or XeLaTeX (not PDFLaTeX)
2. Include `\usepackage{polyglossia}`
3. Ensure Noto fonts are used: `\setmainfont{Noto Serif Bengali}`

### Unicode Errors
If you see Unicode errors:
1. Use XeLaTeX or LuaLaTeX
2. Ensure UTF-8 encoding in source files
3. Avoid PDFLaTeX for non-ASCII characters

## Comparison with Overleaf

| Feature | This Application | Overleaf |
|---------|-----------------|----------|
| LaTeX Engines | LuaLaTeX, XeLaTeX, PDFLaTeX | Same |
| Package Coverage | ~90% (most common packages) | ~95% (texlive-full) |
| Compilation Strategies | 6 automatic fallbacks | Manual selection |
| Error Detection | Automatic + pre-validation | Manual |
| Timeout Handling | Automatic (30-60s) | None (cloud limits) |
| Bengali Support | Full (Noto fonts) | Full |
| TikZ/Graphics | Full | Full |
| Bibliography | BibTeX + Biber | Same |
| Real-time Collaboration | No | Yes |
| Version Control | Git-based | Built-in |

## Future Enhancements

Potential improvements:
1. Add texlive-full for 100% package coverage (trade-off: 4GB image)
2. Implement automatic package installation via tlmgr
3. Add caching for faster repeated compilations
4. Support for custom LaTeX packages upload
5. Real-time compilation preview
6. Collaborative editing features

## References

- [TeX Live Documentation](https://tug.org/texlive/)
- [LuaLaTeX Guide](http://www.luatex.org/)
- [XeLaTeX Guide](http://xelatex.net/)
- [Overleaf Documentation](https://www.overleaf.com/learn)
- [CTAN Package Archive](https://ctan.org/)

## License

The LaTeX installation uses open-source components:
- TeX Live: TeX Live License (free)
- Fonts: Various open-source licenses (SIL OFL, GPL)
- Packages: LPPL (LaTeX Project Public License)
