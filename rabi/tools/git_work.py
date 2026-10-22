"""unpushed_work: uncommitted changes and unpushed commits across your projects.

Before closing apps or moving folders, it's worth knowing what work only exists
on this Mac. We never run `git fetch` so this stays read-only and offline;
"ahead" is relative to the last known state of the remote.
"""

import os
from pathlib import Path

from rabi.tools._macos import run


def default_roots() -> list[str]:
    # RABI_PROJECT_ROOTS lets you add folders, separated by ":" like PATH.
    raw = os.getenv("RABI_PROJECT_ROOTS", "~/dev")
    return [r for r in raw.split(":") if r]


def find_repos(root: Path, max_depth: int = 3) -> list[Path]:
    repos: list[Path] = []
    if not root.is_dir():
        return repos
    for dirpath, dirnames, _ in os.walk(root):
        if ".git" in dirnames or os.path.isfile(os.path.join(dirpath, ".git")):
            repos.append(Path(dirpath))
            dirnames.clear()
            continue
        if len(Path(dirpath).relative_to(root).parts) >= max_depth:
            dirnames.clear()
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".venv", "venv"} and not d.startswith(".")]
    return repos


def parse_status(porcelain: str) -> dict:
    """Parse `git status --porcelain=v2 --branch` output."""
    branch, upstream, ahead, changed, untracked = None, None, 0, 0, 0
    for line in porcelain.splitlines():
        if line.startswith("# branch.head "):
            branch = line.split(" ", 2)[2]
        elif line.startswith("# branch.upstream "):
            upstream = line.split(" ", 2)[2]
        elif line.startswith("# branch.ab "):
            ahead = int(line.split()[2].lstrip("+"))
        elif line.startswith("? "):
            untracked += 1
        elif line and line[0] in "12u":
            changed += 1
    return {"branch": branch, "upstream": upstream, "commits_ahead": ahead,
            "changed_files": changed, "untracked_files": untracked}


def repo_status(repo: Path) -> dict | None:
    out = run(["git", "-C", str(repo), "status", "--porcelain=v2", "--branch"], timeout=10)
    if out is None:
        return None
    st = parse_status(out)
    if st["upstream"] is None:
        # No upstream: count every local commit as unpushed if there's no remote at all.
        has_remote = bool((run(["git", "-C", str(repo), "remote"]) or "").strip())
        st["note"] = "branch has no upstream" if has_remote else "no remote configured"
    return st


def unpushed_work(roots: list[str] | None = None) -> dict:
    """List git repos (default under ~/dev) with uncommitted changes or unpushed commits."""
    home = str(Path.home())
    roots = roots or default_roots()
    at_risk, clean = [], 0
    for root in roots:
        for repo in find_repos(Path(root).expanduser()):
            st = repo_status(repo)
            if st is None:
                continue
            dirty = st["changed_files"] or st["untracked_files"]
            if dirty or st["commits_ahead"] or "note" in st:
                at_risk.append({"repo": str(repo).replace(home, "~", 1), **st})
            else:
                clean += 1
    return {"roots": roots, "repos_with_unsaved_work": at_risk, "clean_repos": clean}
