#!/usr/bin/env python3
"""
Robust LaTeX Compiler - Similar to Overleaf's reliability

Features:
- Pre-compilation validation
- Multiple compilation strategies
- Detailed error messages
- Timeout management
- Resource limits
- Fallback mechanisms
- Better user feedback
"""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import signal
from contextlib import contextmanager


@dataclass
class CompilationResult:
    """Result of a LaTeX compilation"""
    success: bool
    pdf_path: Optional[Path] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    log_content: Optional[str] = None
    compilation_time: float = 0.0

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class LaTeXValidator:
    """Validates LaTeX syntax before compilation"""

    # Common LaTeX errors to catch early
    # Note: Complex environment matching is done separately
    VALIDATION_RULES = [
        (r'\${3,}', 'Too many $ signs (use \\[ \\] or \\begin{{equation}})'),
        (r'\\textbf\{[^}]*\\textbf', 'Nested \\textbf commands'),
    ]

    # Required packages for Bengali/Polyglossia
    REQUIRED_PACKAGES = ['polyglossia', 'fontspec']

    @classmethod
    def validate_syntax(cls, latex_content: str) -> Tuple[bool, List[str]]:
        """
        Validate LaTeX syntax before compilation
        Returns: (is_valid, list_of_errors)
        """
        errors = []

        # Check for basic syntax errors
        for pattern, error_template in cls.VALIDATION_RULES:
            matches = re.finditer(pattern, latex_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    error_msg = error_template.format(match=match.group(0)[:50])
                except:
                    error_msg = error_template
                errors.append(error_msg)

        # Check for balanced braces
        brace_count = latex_content.count('{') - latex_content.count('}')
        if brace_count != 0:
            errors.append(f"Unbalanced braces: {abs(brace_count)} {'extra {' if brace_count > 0 else 'extra }'}")

        # Check for balanced math delimiters
        dollar_count = latex_content.count('$')
        if dollar_count % 2 != 0:
            errors.append("Unbalanced math delimiters ($)")

        return (len(errors) == 0, errors)

    @classmethod
    def validate_packages(cls, latex_content: str) -> Tuple[bool, List[str]]:
        """Check if required packages are present"""
        warnings = []

        for package in cls.REQUIRED_PACKAGES:
            if f'\\usepackage{{{package}}}' not in latex_content:
                warnings.append(f"Missing recommended package: {package}")

        return (True, warnings)  # Don't fail, just warn


class TimeoutError(Exception):
    """Raised when compilation exceeds timeout"""
    pass


@contextmanager
def timeout(seconds: int):
    """Context manager for timeout"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class RobustLaTeXCompiler:
    """
    Production-grade LaTeX compiler with Overleaf-like robustness
    """

    # Compilation strategies (in order of preference)
    STRATEGIES = [
        {
            'name': 'lualatex_fast',
            'command': 'lualatex',
            'args': ['-interaction=nonstopmode', '-halt-on-error'],
            'passes': 2,
            'timeout': 30,
        },
        {
            'name': 'lualatex_robust',
            'command': 'lualatex',
            'args': ['-interaction=nonstopmode'],  # No halt-on-error
            'passes': 2,
            'timeout': 45,
        },
        {
            'name': 'pdflatex_fallback',
            'command': 'pdflatex',
            'args': ['-interaction=nonstopmode'],
            'passes': 2,
            'timeout': 30,
        },
    ]

    def __init__(self, validate_before_compile: bool = True):
        self.validate_before_compile = validate_before_compile

    def compile(
        self,
        latex_content: str,
        output_dir: Path,
        filename: str = "output",
        strategy_name: Optional[str] = None
    ) -> CompilationResult:
        """
        Compile LaTeX content to PDF

        Args:
            latex_content: The LaTeX source code
            output_dir: Directory to save PDF
            filename: Base filename (without extension)
            strategy_name: Specific strategy to use (or None for auto)

        Returns:
            CompilationResult with success status and details
        """
        import time
        start_time = time.time()

        # Pre-compilation validation
        if self.validate_before_compile:
            is_valid, errors = LaTeXValidator.validate_syntax(latex_content)
            if not is_valid:
                return CompilationResult(
                    success=False,
                    error_message="LaTeX validation failed:\n" + "\n".join(f"  • {e}" for e in errors),
                    compilation_time=time.time() - start_time
                )

            # Check packages (warnings only)
            _, warnings = LaTeXValidator.validate_packages(latex_content)
        else:
            warnings = []

        # Try compilation strategies
        strategies = self.STRATEGIES if not strategy_name else [
            s for s in self.STRATEGIES if s['name'] == strategy_name
        ]

        for strategy in strategies:
            result = self._try_strategy(latex_content, output_dir, filename, strategy)
            if result.success:
                result.warnings.extend(warnings)
                result.compilation_time = time.time() - start_time
                return result

        # All strategies failed
        return CompilationResult(
            success=False,
            error_message="All compilation strategies failed. Please check your LaTeX syntax.",
            compilation_time=time.time() - start_time
        )

    def _try_strategy(
        self,
        latex_content: str,
        output_dir: Path,
        filename: str,
        strategy: Dict
    ) -> CompilationResult:
        """Try a specific compilation strategy"""
        try:
            with tempfile.TemporaryDirectory() as td:
                temp_dir = Path(td)
                tex_file = temp_dir / f"{filename}.tex"

                # Write LaTeX file
                tex_file.write_text(latex_content, encoding='utf-8')

                # Compile with timeout
                log_content = ""
                for pass_num in range(strategy['passes']):
                    try:
                        with timeout(strategy['timeout']):
                            cmd = [
                                strategy['command'],
                                *strategy['args'],
                                f"{filename}.tex"
                            ]

                            result = subprocess.run(
                                cmd,
                                cwd=temp_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                timeout=strategy['timeout']
                            )

                            log_content += result.stdout

                            # Check if PDF was created
                            pdf_file = temp_dir / f"{filename}.pdf"
                            if not pdf_file.exists():
                                # Compilation failed, extract error
                                error_msg = self._extract_error_from_log(log_content)
                                return CompilationResult(
                                    success=False,
                                    error_message=f"Strategy '{strategy['name']}' failed: {error_msg}",
                                    log_content=log_content
                                )

                    except subprocess.TimeoutExpired:
                        return CompilationResult(
                            success=False,
                            error_message=f"Compilation timed out after {strategy['timeout']}s (possible infinite loop)",
                            log_content=log_content
                        )
                    except TimeoutError as e:
                        return CompilationResult(
                            success=False,
                            error_message=str(e),
                            log_content=log_content
                        )

                # Success! Copy PDF to output directory
                pdf_file = temp_dir / f"{filename}.pdf"
                if pdf_file.exists():
                    output_pdf = output_dir / f"{filename}.pdf"
                    import shutil
                    shutil.copy2(pdf_file, output_pdf)

                    # Extract warnings from log
                    warnings = self._extract_warnings_from_log(log_content)

                    return CompilationResult(
                        success=True,
                        pdf_path=output_pdf,
                        warnings=warnings,
                        log_content=log_content
                    )
                else:
                    return CompilationResult(
                        success=False,
                        error_message="PDF not generated (unknown error)",
                        log_content=log_content
                    )

        except Exception as e:
            return CompilationResult(
                success=False,
                error_message=f"Unexpected error in strategy '{strategy['name']}': {str(e)}"
            )

    def _extract_error_from_log(self, log_content: str) -> str:
        """Extract meaningful error message from LaTeX log"""
        # Look for common error patterns
        error_patterns = [
            r'! (.+)',  # Standard LaTeX error
            r'ERROR: (.+)',
            r'Fatal error: (.+)',
            r'Runaway argument\?(.+)',
        ]

        for pattern in error_patterns:
            match = re.search(pattern, log_content, re.MULTILINE)
            if match:
                return match.group(1).strip()[:200]  # Limit length

        # Look for "l.XXX" line numbers
        line_match = re.search(r'l\.(\d+)\s+(.+)', log_content)
        if line_match:
            return f"Error at line {line_match.group(1)}: {line_match.group(2)[:100]}"

        return "Unknown compilation error (check log for details)"

    def _extract_warnings_from_log(self, log_content: str) -> List[str]:
        """Extract warnings from LaTeX log"""
        warnings = []

        # Common warning patterns
        warning_patterns = [
            r'Warning: (.+)',
            r'LaTeX Warning: (.+)',
            r'Package \w+ Warning: (.+)',
        ]

        for pattern in warning_patterns:
            matches = re.finditer(pattern, log_content, re.MULTILINE)
            for match in matches:
                warning = match.group(1).strip()[:150]
                if warning not in warnings:  # Avoid duplicates
                    warnings.append(warning)

        return warnings[:10]  # Limit to 10 warnings


# Convenience function for easy usage
def compile_latex_robust(
    latex_content: str,
    output_dir: Path,
    filename: str = "output",
    validate: bool = True
) -> CompilationResult:
    """
    Compile LaTeX with robust error handling

    Example:
        result = compile_latex_robust(my_latex, Path("/output"))
        if result.success:
            print(f"PDF created: {result.pdf_path}")
        else:
            print(f"Error: {result.error_message}")
    """
    compiler = RobustLaTeXCompiler(validate_before_compile=validate)
    return compiler.compile(latex_content, output_dir, filename)
