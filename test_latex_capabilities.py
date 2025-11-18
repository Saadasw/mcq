#!/usr/bin/env python3
"""
Test script for comprehensive LaTeX capabilities
Tests various LaTeX features to ensure Overleaf-like functionality
"""

from pathlib import Path
import tempfile
import sys

# Add web directory to path
sys.path.insert(0, str(Path(__file__).parent / "web"))

from utils.robust_latex_compiler import compile_latex_robust, RobustLaTeXCompiler


# Test cases representing different LaTeX features
TEST_CASES = [
    {
        'name': 'Basic Math',
        'description': 'Simple mathematical equations',
        'latex': r'''
\documentclass{article}
\usepackage{amsmath}
\begin{document}
\section{Mathematics}
The quadratic formula is:
\begin{equation}
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
\end{equation}

Inline math: $E = mc^2$
\end{document}
'''
    },
    {
        'name': 'Bengali Text',
        'description': 'Bengali text with Polyglossia',
        'latex': r'''
\documentclass{article}
\usepackage{polyglossia}
\usepackage{fontspec}
\setdefaultlanguage{bengali}
\setmainfont{Noto Serif Bengali}
\begin{document}
\section{বাংলা পরীক্ষা}
এটি একটি বাংলা নথি। গণিত: $x^2 + y^2 = z^2$
\end{document}
'''
    },
    {
        'name': 'Advanced Math',
        'description': 'Complex mathematical expressions',
        'latex': r'''
\documentclass{article}
\usepackage{amsmath,amssymb}
\begin{document}
\[
\int_0^\infty e^{-x^2} \, dx = \frac{\sqrt{\pi}}{2}
\]

\[
\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}
\]

\[
\lim_{x \to 0} \frac{\sin x}{x} = 1
\]
\end{document}
'''
    },
    {
        'name': 'Graphics',
        'description': 'Including graphics packages',
        'latex': r'''
\documentclass{article}
\usepackage{graphicx}
\usepackage{xcolor}
\begin{document}
\section{Graphics}
{\color{red}Red text} and {\color{blue}blue text}.

\textbf{Bold} and \textit{italic} formatting.
\end{document}
'''
    },
    {
        'name': 'Tables',
        'description': 'Professional tables with booktabs',
        'latex': r'''
\documentclass{article}
\usepackage{booktabs}
\begin{document}
\section{Tables}
\begin{table}[h]
\centering
\begin{tabular}{lcc}
\toprule
Name & Value & Unit \\
\midrule
Speed & 100 & m/s \\
Distance & 50 & km \\
Time & 0.5 & hour \\
\bottomrule
\end{tabular}
\caption{Sample Data}
\end{table}
\end{document}
'''
    },
    {
        'name': 'Multiple Languages',
        'description': 'English and Bengali mixed',
        'latex': r'''
\documentclass{article}
\usepackage{polyglossia}
\usepackage{fontspec}
\setdefaultlanguage{english}
\setotherlanguage{bengali}
\newfontfamily\bengalifont[Script=Bengali]{Noto Serif Bengali}
\begin{document}
\section{English Section}
This is English text with math: $a^2 + b^2 = c^2$

\begin{bengali}
\section{বাংলা অংশ}
এটি বাংলা লেখা।
\end{bengali}
\end{document}
'''
    },
    {
        'name': 'Lists and Formatting',
        'description': 'Various formatting features',
        'latex': r'''
\documentclass{article}
\begin{document}
\section{Lists}
\begin{enumerate}
\item First item
\item Second item
  \begin{itemize}
  \item Sub-item A
  \item Sub-item B
  \end{itemize}
\item Third item
\end{enumerate}

\subsection{Formatting}
\textbf{Bold}, \textit{italic}, \underline{underlined}, and \texttt{monospace}.
\end{document}
'''
    },
]


def test_latex_capability(test_case: dict, output_dir: Path) -> bool:
    """
    Test a specific LaTeX capability
    Returns True if compilation succeeds
    """
    print(f"\n{'='*60}")
    print(f"Test: {test_case['name']}")
    print(f"Description: {test_case['description']}")
    print(f"{'='*60}")

    result = compile_latex_robust(
        test_case['latex'],
        output_dir,
        filename=test_case['name'].replace(' ', '_').lower(),
        validate=True
    )

    if result.success:
        print(f"✓ SUCCESS - PDF created: {result.pdf_path.name}")
        print(f"  Compilation time: {result.compilation_time:.2f}s")
        if result.warnings:
            print(f"  Warnings ({len(result.warnings)}):")
            for warning in result.warnings[:3]:
                print(f"    - {warning[:80]}")
        return True
    else:
        print(f"✗ FAILED - {result.error_message}")
        if result.log_content:
            # Print last few lines of log
            log_lines = result.log_content.split('\n')
            print(f"  Last log lines:")
            for line in log_lines[-5:]:
                if line.strip():
                    print(f"    {line[:100]}")
        return False


def test_package_detection():
    """Test missing package detection"""
    print(f"\n{'='*60}")
    print("Test: Package Detection")
    print(f"{'='*60}")

    sample_log = """
! LaTeX Error: File `nonexistent.sty' not found.
! LaTeX Error: File `missing.cls' not found.
Package foobar Error: Something went wrong
"""

    packages = RobustLaTeXCompiler.detect_missing_packages(sample_log)
    if packages:
        print(f"✓ Detected missing packages: {', '.join(packages)}")
        return True
    else:
        print("✗ Failed to detect missing packages")
        return False


def test_latex_enhancement():
    """Test automatic package enhancement"""
    print(f"\n{'='*60}")
    print("Test: LaTeX Enhancement")
    print(f"{'='*60}")

    sample_latex = r"""
\documentclass{article}
\begin{document}
Test document
\end{document}
"""

    enhanced = RobustLaTeXCompiler.enhance_latex_content(sample_latex, add_packages=True)

    if 'amsmath' in enhanced and 'graphicx' in enhanced:
        print("✓ Successfully added recommended packages")
        print(f"  Added packages: amsmath, amssymb, graphicx, etc.")
        return True
    else:
        print("✗ Failed to enhance LaTeX content")
        return False


def main():
    """Run all LaTeX capability tests"""
    print("\n" + "="*60)
    print("LaTeX Capability Test Suite")
    print("Testing Overleaf-like LaTeX compilation")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        results = []

        # Test package detection
        results.append(('Package Detection', test_package_detection()))

        # Test LaTeX enhancement
        results.append(('LaTeX Enhancement', test_latex_enhancement()))

        # Test all LaTeX features
        for test_case in TEST_CASES:
            success = test_latex_capability(test_case, output_dir)
            results.append((test_case['name'], success))

        # Summary
        print(f"\n{'='*60}")
        print("Test Summary")
        print(f"{'='*60}")

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for name, success in results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status:10} - {name}")

        print(f"\n{passed}/{total} tests passed ({100*passed//total}%)")

        if passed == total:
            print("\n🎉 All tests passed! LaTeX compiler is fully functional.")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Check the output above.")
            return 1


if __name__ == "__main__":
    sys.exit(main())
