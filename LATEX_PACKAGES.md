# LaTeX Packages and Capabilities

This document describes the LaTeX packages included in the Docker image and what they enable.

## 📦 Included TeX Live Packages

### Core LaTeX
- **texlive-latex-base** - Essential LaTeX system
- **texlive-latex-recommended** - Recommended packages for most documents
- **texlive-latex-extra** (~450MB) - Extensive collection of LaTeX packages
  - Enables: advanced formatting, specialized environments, custom layouts
  - Includes: `geometry`, `hyperref`, `graphicx`, `xcolor`, `fancyhdr`, `enumitem`, `multicol`, `listings`, and 100+ more

### Math & Science
- **texlive-science** - Mathematical and scientific packages
  - Enables: advanced math typesetting, chemical formulas, algorithms
  - Includes: `amsmath`, `amssymb`, `amsthm`, `chemfig`, `siunitx`, `algorithm2e`

### Fonts
- **texlive-fonts-recommended** - High-quality fonts
- **fonts-liberation** - Liberation fonts (Arial/Times alternative)
- **fonts-beng** - Bengali/Bangla fonts (required for this application)
- **fonts-noto** - Google Noto fonts (universal coverage)
  - Note: `texlive-fonts-extra` NOT included (1.7GB, too large for 4GB limit)

### Engines
- **texlive-luatex** - LuaLaTeX engine (used by this application)
  - Enables: Unicode support, modern font handling, Lua scripting
  - Better font rendering than pdflatex
- **texlive-xetex** - XeLaTeX engine
  - Alternative modern engine with excellent font support
  - Can compile with `xelatex` instead of `lualatex` if needed

### Graphics & Diagrams
- **texlive-pictures** (~150MB) - Graphics and diagram packages
  - **TikZ/PGF** - Powerful vector graphics
  - **pgfplots** - Publication-quality plots
  - Enables: flowcharts, diagrams, graphs, technical drawings

### Bibliography
- **texlive-bibtex-extra** - Enhanced bibliography support
  - BibTeX and BibLaTeX support
  - Multiple citation styles

### Utilities
- **ghostscript** - PostScript/PDF processing
- **poppler-utils** - PDF utilities (pdfinfo, pdftoppm, etc.)

## 🎯 What You Can Do

### ✅ Supported Features

1. **Advanced Math**
   ```latex
   \usepackage{amsmath}
   \begin{equation}
     E = mc^2
   \end{equation}
   ```

2. **TikZ Diagrams**
   ```latex
   \usepackage{tikz}
   \begin{tikzpicture}
     \draw (0,0) circle (1cm);
   \end{tikzpicture}
   ```

3. **Code Listings**
   ```latex
   \usepackage{listings}
   \begin{lstlisting}[language=Python]
   def hello():
       print("Hello, World!")
   \end{lstlisting}
   ```

4. **Tables & Figures**
   ```latex
   \usepackage{booktabs}
   \usepackage{graphicx}
   ```

5. **Custom Page Layout**
   ```latex
   \usepackage{geometry}
   \geometry{margin=1in}
   ```

6. **Hyperlinks**
   ```latex
   \usepackage{hyperref}
   ```

7. **Bengali/Unicode Text**
   ```latex
   \usepackage{fontspec}
   \usepackage{polyglossia}
   \setmainlanguage{bengali}
   ```

### ❌ Limitations

1. **Fonts**: Limited font selection (fonts-extra package excluded due to size)
   - Solution: Use web fonts or include specific fonts only

2. **Publishers**: No publisher-specific templates (texlive-publishers excluded)
   - Solution: Install individual publisher classes if needed

3. **Languages**: Limited language support beyond Bengali
   - Solution: Add specific language packages if needed

## 📊 Image Size Breakdown

Estimated Docker image size: **~2.5-3GB** (well under 4GB Railway limit)

- Python 3.11-slim base: ~200MB
- TeX Live packages: ~1.5-2GB (after aggressive cleanup)
- Application code: ~50MB
- Python dependencies: ~200MB

### Size Optimizations Applied

1. **Removed documentation** - Saves ~200-300MB
   - `/usr/share/texlive/texmf-dist/doc/*`
   - `/usr/share/texmf/doc/*`

2. **Removed source files** - Saves ~100-150MB
   - `/usr/share/texlive/texmf-dist/source/*`

3. **Removed man pages and locale** - Saves ~50-100MB
   - `/usr/share/man/*`
   - `/usr/share/locale/*`

4. **Cleaned package caches** - Saves ~50MB
   - `/var/lib/apt/lists/*`
   - `/var/cache/apt/*`

## 🔧 Adding More Packages

If you need additional LaTeX packages not included:

### Option 1: Add Debian Package (recommended for major additions)
Edit `Dockerfile` and add to the `apt-get install` line:
```dockerfile
texlive-your-package-name \
```

### Option 2: Use tlmgr (for individual packages)
Add to Dockerfile after the TeX Live installation:
```dockerfile
RUN tlmgr init-usertree && \
    tlmgr install package-name
```

### Option 3: Include .sty files directly
Place custom `.sty` files in the project and use:
```latex
\usepackage{custom-package}
```

## 🚀 Comparison with Overleaf

This setup provides **~80-90% of Overleaf's capabilities** while staying under 4GB:

| Feature | Overleaf | This Image | Notes |
|---------|----------|------------|-------|
| Core LaTeX | ✅ | ✅ | Full support |
| Math packages | ✅ | ✅ | All essential packages |
| TikZ/Graphics | ✅ | ✅ | Full support |
| LuaLaTeX | ✅ | ✅ | Primary engine |
| XeLaTeX | ✅ | ✅ | Available |
| Font library | ✅ | ⚠️ | Limited (no fonts-extra) |
| Publisher templates | ✅ | ❌ | Can add individually |
| Language support | ✅ | ⚠️ | Bengali + basic |
| Bibliography | ✅ | ✅ | Full support |

## 📝 Testing Your LaTeX

To test if a package is available:

```bash
# Check if package exists
kpsewhich package-name.sty

# List all installed packages
tlmgr list --only-installed

# Search for a package
apt-cache search texlive | grep your-term
```

## 🎓 Recommended Usage

For best results:

1. **Use LuaLaTeX** (already configured)
   - Better Unicode support
   - Modern font handling
   - Lua scripting capabilities

2. **Test locally first** if using exotic packages
   - Check if package is in the list above
   - Add to Dockerfile if needed

3. **Keep packages minimal** in your documents
   - Only include what you need
   - Faster compilation
   - Better compatibility

## 📚 Resources

- [TeX Live Package Documentation](https://www.tug.org/texlive/)
- [CTAN - Comprehensive TeX Archive](https://ctan.org/)
- [LaTeX Package Documentation](https://www.latex-project.org/)
- [Overleaf Learn](https://www.overleaf.com/learn)
