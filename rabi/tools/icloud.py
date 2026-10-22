"""icloud_stuck_projects: find code projects whose files iCloud has offloaded.

Why this exists: with "Desktop & Documents" in iCloud and "Optimize Mac Storage"
on, macOS can evict file contents and leave "dataless" placeholders. Opening one
blocks until it downloads. A venv full of placeholders made `import torch` take
24 minutes. Code belongs outside iCloud, e.g. in ~/dev.
"""

import os
from pathlib import Path

# From <sys/stat.h>: file has no local data; contents live in the cloud.
SF_DATALESS = 0x40000000

PROJECT_MARKERS = (".git", "pyproject.toml", "requirements.txt", "package.json")
# Big dependency folders: don't descend into them while looking for projects.
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "Library"}


def is_dataless(path: str) -> bool:
    """True if the file is an iCloud placeholder.

    lstat only reads metadata, so checking never triggers a download.
    st_flags only exists on BSD/macOS; elsewhere we report False.
    """
    try:
        return bool(getattr(os.lstat(path), "st_flags", 0) & SF_DATALESS)
    except OSError:
        return False


def find_projects(root: Path, max_depth: int = 3) -> list[Path]:
    """Folders under root containing a project marker, not nested in another project."""
    found: list[Path] = []
    if not root.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        entries = set(dirnames) | set(filenames)
        if any(m in entries for m in PROJECT_MARKERS):
            found.append(Path(dirpath))
            dirnames.clear()  # a project's subfolders are part of that project
            continue
        if depth >= max_depth:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
    return found


def sample_files(project: Path, limit: int = 200) -> list[str]:
    """Up to `limit` file paths, including inside venvs (that's where offloading hurts)."""
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for f in filenames:
            files.append(os.path.join(dirpath, f))
            if len(files) >= limit:
                return files
    return files


def icloud_stuck_projects(roots: list[str] | None = None, sample_size: int = 200) -> dict:
    """Scan ~/Desktop and ~/Documents for code projects with files offloaded to iCloud."""
    home = Path.home()
    scan = [Path(r).expanduser() for r in roots] if roots else [home / "Desktop", home / "Documents"]
    projects = []
    for root in scan:
        for proj in find_projects(root):
            files = sample_files(proj, sample_size)
            offloaded = sum(is_dataless(f) for f in files)
            pct = round(100 * offloaded / len(files), 1) if files else 0.0
            projects.append({
                "project": str(proj).replace(str(home), "~", 1),
                "files_sampled": len(files),
                "files_offloaded": offloaded,
                "percent_offloaded": pct,
            })
    projects.sort(key=lambda p: p["percent_offloaded"], reverse=True)
    stuck = [p for p in projects if p["files_offloaded"] > 0]
    return {
        "roots_scanned": [str(r).replace(str(home), "~", 1) for r in scan],
        "projects_found": len(projects),
        "projects_with_offloaded_files": len(stuck),
        "projects": projects[:15],
        "recommendation": (
            "Move these projects to ~/dev (outside iCloud) and recreate their virtual environments."
            if stuck else "No offloaded project files found. Keeping code in ~/dev avoids this problem."
        ),
    }
