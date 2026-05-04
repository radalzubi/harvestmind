"""Tripwire test: scan tracked files for obvious credentials / tokens.

This is a coarse first line of defence — `pip-audit` and a real secret
scanner like `gitleaks` should still run in CI. The intent is that any PR
that accidentally commits an API key or service-account JSON fails this
test before review.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Patterns that should NEVER appear in tracked text files.
PATTERNS = [
    # Common API key shapes
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),                    # OpenAI / Stripe-style
    re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),             # Slack tokens
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),                     # GitHub PAT
    re.compile(r"AKIA[0-9A-Z]{16}"),                          # AWS access key id
    re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA|PRIVATE) KEY-----"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),                    # Google API key
    re.compile(r"[A-Za-z0-9_]{0,32}eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}"),  # JWT-ish
]

# Files we expect to *contain* the patterns above as documentation strings
# or test fixtures. None today; left empty as a forwards-compat hook.
ALLOWLIST_FILES: set[str] = set()

# Extensions to scan. Binary-heavy extensions are skipped.
TEXT_EXTS = {
    ".py", ".toml", ".yaml", ".yml", ".json", ".md", ".sql",
    ".html", ".js", ".ts", ".env",  # .env never tracked, but check anyway
    "",  # files like Makefile / Dockerfile
}


def _tracked_files() -> list[Path]:
    """Return git-tracked files, suitable for scanning."""
    try:
        out = subprocess.check_output(
            ["git", "ls-files"], cwd=ROOT, text=True, timeout=10
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("git not available")
    paths = []
    for line in out.strip().splitlines():
        p = ROOT / line
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in TEXT_EXTS:
            continue
        paths.append(p)
    return paths


def test_no_obvious_secrets_in_tracked_files():
    bad: list[tuple[Path, int, str, str]] = []
    for p in _tracked_files():
        rel = p.relative_to(ROOT).as_posix()
        if rel in ALLOWLIST_FILES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for pat in PATTERNS:
                m = pat.search(line)
                if m:
                    # Ignore obvious placeholders inside .env.example etc.
                    redacted = m.group(0)[:6] + "…"
                    bad.append((p.relative_to(ROOT), i, pat.pattern, redacted))
    if bad:
        msg = "\n".join(
            f"  {p}:{ln}  pattern={pat}  match={hit}"
            for p, ln, pat, hit in bad
        )
        pytest.fail("Secrets-like strings found in tracked files:\n" + msg)


def test_env_file_not_tracked():
    """The real .env must never be tracked."""
    out = subprocess.check_output(
        ["git", "ls-files", "--error-unmatch", ".env"],
        cwd=ROOT, text=True, stderr=subprocess.STDOUT,
    ).strip() if False else ""
    # The above one-liner branch is intentionally unreachable; we use a
    # subprocess invocation that returns non-zero when the file isn't
    # tracked, and translate that to "good".
    try:
        subprocess.check_output(
            ["git", "ls-files", "--error-unmatch", ".env"],
            cwd=ROOT, stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError:
        return  # not tracked → pass
    pytest.fail(".env is git-tracked — it must be in .gitignore and untracked")


def test_gitignore_covers_env_files():
    gi = (ROOT / ".gitignore").read_text()
    assert ".env" in gi, ".gitignore must list .env"
    assert "!.env.example" in gi, ".env.example must remain trackable"
