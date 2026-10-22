import subprocess

from rabi.tools import git_work


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def init_repo(path):
    path.mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=path)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init", cwd=path)


def test_parse_status_counts():
    out = "# branch.oid abc\n# branch.head main\n# branch.upstream origin/main\n# branch.ab +3 -0\n1 .M N... 100644 100644 100644 a b f.py\n? new.txt\n"
    st = git_work.parse_status(out)
    assert st == {"branch": "main", "upstream": "origin/main", "commits_ahead": 3, "changed_files": 1, "untracked_files": 1}


def test_unpushed_work_finds_dirty_and_ahead(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    dev = tmp_path / "dev"
    a = dev / "app"
    init_repo(a)
    git("remote", "add", "origin", str(remote), cwd=a)
    git("push", "-q", "-u", "origin", "main", cwd=a)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "local", cwd=a)
    (a / "wip.py").write_text("x")
    clean = dev / "clean"
    init_repo(clean)
    git("remote", "add", "origin", str(remote), cwd=clean)
    git("fetch", "-q", "origin", cwd=clean)
    git("branch", "-q", "-u", "origin/main", cwd=clean)
    git("reset", "-q", "--hard", "origin/main", cwd=clean)

    out = git_work.unpushed_work([str(dev)])
    risky = {r["repo"].rsplit("/", 1)[-1]: r for r in out["repos_with_unsaved_work"]}
    assert risky["app"]["commits_ahead"] == 1
    assert risky["app"]["untracked_files"] == 1
    assert out["clean_repos"] == 1


def test_default_roots_from_env(monkeypatch):
    monkeypatch.setenv("RABI_PROJECT_ROOTS", "~/dev:~/work")
    assert git_work.default_roots() == ["~/dev", "~/work"]
